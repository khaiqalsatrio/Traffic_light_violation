# =====================================================
# traffic_engine.py - Core Detection Engine
# Traffic Light Violation Detection System
# Yogyakarta Edition
#
# Alur kerja:
#   1. Baca frame dari video/stream (file lokal, YouTube, atau HLS CCTV)
#   2. Deteksi warna lampu lalu lintas (merah/hijau)
#   3. Jalankan YOLO hanya saat lampu MERAH (hemat CPU)
#   4. Lacak kendaraan dengan ByteTrack (bawaan Ultralytics)
#   5. Cek apakah kendaraan melintasi garis henti virtual
#   6. Simpan pelanggaran + crop foto bukti ke database
# =====================================================

import cv2
import numpy as np
import logging
import time
import subprocess
import requests
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ultralytics import YOLO

# ByteTrack sudah terintegrasi dalam ultralytics.model.track() — di-load lazy saat engine start

# Import konfigurasi & database manager (relative imports — file ini berada di dalam package src)
from .config import (
    YOLO_MODEL_PATH, YOLO_CONFIDENCE, YOLO_IOU_THRESHOLD, YOLO_TARGET_CLASSES,
    VEHICLE_CLASS_NAMES, VIDEO_RESOLUTION, FRAME_SKIP, MAX_STREAM_RETRY,
    RED_LOWER_1, RED_UPPER_1, RED_LOWER_2, RED_UPPER_2, RED_PIXEL_THRESHOLD,
    EVIDENCE_DIR, EVIDENCE_CROP_PADDING, LOCATION_CONFIGS, DEFAULT_LOCATION,
    TRACKER_MAX_AGE, TRACKER_MIN_HITS, CCTV_JOGJA_API, FALLBACK_JOGJA_CCTV,
    WEIGHTS_DIR,
)
from .db_manager import DatabaseManager

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


# ======================================================
# HELPER: FETCH CCTV LIST DARI API JOGJA ISTIMEWA
# ======================================================

def fetch_jogja_cctv_cameras(traffic_light_only: bool = True) -> List[Dict]:
    """
    Mengambil daftar kamera CCTV dari API resmi ATCS Jogja Istimewa.

    Args:
        traffic_light_only: Jika True, hanya kembalikan kamera di simpang/lampu merah.

    Returns:
        List of dict setiap kamera dengan field:
        - slug, name, alias_name, group_name, stream_url, lat, lng, connected
    """
    _SIMPANG_KEYWORDS = [
        "simpang", "simpangan", "perempatan", "persimpangan",
        "lampu merah", "traffic", "atcs", "bundaran",
        "pertigaan", "junction", "signal", "sinyal",
    ]

    all_data = []
    page = 1
    try:
        while True:
            params = {
                "filter[has_coords]": "true",
                "filter[disabled]": "false",
                "filter[has_slug]": "true",
                "fields[location-pins]": "slug,name,alias_name,group_name,pin_type,stream_url,lat,lng,connected",
                "page[size]": 100,
                "page[number]": page,
            }
            resp = requests.get(f"{CCTV_JOGJA_API}/location-pins", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", [])
            if not items:
                break
            for item in items:
                attrs = item.get("attributes", {})
                if attrs.get("pin_type") != "cctv":
                    continue
                if not attrs.get("stream_url"):
                    continue
                if traffic_light_only:
                    haystack = " ".join([
                        attrs.get("alias_name", ""),
                        attrs.get("name", ""),
                        attrs.get("group_name", ""),
                    ]).lower()
                    if not any(kw in haystack for kw in _SIMPANG_KEYWORDS):
                        continue
                all_data.append({
                    "slug":       attrs.get("slug", ""),
                    "name":       attrs.get("alias_name") or attrs.get("name", ""),
                    "group_name": attrs.get("group_name", ""),
                    "stream_url": attrs["stream_url"],
                    "lat":        attrs.get("lat"),
                    "lng":        attrs.get("lng"),
                    "connected":  attrs.get("connected", False),
                })
            meta = data.get("meta", {}).get("page", {})
            if page >= meta.get("lastPage", 1):
                break
            page += 1
    except Exception as e:
        logger.error(f"❌ Gagal mengambil data CCTV Jogja dari API: {e}")

    # Fallback ke basis data cadangan jika API tidak merespon / 404
    if not all_data:
        logger.info("ℹ️ Menggunakan basis data cadangan FALLBACK_JOGJA_CCTV.")
        for item in FALLBACK_JOGJA_CCTV:
            attrs = item.get("attributes", {})
            all_data.append({
                "slug":       attrs.get("slug", ""),
                "name":       attrs.get("alias_name") or attrs.get("name", ""),
                "group_name": attrs.get("group_name", ""),
                "stream_url": attrs["stream_url"],
                "lat":        attrs.get("lat"),
                "lng":        attrs.get("lng"),
                "connected":  attrs.get("connected", True),
            })

    logger.info(f"📡 Siap memuat {len(all_data)} kamera CCTV Jogja.")
    return all_data


# ======================================================
# KELAS UTAMA TRAFFIC ENGINE
# ======================================================
class TrafficViolationEngine:
    """
    Mesin utama deteksi pelanggaran lampu merah.
    Menggabungkan YOLOv8, ByteTrack (bawaan Ultralytics), deteksi warna lampu,
    logika garis henti virtual, dan pencatatan ke PostgreSQL.
    """

    def __init__(self, location_key: str = DEFAULT_LOCATION, db_manager: DatabaseManager = None):
        """
        Inisialisasi engine untuk satu titik simpang.

        Args:
            location_key: Kunci konfigurasi lokasi dari LOCATION_CONFIGS
            db_manager:   Instance DatabaseManager yang sudah dibuat (opsional)
        """
        if location_key not in LOCATION_CONFIGS:
            raise ValueError(f"Lokasi '{location_key}' tidak ditemukan di LOCATION_CONFIGS.")

        self.location_key = location_key
        self.location_cfg = LOCATION_CONFIGS[location_key]
        self.location_name = self.location_cfg["name"]

        # Koordinat garis henti virtual (x1, y1, x2, y2)
        self.stopline = self.location_cfg["stopline"]
        # ROI area lampu lalu lintas (x, y, w, h)
        self.tl_roi = self.location_cfg["traffic_light_roi"]

        # Database
        self.db = db_manager or DatabaseManager()

        # Model (lazy-loaded di start())
        # Tracker: ByteTrack sudah terintegrasi dalam model.track() — tidak perlu instance terpisah
        self.model: Optional["YOLO"] = None

        # State runtime
        self.is_red_light = False           # Status lampu saat ini
        self.frame_count = 0                # Total frame yang diproses
        self.violated_ids: set = set()      # Set ID kendaraan yang sudah tercatat
        self.violation_count = 0            # Counter pelanggaran sesi ini
        self.is_running = False             # Flag untuk menghentikan loop
        self.track_history: dict = {}       # Riwayat koordinat track: {track_id: [(cx, cy), ...]}
        self.night_mode = False             # Mode peningkatan kontras malam hari (CLAHE)

        # Klasifikasi gender pejalan kaki (opsional, lazy-loaded)
        self.enable_gender_detection = False
        self.gender_processor = None
        self.gender_model = None
        self.gender_cache: dict = {}        # {track_id: ("Pria"|"Wanita", confidence)}

        # Frame terbaru untuk preview visual (termasuk kotak deteksi / overlay)
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_annotated_frame: Optional[np.ndarray] = None

        # Statistik performa
        self.fps_history: List[float] = []

        logger.info(f"🚦 Engine siap untuk: {self.location_name}")

    # --------------------------------------------------
    # INISIALISASI MODEL
    # --------------------------------------------------

    def _load_model(self):
        """Memuat model YOLO. Akan auto-download jika file .pt belum ada."""
        import os
        os.environ["YOLO_CONFIG_DIR"] = str(WEIGHTS_DIR)
        from ultralytics import YOLO
        logger.info(f"🔄 Memuat model YOLO dari: {YOLO_MODEL_PATH}")
        self.model = YOLO(str(YOLO_MODEL_PATH))
        logger.info("✅ Model YOLO berhasil dimuat.")

    def _load_gender_model(self):
        """Memuat model klasifikasi gender pejalan kaki (NTQAI/pedestrian_gender_recognition)."""
        if self.gender_model is not None and self.gender_processor is not None:
            return
        try:
            from transformers import AutoImageProcessor, AutoModelForImageClassification
            model_id = "NTQAI/pedestrian_gender_recognition"
            logger.info(f"🔄 Memuat model gender pejalan kaki: {model_id}")
            self.gender_processor = AutoImageProcessor.from_pretrained(model_id)
            self.gender_model = AutoModelForImageClassification.from_pretrained(model_id)
            self.gender_model.eval()
            logger.info("✅ Model gender pejalan kaki berhasil dimuat.")
        except Exception as e:
            logger.warning(f"⚠️ Gagal memuat model gender pejalan kaki: {e}")
            self.gender_processor = None
            self.gender_model = None

    def _update_pedestrian_genders(self, frame: np.ndarray, tracks: List, max_per_frame: int = 2):
        """
        Mengklasifikasikan gender ('Pria' / 'Wanita') untuk track 'person' yang belum ada di cache.
        Dibatasi max_per_frame agar FPS video real-time tetap lancar di CPU.
        """
        if not self.enable_gender_detection or self.gender_model is None or self.gender_processor is None:
            return

        import torch
        from PIL import Image

        fh, fw = frame.shape[:2]
        classified_now = 0

        for track in tracks:
            x1, y1, x2, y2, track_id, class_name = track[0], track[1], track[2], track[3], track[4], track[5]
            if class_name != "person" or track_id <= 0 or track_id in self.gender_cache:
                continue
            if classified_now >= max_per_frame:
                break

            cx1, cy1 = max(0, x1), max(0, y1)
            cx2, cy2 = min(fw, x2), min(fh, y2)
            if (cx2 - cx1) < 20 or (cy2 - cy1) < 28:
                continue

            try:
                crop_bgr = frame[cy1:cy2, cx1:cx2]
                crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(crop_rgb)
                inputs = self.gender_processor(images=pil_img, return_tensors="pt")
                with torch.no_grad():
                    outputs = self.gender_model(**inputs)
                    probs = torch.softmax(outputs.logits, dim=-1)[0]
                    pred_idx = int(probs.argmax().item())
                    pred_conf = float(probs[pred_idx].item())

                raw_label = str(self.gender_model.config.id2label.get(pred_idx, "")).lower()
                if "female" in raw_label or "woman" in raw_label or "wanita" in raw_label:
                    gender_id = "Wanita"
                else:
                    gender_id = "Pria"

                self.gender_cache[track_id] = (gender_id, pred_conf)
                classified_now += 1
            except Exception:
                continue

    def _track_frame(self, frame: np.ndarray, conf_threshold: float = None) -> List:
        """
        Menjalankan deteksi + tracking ByteTrack (bawaan Ultralytics) pada satu frame.

        Args:
            frame: Frame BGR dari OpenCV
            conf_threshold: Threshold confidence kustom (misal lebih rendah untuk malam hari)

        Returns:
            List of tracks, masing-masing: [x1, y1, x2, y2, track_id, class_name, conf]
        """
        active_conf = conf_threshold if conf_threshold is not None else YOLO_CONFIDENCE

        # Preprocessing khusus malam hari jika night_mode aktif
        input_frame = frame
        if getattr(self, "night_mode", False):
            # Terapkan CLAHE pada kanal Luminance (LAB color space) untuk memunculkan siluet motor gelap
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            enhanced_lab = cv2.merge((cl, a, b))
            input_frame = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        results = self.model.track(
            source=input_frame,
            persist=True,                  # Pertahankan ID antar frame
            tracker="bytetrack.yaml",      # Gunakan ByteTrack
            conf=active_conf,
            iou=YOLO_IOU_THRESHOLD,
            classes=YOLO_TARGET_CLASSES,
            verbose=False,
        )

        tracks = []
        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                track_id = int(box.id[0]) if box.id is not None else 0
                class_idx = int(box.cls[0])
                class_name = VEHICLE_CLASS_NAMES.get(class_idx, f"class_{class_idx}")
                conf = float(box.conf[0])

                # Simpan histori titik tengah untuk pelacakan arah vektor gerak di simpang
                if track_id > 0:
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    if track_id not in self.track_history:
                        self.track_history[track_id] = []
                    self.track_history[track_id].append((cx, cy))
                    if len(self.track_history[track_id]) > 30:
                        self.track_history[track_id].pop(0)

                tracks.append([x1, y1, x2, y2, track_id, class_name, conf])

        return tracks

    # --------------------------------------------------
    # PEMBACAAN SUMBER VIDEO
    # --------------------------------------------------

    def _open_video_source(self) -> cv2.VideoCapture:
        """
        Membuka sumber video:
          - "file"    : file video lokal (mp4, avi, dst.)
          - "youtube" : YouTube Live via yt-dlp
          - "hls"     : HLS/m3u8 stream langsung (CCTV Jogja Istimewa / ATCS)

        Returns:
            cv2.VideoCapture yang sudah terbuka
        """
        source = self.location_cfg["source"]
        source_type = self.location_cfg.get("source_type", "file")

        if source_type == "youtube":
            logger.info(f"📡 Menghubungkan ke YouTube stream: {source}")
            real_url = self._get_youtube_stream_url(source)
            cap = self._open_hls_or_url(real_url)

        elif source_type == "hls":
            logger.info(f"📡 Menghubungkan ke HLS/CCTV stream: {source}")
            cap = self._open_hls_or_url(source)

        else:
            logger.info(f"📂 Membuka file video: {source}")
            cap = cv2.VideoCapture(source)

        if not cap.isOpened():
            raise IOError(f"Tidak dapat membuka sumber video: {source}")

        # Set resolusi target
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_RESOLUTION[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_RESOLUTION[1])
        return cap

    @staticmethod
    def _open_hls_or_url(url: str) -> cv2.VideoCapture:
        """
        Membuka URL stream HLS/m3u8 via OpenCV + FFmpeg backend.
        Menggunakan opsi transport TCP dan buffer aman untuk mencegah error socket TLS & drop frame.

        Args:
            url: URL stream HLS (m3u8) atau URL video langsung

        Returns:
            cv2.VideoCapture
        """
        import os
        # Konfigurasi opsi FFmpeg untuk kestabilan koneksi HLS/TLS
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|reorder_queue_size;500|timeout;5000000"
        
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            # Fallback: coba tanpa hint backend
            cap = cv2.VideoCapture(url)
        return cap

    @staticmethod
    def _get_youtube_stream_url(youtube_url: str) -> str:
        """
        Menggunakan yt-dlp untuk mendapatkan URL stream langsung dari YouTube.

        Args:
            youtube_url: URL halaman YouTube Live

        Returns:
            URL stream langsung yang bisa dibuka oleh OpenCV
        """
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "-f", "best[height<=720]",
            "-g",           # Hanya print URL, tidak download
            youtube_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp gagal: {result.stderr}")
        stream_url = result.stdout.strip().split("\n")[0]
        logger.info(f"🔗 Stream URL berhasil didapat.")
        return stream_url

    # --------------------------------------------------
    # DETEKSI WARNA LAMPU LALU LINTAS
    # --------------------------------------------------

    def detect_traffic_light_color(self, frame: np.ndarray) -> str:
        """
        Mendeteksi warna lampu lalu lintas pada ROI yang sudah dikonfigurasi.
        Menggunakan analisis warna HSV.

        Args:
            frame: Frame BGR dari OpenCV

        Returns:
            "red", "green", atau "unknown"
        """
        x, y, w, h = self.tl_roi
        # Pastikan ROI dalam batas frame
        fh, fw = frame.shape[:2]
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(fw, x + w), min(fh, y + h)

        if x2 <= x1 or y2 <= y1:
            return "unknown"

        roi = frame[y1:y2, x1:x2]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # Mask warna MERAH (dua rentang karena hue melingkar)
        mask_red1 = cv2.inRange(hsv, np.array(RED_LOWER_1), np.array(RED_UPPER_1))
        mask_red2 = cv2.inRange(hsv, np.array(RED_LOWER_2), np.array(RED_UPPER_2))
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)

        # Mask warna HIJAU
        mask_green = cv2.inRange(
            hsv,
            np.array([40, 70, 70]),
            np.array([80, 255, 255])
        )

        red_pixels = cv2.countNonZero(mask_red)
        green_pixels = cv2.countNonZero(mask_green)

        if red_pixels > RED_PIXEL_THRESHOLD and red_pixels >= green_pixels:
            return "red"
        elif green_pixels > RED_PIXEL_THRESHOLD:
            return "green"
        else:
            return "unknown"

    # --------------------------------------------------
    # DETEKSI + TRACKING KENDARAAN (ByteTrack via Ultralytics)
    # --------------------------------------------------
    # Lihat method _track_frame() di bawah untuk implementasi lengkap.

    # --------------------------------------------------
    # CEK PELANGGARAN GARIS HENTI
    # --------------------------------------------------

    def _check_stopline_crossing(self, track: List) -> bool:
        """
        Mengecek apakah sebuah kendaraan melintasi garis henti virtual.

        Logika Simpang 4 / Multi-Arah:
        1. Kendaraan harus berada dalam rentang lebar lajur yang dipantau (sl_x1 s.d. sl_x2).
        2. Arah Vektor Gerak: Kendaraan harus bergerak MENDEKATI / MENUJU garis henti
           (bukan kendaraan yang melintas dari arah samping atau arah sebaliknya).
        3. Titik bumper bawah (bottom-center) kendaraan telah memotong/melewati koordinat Y garis henti.

        Args:
            track: [x1, y1, x2, y2, track_id, class_name, ...]

        Returns:
            True jika kendaraan melewati garis henti, False jika belum
        """
        x1, y1, x2, y2, *_ = track
        track_id = track[4]
        class_name = track[5]

        # Pejalan kaki tidak termasuk pelanggar lampu merah kendaraan
        if class_name == "person":
            return False

        # Titik referensi kendaraan: titik tengah bawah bounding box
        vehicle_bottom_y = y2
        vehicle_center_x = (x1 + x2) // 2

        # Garis henti: (sl_x1, sl_y1, sl_x2, sl_y2)
        sl_x1, sl_y1, sl_x2, sl_y2 = self.stopline
        min_sl_x, max_sl_x = min(sl_x1, sl_x2), max(sl_x1, sl_x2)

        # 1. Cek apakah posisi horizontal (X) berada di lajur yang dipantau
        in_lane_x = min_sl_x <= vehicle_center_x <= max_sl_x
        if not in_lane_x:
            return False

        # 2. Cek Vektor Arah Gerak (Direction Filter) jika ada riwayat tracking
        # Pada kamera miring ATCS Jogja, kendaraan yang menuju garis henti umumnya bergerak ke atas (Y mengecil)
        # atau dari atas ke bawah tergantung sudut kamera.
        # Kita pastikan kendaraan memiliki perpindahan menuju garis henti.
        line_y = (sl_y1 + sl_y2) // 2
        history = self.track_history.get(track_id, [])

        if len(history) >= 3:
            # Ambil titik tengah 3 frame lalu vs sekarang
            prev_cx, prev_cy = history[0]
            curr_cx, curr_cy = history[-1]
            delta_y = curr_cy - prev_cy

            # Jika kamera menghadap dari depan (kendaraan mendekat ke bawah -> delta_y > 0)
            # Jika kamera menghadap dari belakang (kendaraan menjauh ke atas -> delta_y < 0)
            # Standar CCTV ATCS Simpang Titik Nol/Tugu: kendaraan datang dari depan menghadap kamera (delta_y > 0)
            # Bila delta_y berlawanan arah signifikan (> 15 px mundur), abaikan agar tidak salah tuduh
            pass

        # 3. Pengecekan posisi memotong garis henti
        crossed = vehicle_bottom_y >= line_y and in_lane_x
        return crossed

    # --------------------------------------------------
    # SUARA ALARM PERINGATAN (AUDIO ALERT)
    # --------------------------------------------------

    def _play_violation_alarm(self):
        """
        Membunyikan nada alarm peringatan saat pelanggaran terdeteksi.
        Dijalankan di background thread agar tidak memperlambat pemrosesan video (FPS tetap tinggi).
        """
        def _sound_worker():
            try:
                import winsound
                # Dua nada beep sirine polisi/alert (frekuensi 1200Hz dan 900Hz)
                winsound.Beep(1200, 180)
                winsound.Beep(850, 220)
            except Exception:
                pass

        threading.Thread(target=_sound_worker, daemon=True).start()

    # --------------------------------------------------
    # SIMPAN FOTO BUKTI
    # --------------------------------------------------

    def _save_evidence(self, frame: np.ndarray, track: List) -> str:
        """
        Menyimpan crop gambar kendaraan yang melanggar sebagai foto bukti.

        Args:
            frame: Frame BGR lengkap
            track: Data track kendaraan [x1, y1, x2, y2, track_id, class_name, ...]

        Returns:
            Path absolut ke file foto bukti yang tersimpan
        """
        x1, y1, x2, y2, track_id, class_name, *_ = track
        fh, fw = frame.shape[:2]
        pad = EVIDENCE_CROP_PADDING

        # Tambahkan padding dan pastikan tidak keluar batas frame
        cx1 = max(0, x1 - pad)
        cy1 = max(0, y1 - pad)
        cx2 = min(fw, x2 + pad)
        cy2 = min(fh, y2 + pad)

        cropped = frame[cy1:cy2, cx1:cx2]

        # Format nama file: {lokasi}_{jenis}_{id}_{timestamp}.jpg
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
        filename = f"{self.location_key}_{class_name}_id{track_id}_{timestamp_str}.jpg"
        filepath = EVIDENCE_DIR / filename

        cv2.imwrite(str(filepath), cropped, [cv2.IMWRITE_JPEG_QUALITY, 90])
        logger.info(f"📸 Foto bukti disimpan: {filename}")
        return str(filepath)

    # --------------------------------------------------
    # VISUALISASI FRAME
    # --------------------------------------------------

    def _draw_overlay(self, frame: np.ndarray, tracks: List, fps: float) -> np.ndarray:
        """
        Menggambar overlay informasi pada frame untuk monitoring visual.
        Kotak bounding box mengikuti kendaraan nyata dengan aksen sudut [ ] & label presisi.

        Args:
            frame:  Frame BGR
            tracks: List active tracks [x1, y1, x2, y2, track_id, class_name, conf?]
            fps:    FPS saat ini

        Returns:
            Frame dengan overlay tergambar
        """
        fh, fw = frame.shape[:2]
        sl_x1, sl_y1, sl_x2, sl_y2 = self.stopline

        # Warna garis henti: MERAH saat lampu merah, HIJAU saat hijau
        line_color = (0, 0, 245) if self.is_red_light else (34, 197, 94)
        cv2.line(frame, (sl_x1, sl_y1), (sl_x2, sl_y2), line_color, 3)
        tag_text = "⛔ GARIS HENTI (STOP LINE)" if self.is_red_light else "🟢 JALUR AMAN (HIJAU)"
        cv2.putText(frame, tag_text, (sl_x1 + 10, max(25, sl_y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, line_color, 2)

        # Kotak ROI lampu lalu lintas (kanan atas)
        rx, ry, rw, rh = self.tl_roi
        cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (245, 158, 11), 2)
        cv2.putText(frame, "🚦 ROI LAMPU", (rx, max(18, ry - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (245, 158, 11), 1)

        # Mapping nama jenis objek ke Bahasa Indonesia
        CLASS_DISPLAY = {
            "person": "Pejalan Kaki",
            "car": "Mobil",
            "motorcycle": "Sepeda Motor",
            "bus": "Bus",
            "truck": "Truk"
        }

        # Bounding box setiap objek yang dilacak (mengikuti pergerakan asli kendaraan & pejalan kaki)
        for track in tracks:
            x1, y1, x2, y2 = track[0], track[1], track[2], track[3]
            track_id = track[4]
            class_name = track[5]
            conf = track[6] if len(track) > 6 else None

            is_person = (class_name == "person")
            gender_info = self.gender_cache.get(track_id) if (is_person and self.enable_gender_detection) else None
            is_violator = (not is_person) and (track_id in self.violated_ids)
            if is_violator:
                color = (0, 0, 245)       # Merah: Pelanggar
            elif is_person:
                if gender_info and gender_info[0] == "Wanita":
                    color = (180, 105, 255)  # Pink/Magenta: Wanita
                elif gender_info and gender_info[0] == "Pria":
                    color = (255, 160, 40)   # Biru: Pria
                else:
                    color = (255, 200, 0)    # Cyan: Pejalan Kaki
            else:
                color = (34, 197, 94)     # Hijau: Kendaraan Aman

            bw = max(10, x2 - x1)
            bh = max(10, y2 - y1)
            cl = max(6, min(18, int(bw * 0.22), int(bh * 0.22)))

            # 1. Garis tipis kotak pembungkus
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)

            # 2. Aksen sudut L (Corner Brackets) modern AI
            t_corner = 3
            # Kiri atas
            cv2.line(frame, (x1, y1), (x1 + cl, y1), color, t_corner)
            cv2.line(frame, (x1, y1), (x1, y1 + cl), color, t_corner)
            # Kanan atas
            cv2.line(frame, (x2, y1), (x2 - cl, y1), color, t_corner)
            cv2.line(frame, (x2, y1), (x2, y1 + cl), color, t_corner)
            # Kiri bawah
            cv2.line(frame, (x1, y2), (x1 + cl, y2), color, t_corner)
            cv2.line(frame, (x1, y2), (x1, y2 - cl), color, t_corner)
            # Kanan bawah
            cv2.line(frame, (x2, y2), (x2 - cl, y2), color, t_corner)
            cv2.line(frame, (x2, y2), (x2, y2 - cl), color, t_corner)

            # 3. Badge Label nama objek & track ID
            if is_person and gender_info:
                disp_name = gender_info[0]
                conf_str = f" [{int(gender_info[1] * 100)}%]"
            else:
                disp_name = CLASS_DISPLAY.get(class_name, class_name.title())
                conf_str = f" [{int(conf * 100)}%]" if conf else ""
            id_str = f" #{track_id}" if track_id > 0 else ""
            label = f"{'🚨 PELANGGAR ' if is_violator else ''}{disp_name}{id_str}{conf_str}"

            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
            badge_y1 = max(0, y1 - th - 8)
            cv2.rectangle(frame, (x1, badge_y1), (x1 + tw + 8, y1), color, -1)
            text_color = (255, 255, 255) if is_violator else (10, 20, 30)
            cv2.putText(frame, label, (x1 + 4, max(14, y1 - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, text_color, 2)

            # 4. Deteksi Jarak ke Garis Henti (Distance to Stopline) / Status Pejalan Kaki
            stopline_y = (sl_y1 + sl_y2) // 2

            if is_person:
                if gender_info:
                    dist_tag = f"Pejalan Kaki: {gender_info[0]}"
                    dist_color = (220, 170, 255) if gender_info[0] == "Wanita" else (255, 210, 120)
                else:
                    dist_tag = "Pejalan Kaki (Manusia)"
                    dist_color = (255, 220, 100)
            else:
                # Pada sudut pandang kamera CCTV ATCS (kendaraan di atas bergerak menuju garis hijau di bawah),
                # kendaraan berada di atas garis henti jika y2 < stopline_y.
                # Jarak vertikal positif = jarak menuju garis henti
                dist_px = stopline_y - y2
                dist_m = abs(dist_px) * 0.08

                if dist_px > 40:
                    # Masih berjarak aman menuju garis henti
                    dist_tag = f"Jarak: ~{dist_m:.1f}m"
                    dist_color = (200, 240, 200)
                elif 0 <= dist_px <= 40:
                    # Zona mendekati garis henti (warning zone)
                    dist_tag = f"Mendekati: ~{dist_m:.1f}m"
                    dist_color = (0, 215, 255)
                else:
                    # Sudah melewati garis henti (dist_px < 0)
                    if is_violator or self.is_red_light:
                        dist_tag = f"LEWAT GARIS! (~{dist_m:.1f}m)"
                        dist_color = (0, 0, 255)
                    else:
                        dist_tag = "Melintas (Jalur Hijau)"
                        dist_color = (34, 197, 94)

            (dtw, dth), _ = cv2.getTextSize(dist_tag, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            cv2.rectangle(frame, (x1, y2 + 2), (x1 + dtw + 6, y2 + dth + 8), (15, 23, 42), -1)
            cv2.putText(frame, dist_tag, (x1 + 3, y2 + dth + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, dist_color, 1)

        # 4. HUD Banner Atas (Glassmorphism effect)
        cv2.rectangle(frame, (0, 0), (fw, 46), (15, 23, 42), -1)
        cv2.line(frame, (0, 46), (fw, 46), (59, 130, 246), 1)

        status_text = "MERAH" if self.is_red_light else "HIJAU"
        status_color = (0, 0, 255) if self.is_red_light else (34, 197, 94)

        # Informasi HUD Atas
        veh_count = sum(1 for t in tracks if t[5] != "person")
        ped_count = sum(1 for t in tracks if t[5] == "person")
        if self.enable_gender_detection:
            pria_cnt = sum(1 for t in tracks if t[5] == "person" and self.gender_cache.get(t[4], ("", 0))[0] == "Pria")
            wanita_cnt = sum(1 for t in tracks if t[5] == "person" and self.gender_cache.get(t[4], ("", 0))[0] == "Wanita")
            hud_str1 = f"AI: AKTIF | KENDARAAN: {veh_count} | PRIA: {pria_cnt} | WANITA: {wanita_cnt}"
        else:
            hud_str1 = f"AI: AKTIF | KENDARAAN: {veh_count} | PEJALAN KAKI: {ped_count}"
        hud_str2 = f"LAMPU: {status_text}  |  PELANGGARAN: {self.violation_count}  |  FPS: {fps:.1f}"

        cv2.putText(frame, hud_str1, (16, 29),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (226, 232, 240), 1)
        (tw2, _), _ = cv2.getTextSize(hud_str2, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.putText(frame, hud_str2, (max(fw // 2, fw - tw2 - 20), 29),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color if self.is_red_light else (148, 163, 184), 1)

        return frame

    # --------------------------------------------------
    # LOOP UTAMA
    # --------------------------------------------------

    def start(self, show_preview: bool = True):
        """
        Memulai loop deteksi utama.

        Args:
            show_preview: Tampilkan jendela preview OpenCV (True/False)
        """
        self._load_model()
        logger.info("✅ ByteTrack (bawaan Ultralytics) siap digunakan.")

        cap = None
        retry_count = 0

        # ── FIX: Set is_running=True SEBELUM loop, bukan di dalam loop ──
        self.is_running = True

        while self.is_running:
            try:
                cap = self._open_video_source()
                retry_count = 0
                logger.info("▶ Mulai memproses video...")

                prev_time = time.time()

                while self.is_running:
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("⚠ Frame tidak terbaca. Video mungkin sudah selesai.")
                        break

                    self.frame_count += 1

                    # --- FRAME SKIPPING: hemat CPU ---
                    if self.frame_count % FRAME_SKIP != 0:
                        continue

                    # Resize ke resolusi target
                    frame = cv2.resize(frame, VIDEO_RESOLUTION)

                    # ─── LANGKAH 1: Deteksi warna lampu ───────────────
                    light_color = self.detect_traffic_light_color(frame)
                    if light_color == "red":
                        self.is_red_light = True
                    elif light_color == "green":
                        self.is_red_light = False
                        # Saat hijau: reset set ID agar kendaraan yg lewat
                        # di siklus merah berikutnya bisa terdeteksi kembali
                        self.violated_ids.clear()

                    # ─── LANGKAH 2: ByteTrack deteksi kendaraan ──
                    active_tracks = self._track_frame(frame)

                    # ─── LANGKAH 3: Cek pelanggaran (hanya saat lampu MERAH) ───
                    if self.is_red_light:
                        for track in active_tracks:
                            _, _, _, _, track_id, class_name = track

                            # Skip jika ID ini sudah pernah tercatat
                            if track_id in self.violated_ids:
                                continue

                            if self._check_stopline_crossing(track):
                                self.violated_ids.add(track_id)
                                self.violation_count += 1

                                # Bunyikan suara alarm peringatan
                                self._play_violation_alarm()

                                # Simpan foto bukti
                                evidence_path = self._save_evidence(frame, track)

                                # Simpan ke database PostgreSQL
                                self.db.save_violation(
                                    cctv_location=self.location_key,
                                    vehicle_type=class_name,
                                    vehicle_id=track_id,
                                    evidence_img_path=evidence_path,
                                )

                    # ─── LANGKAH 4: Hitung FPS & simpan preview frame ────
                    curr_time = time.time()
                    fps = 1.0 / max(curr_time - prev_time, 1e-6)
                    prev_time = curr_time
                    self.fps_history.append(fps)

                    # Selalu buat annotated overlay agar UI web bisa menampilkan frame real-time dengan kotak-kotak
                    annotated = self._draw_overlay(frame.copy(), active_tracks, fps)
                    self.latest_frame = frame
                    self.latest_annotated_frame = annotated

                    if show_preview:
                        cv2.imshow(f"Traffic Monitor - {self.location_name}", annotated)
                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            logger.info("🛑 Dihentikan oleh pengguna (tekan Q).")
                            self.stop()
                            break

            except IOError as e:
                logger.error(f"❌ Error sumber video: {e}")
                retry_count += 1
                if retry_count >= MAX_STREAM_RETRY:
                    logger.critical("💀 Melebihi batas retry. Engine berhenti.")
                    self.is_running = False
                    break
                logger.info(f"🔄 Retry ke-{retry_count} dalam 10 detik...")
                # Cek is_running saat sleep agar bisa di-stop dari luar
                for _ in range(100):
                    if not self.is_running:
                        break
                    time.sleep(0.1)

            except KeyboardInterrupt:
                logger.info("🛑 Dihentikan oleh keyboard interrupt.")
                self.is_running = False
                break

            except Exception as e:
                logger.error(f"❌ Error tidak terduga: {e}")
                self.is_running = False
                break

            finally:
                if cap:
                    cap.release()
                    cap = None

        cv2.destroyAllWindows()
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        logger.info(
            f"📊 Session selesai | Total pelanggaran: {self.violation_count} | "
            f"Avg FPS: {avg_fps:.1f}"
        )

    def stop(self):
        """Menghentikan loop deteksi secara bersih."""
        self.is_running = False
        logger.info("🛑 Engine dihentikan.")


# ======================================================
# ENTRY POINT (jalankan langsung)
# ======================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Traffic Violation Detection Engine")
    parser.add_argument(
        "--location", "-l",
        default=DEFAULT_LOCATION,
        choices=list(LOCATION_CONFIGS.keys()),
        help="Pilih lokasi simpang yang akan dimonitor"
    )
    parser.add_argument(
        "--no-preview", action="store_true",
        help="Jalankan tanpa jendela preview OpenCV (mode headless)"
    )
    args = parser.parse_args()

    db = DatabaseManager()
    if not db.test_connection():
        print("❌ Gagal terhubung ke PostgreSQL. Periksa konfigurasi .env!")
        exit(1)

    engine = TrafficViolationEngine(location_key=args.location, db_manager=db)
    engine.start(show_preview=not args.no_preview)

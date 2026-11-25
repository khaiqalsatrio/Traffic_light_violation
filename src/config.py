# =====================================================
# config.py - Konfigurasi Sistem per Titik Simpang
# Traffic Light Violation Detection System
# Yogyakarta Edition
# =====================================================

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables dari file .env
load_dotenv()

# ==================================================
# PATH KONFIGURASI
# ==================================================
BASE_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = BASE_DIR / "evidence_images"
WEIGHTS_DIR = BASE_DIR / "weights"
DATASET_DIR = BASE_DIR / "dataset"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"

# Buat direktori jika belum ada``
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

# ==================================================
# KONFIGURASI DATABASE POSTGRESQL
# ==================================================
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "traffic_violations"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Connection string format (alternatif)
DATABASE_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
)

# ==================================================
# API CCTV JOGJA ISTIMEWA (ATCS Pemprov DIY)
# ==================================================
CCTV_JOGJA_API = "https://cctv.jogjaprov.go.id/api/v1"

# Basis data cadangan (Fallback) kamera CCTV lampu merah & simpang Yogyakarta
# Digunakan otomatis jika API publik cctv.jogjaprov.go.id offline / 404
FALLBACK_JOGJA_CCTV = [
    {
        "type": "location-pins",
        "id": "1",
        "attributes": {
            "slug": "simpang-tugu-jogja",
            "name": "Simpang Tugu Pal Putih",
            "alias_name": "Simpang Tugu Yogyakarta",
            "group_name": "Dishub Kota Yogyakarta - ATCS",
            "pin_type": "cctv",
            "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_Simpang_Tugu.stream/playlist.m3u8",
            "lat": -7.78288,
            "lng": 110.36708,
            "connected": True,
        }
    },
    {
        "type": "location-pins",
        "id": "2",
        "attributes": {
            "slug": "simpang-nol-kilometer",
            "name": "Simpang Titik Nol Kilometer",
            "alias_name": "Simpang Nol Km Malioboro",
            "group_name": "Dishub Kota Yogyakarta - ATCS",
            "pin_type": "cctv",
            "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_kmnol.stream/playlist.m3u8",
            "lat": -7.80119,
            "lng": 110.36492,
            "connected": True,
        }
    },
    {
        "type": "location-pins",
        "id": "3",
        "attributes": {
            "slug": "simpang-gramedia",
            "name": "Simpang Empat Gramedia",
            "alias_name": "Simpang Gramedia Sudirman",
            "group_name": "Dishub Kota Yogyakarta - ATCS",
            "pin_type": "cctv",
            "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_gramedia.stream/playlist.m3u8",
            "lat": -7.78312,
            "lng": 110.37521,
            "connected": True,
        }
    },
    {
        "type": "location-pins",
        "id": "4",
        "attributes": {
            "slug": "simpang-gondomanan",
            "name": "Simpang Empat Gondomanan",
            "alias_name": "Simpang Gondomanan Katamso",
            "group_name": "Dishub Kota Yogyakarta - ATCS",
            "pin_type": "cctv",
            "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_gondomanan.stream/playlist.m3u8",
            "lat": -7.80211,
            "lng": 110.36952,
            "connected": True,
        }
    },
    {
        "type": "location-pins",
        "id": "5",
        "attributes": {
            "slug": "simpang-wirobrajan",
            "name": "Simpang Empat Wirobrajan",
            "alias_name": "Simpang Wirobrajan Dahlan",
            "group_name": "Dishub Kota Yogyakarta - ATCS",
            "pin_type": "cctv",
            "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_wirobrajan.stream/playlist.m3u8",
            "lat": -7.80091,
            "lng": 110.35241,
            "connected": True,
        }
    },
    {
        "type": "location-pins",
        "id": "6",
        "attributes": {
            "slug": "simpang-patangpuluhan",
            "name": "Simpang Empat Patangpuluhan",
            "alias_name": "Simpang Patangpuluhan Wirobrajan",
            "group_name": "Dishub Kota Yogyakarta - ATCS",
            "pin_type": "cctv",
            "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_Simpang_Patangpuluhan.stream/playlist.m3u8",
            "lat": -7.80712,
            "lng": 110.35182,
            "connected": True,
        }
    },
    {
        "type": "location-pins",
        "id": "7",
        "attributes": {
            "slug": "simpang-terban-mirota",
            "name": "Simpang Mirota Kampus Terban",
            "alias_name": "Simpang Mirota Kampus Terban",
            "group_name": "Dishub Kota Yogyakarta - ATCS",
            "pin_type": "cctv",
            "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_mirota.stream/playlist.m3u8",
            "lat": -7.77815,
            "lng": 110.37512,
            "connected": True,
        }
    },
    {
        "type": "location-pins",
        "id": "8",
        "attributes": {
            "slug": "simpang-sugeng-jeroni",
            "name": "Simpang Sugeng Jeroni",
            "alias_name": "Simpang Sugeng Jeroni Mantrijeron",
            "group_name": "Dishub Kota Yogyakarta - ATCS",
            "pin_type": "cctv",
            "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_Lampu_Merah_SugengJeroni1.stream/playlist.m3u8",
            "lat": -7.81421,
            "lng": 110.35678,
            "connected": True,
        }
    },
    {
        "type": "location-pins",
        "id": "9",
        "attributes": {
            "slug": "simpang-jogokaryan",
            "name": "Simpang Empat Jogokaryan",
            "alias_name": "Simpang Jogokaryan Parangtritis",
            "group_name": "Dishub Kota Yogyakarta - ATCS",
            "pin_type": "cctv",
            "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_jogokaryan.stream/playlist.m3u8",
            "lat": -7.82412,
            "lng": 110.36781,
            "connected": True,
        }
    },
    {
        "type": "location-pins",
        "id": "10",
        "attributes": {
            "slug": "simpang-glagahsari",
            "name": "Simpang Empat Glagahsari",
            "alias_name": "Simpang Glagahsari Umbulharjo",
            "group_name": "Dishub Kota Yogyakarta - ATCS",
            "pin_type": "cctv",
            "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_Glagahsari.stream/playlist.m3u8",
            "lat": -7.80821,
            "lng": 110.38812,
            "connected": True,
        }
    },
    {
        "type": "location-pins",
        "id": "11",
        "attributes": {
            "slug": "simpang-serangan",
            "name": "Simpang Serangan Notoprajan",
            "alias_name": "Simpang Serangan Notoprajan",
            "group_name": "Dishub Kota Yogyakarta - ATCS",
            "pin_type": "cctv",
            "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_serangan.stream/playlist.m3u8",
            "lat": -7.80312,
            "lng": 110.35789,
            "connected": True,
        }
    },
    {
        "type": "location-pins",
        "id": "12",
        "attributes": {
            "slug": "simpang-ukdw",
            "name": "Simpang Tiga UKDW",
            "alias_name": "Simpang UKDW Duta Wacana",
            "group_name": "Dishub Kota Yogyakarta - ATCS",
            "pin_type": "cctv",
            "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_ukdw.stream/playlist.m3u8",
            "lat": -7.78912,
            "lng": 110.37891,
            "connected": True,
        }
    }
]

# ==================================================
# KONFIGURASI MODEL YOLO
# ==================================================
YOLO_MODEL_PATH = WEIGHTS_DIR / "yolov8n.pt"
YOLO_CONFIDENCE = 0.45          # Threshold kepercayaan deteksi (0.0 - 1.0)
YOLO_IOU_THRESHOLD = 0.45       # Threshold IoU untuk NMS
YOLO_TARGET_CLASSES = [2, 3]    # COCO class IDs: 2=car, 3=motorcycle

# Mapping class ID COCO ke nama kendaraan
VEHICLE_CLASS_NAMES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

# ==================================================
# KONFIGURASI VIDEO
# ==================================================
VIDEO_RESOLUTION = (1280, 720)  # Resolusi target (lebar x tinggi)
FRAME_SKIP = 2                  # Proses 1 frame setiap N frame (hemat CPU)
MAX_STREAM_RETRY = 5            # Jumlah retry jika koneksi stream putus

# ==================================================
# KONFIGURASI DETEKSI LAMPU MERAH
# ==================================================
TRAFFIC_LIGHT_DETECT_METHOD = "color"   # Deteksi berbasis warna piksel dominan

# Batas warna MERAH dalam ruang warna HSV (dua rentang karena merah melingkar di hue)
RED_LOWER_1 = (0, 100, 100)
RED_UPPER_1 = (10, 255, 255)
RED_LOWER_2 = (160, 100, 100)
RED_UPPER_2 = (180, 255, 255)

# Luas area merah (piksel) agar dianggap lampu MERAH aktif
RED_PIXEL_THRESHOLD = 200

# ==================================================
# KONFIGURASI TITIK SIMPANG YOGYAKARTA
# ==================================================
# Format:
#   "source": path video lokal ATAU URL YouTube Live
#   "stopline": (x1, y1, x2, y2)       → garis henti virtual
#   "traffic_light_roi": (x, y, w, h)  → area crop lampu lalu lintas
LOCATION_CONFIGS = {
    "simpang_tugu": {
        "name": "Simpang Tugu Pal Putih (Live CCTV)",
        "source": "https://cctvjss.jogjakota.go.id/atcs/ATCS_Simpang_Tugu.stream/playlist.m3u8",
        "source_type": "hls",          # "file" | "youtube" | "hls"
        "stopline": (50, 420, 900, 420),
        "traffic_light_roi": (880, 50, 120, 180),
        "description": "Persimpangan Tugu Pal Putih - ATCS Dishub Kota Yogyakarta",
    },
    "simpang_kmnol": {
        "name": "Simpang Titik Nol Km Malioboro (Live CCTV)",
        "source": "https://cctvjss.jogjakota.go.id/atcs/ATCS_kmnol.stream/playlist.m3u8",
        "source_type": "hls",
        "stopline": (60, 430, 920, 430),
        "traffic_light_roi": (850, 40, 130, 190),
        "description": "Simpang Titik Nol Kilometer Malioboro - ATCS Dishub Kota Yogyakarta",
    },
    "simpang_gramedia": {
        "name": "Simpang Empat Gramedia Sudirman (Live CCTV)",
        "source": "https://cctvjss.jogjakota.go.id/atcs/ATCS_gramedia.stream/playlist.m3u8",
        "source_type": "hls",
        "stopline": (80, 400, 850, 400),
        "traffic_light_roi": (800, 60, 130, 200),
        "description": "Persimpangan Gramedia - Jl. Jend. Sudirman",
    },
    "simpang_gondomanan": {
        "name": "Simpang Empat Gondomanan (Live CCTV)",
        "source": "https://cctvjss.jogjakota.go.id/atcs/ATCS_gondomanan.stream/playlist.m3u8",
        "source_type": "hls",
        "stopline": (70, 410, 880, 410),
        "traffic_light_roi": (820, 50, 130, 180),
        "description": "Persimpangan Gondomanan - Jl. Brigjend Katamso",
    },
    "simpang_wirobrajan": {
        "name": "Simpang Empat Wirobrajan (Live CCTV)",
        "source": "https://cctvjss.jogjakota.go.id/atcs/ATCS_wirobrajan.stream/playlist.m3u8",
        "source_type": "hls",
        "stopline": (60, 420, 900, 420),
        "traffic_light_roi": (840, 50, 130, 180),
        "description": "Persimpangan Wirobrajan - Jl. KH. Ahmad Dahlan",
    },
    # ─────────────────────────────────────────────────────────────────────────
    # LOKASI CCTV REAL-TIME — HLS Stream dari API ATCS Jogja Istimewa
    # ─────────────────────────────────────────────────────────────────────────
    "cctv_live": {
        "name": "CCTV Live — Dipilih dari Dashboard",
        "source": "https://cctvjss.jogjakota.go.id/atcs/ATCS_Simpang_Tugu.stream/playlist.m3u8",
        "source_type": "hls",
        "stopline": (50, 400, 1230, 400),
        "traffic_light_roi": (900, 30, 150, 200),
        "description": "CCTV Lampu Merah ATCS Jogja Istimewa — Real-time HLS Stream",
    },
    "demo": {
        "name": "Demo Mode (Video Sampel Lokal)",
        "source": str(DATASET_DIR / "sample_day.mp4"),
        "source_type": "file",
        "stopline": (100, 380, 750, 380),
        "traffic_light_roi": (700, 30, 100, 150),
        "description": "Mode demonstrasi cadangan menggunakan video lokal",
    },
}

DEFAULT_LOCATION = "simpang_tugu"

# ==================================================
# KONFIGURASI TRACKER (ByteTrack via Ultralytics)
# ==================================================
TRACKER_MAX_AGE = 30        # Frame sebelum track dianggap hilang
TRACKER_MIN_HITS = 3        # Minimal deteksi sebelum track dikonfirmasi
# TRACKER_IOU_THRESHOLD ditangani internal oleh ByteTrack

# ==================================================
# KONFIGURASI OUTPUT & LOGGING
# ==================================================
LOG_INTERVAL_SECONDS = 5
EVIDENCE_CROP_PADDING = 30      # Padding piksel saat crop foto bukti

# ==================================================
# KONFIGURASI DASHBOARD STREAMLIT
# ==================================================
DASHBOARD_REFRESH_INTERVAL = 10  # Detik antara auto-refresh
MAX_GALLERY_IMAGES = 20          # Maks gambar bukti di galeri

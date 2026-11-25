# 🚦 Project Planning: Traffic Light Violation Detection System (Yogyakarta Edition)

Dokumen ini berisi cetak biru (blueprint), spesifikasi, alur kerja, dan rencana implementasi sistem deteksi pelanggaran lampu merah berbasis _Computer Vision_ untuk pemantauan akumulatif 1x24 jam di wilayah Yogyakarta.

---

## 📌 1. Ruang Lingkup Proyek (Scope of Work)

- **Target Objek:** Kendaraan bermotor (Fokus utama pada mobil dan sepeda motor karena volume kendaraan roda dua yang sangat tinggi di Jogja).
- **Wilayah Pengamatan:** 1-2 titik simpang lampu merah di Yogyakarta menggunakan sumber video _live stream_ publik (kamera berjenis statis/_fixed camera_).
- **Durasi Pemantauan:** Akumulasi data statistik pelanggaran secara berkala dalam siklus **1x24 jam**.
- **Output Utama:**
  1. Mesin deteksi berbasis Python (YOLOv8 + OpenCV + Tracker).
  2. Basis data (Database) lokal sebagai penyimpanan log pelanggaran dan berkas foto bukti.
  3. Dashboard berbasis web (_Streamlit_) untuk visualisasi statistik pelanggar.

---

## 🛠️ 2. Kebutuhan Komponen & Spesifikasi Teknis

### A. Data & Sumber Gambar (Dataset)

- **Sumber Utama:** _Stream_ video dari YouTube Channel Resmi **CCTV Pemkot Yogyakarta** atau **CCTV Jogja Istimewa (Kominfo DIY)**.
- **Variasi Kondisi:** Sampel rekaman kondisi **Siang Hari** (terang, kontras tinggi) dan **Malam Hari** (minim cahaya, silau lampu kendaraan).

### B. Perangkat Lunak & Pustaka Python (Software Libraries)

- **Deteksi Objek (AI):** `ultralytics` (YOLOv8) untuk mengenali jenis kendaraan secara _real-time_.
- **Pelacakan Objek (Object Tracking):** `deep-sort-realtime` atau `ByteTrack` untuk memberikan ID unik pada tiap kendaraan agar tidak terhitung ganda.
- **Pemrosesan Citra:** `opencv-python` untuk manipulasi video, menggambar garis henti virtual, dan mendeteksi perubahan status warna lampu.
- **Koneksi Streaming:** `yt-dlp` untuk membaca data _raw stream_ dari YouTube Live.
- **Penyimpanan:** `SQLite` (database relasional lokal yang ringan).
- **Antarmuka Visual:** `streamlit` bersama pustaka `pandas` dan `plotly` untuk membuat grafik dashboard interaktif.

---

## 📂 3. Desain Struktur Folder Proyek

```text
traffic-violation-jogja/
│
├── dataset/                  # Berisi file video sampel CCTV (siang & malam)
│   ├── sample_day.mp4
│   └── sample_night.mp4
│
├── weights/                  # Menyimpan model YOLO pre-trained (.pt)
│   └── yolov8n.pt
│
├── database/                 # Berisi file database SQLite dan log data
│   ├── violations.db
│   └── schema.sql
│
├── src/                      # Source code inti program
│   ├── __init__.py
│   ├── config.py             # Pengaturan koordinat garis virtual tiap simpang
│   ├── traffic_engine.py     # Logika inti (YOLO + Line Crossing + Status Lampu)
│   └── db_manager.py         # Fungsi untuk melakukan simpan/ambil data ke SQLite
│
├── app.py                    # Aplikasi dashboard visualisasi Streamlit
├── requirements.txt          # Daftar pustaka Python yang wajib diinstal
└── PLANNING.md               # Dokumen rencana kerja (File ini)
```

---

## 🗓️ 4. Tahapan Implementasi (Milestones)

### FASE 1: Pengumpulan Data & Analisis Simpang (Minggu 1)

- [ ] Menentukan titik lampu merah target di Jogja yang memiliki kamera statis (contoh: Simpang Gramedia, Tugu, atau Gejayan).
- [ ] Merekam sampel video 10-15 menit (versi siang dan malam) menggunakan skrip `yt-dlp` + `OpenCV` sebagai dataset lokal untuk eksperimen.
- [ ] Memetakan koordinat piksel untuk posisi lampu lalu lintas dan posisi garis henti (_stopline_) virtual pada video.

### FASE 2: Pengembangan Core Engine Deteksi (Minggu 2)

- [ ] Mengintegrasikan YOLOv8 untuk memastikan akurasi deteksi kelas `car` dan `motorcycle` pada sudut pandang CCTV Jogja yang tinggi.
- [ ] Menerapkan algoritme _Object Tracking_ agar setiap kendaraan terkunci dengan ID yang unik selama berada dalam _frame_.
- [ ] Menyusun logika kalkulasi pelanggaran: _JIKA status lampu = MERAH DAN titik koordinat kendaraan memotong GARIS VIRTUAL, MAKA trigger counter pelanggaran._

### FASE 3: Manajemen Data & Optimasi Sistem 24 Jam (Minggu 3)

- [ ] Membuat skema database SQLite yang mencatat: `timestamp`, `cctv_location`, `vehicle_type`, `vehicle_id`, dan `evidence_img_path`.
- [ ] Membuat fungsi pemotongan (_cropping_) otomatis gambar kendaraan yang melanggar untuk dijadikan file bukti visual.
- [ ] **Optimasi Performa:** Menerapkan fitur _Frame Skipping_ dan menonaktifkan pemrosesan deteksi kendaraan jika status lampu lalu lintas sedang HIJAU (menghemat daya komputasi laptop untuk durasi 24 jam).

### FASE 4: Pembangunan Dashboard Visualisasi (Minggu 4)

- [ ] Membangun antarmuka web interaktif menggunakan Streamlit (`app.py`).
- [ ] Menampilkan indikator angka (_Live Counter_) total pelanggaran hari ini yang diambil langsung dari database.
- [ ] Membuat visualisasi tren jam rawan pelanggaran dalam siklus 24 jam menggunakan grafik garis (_Plotly_).
- [ ] Menyediakan tabel log data kejadian lengkap dengan galeri foto kendaraan yang melanggar.
- [ ] Melakukan pengujian sistem secara menyeluruh (_End-to-End Testing_).

---

## 📊 5. Skema Struktur Database (SQLite)

Tabel berikut akan secara otomatis mencatat setiap detail kejadian menerobos lampu merah:

```sql
CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    cctv_location TEXT NOT NULL,
    vehicle_type TEXT NOT NULL,
    vehicle_id INTEGER NOT NULL,
    evidence_img_path TEXT NOT NULL
);
```

---

## ⚠️ 6. Identifikasi Risiko & Mitigasi

1.  **Risiko Kerapatan Kendaraan Tinggi (Khas Jogja):** Saat lampu merah, motor menumpuk sangat rapat di depan sehingga kotak pembatas (_bounding box_) model rentan tumpang tindih (_occlusion_).
    - _Mitigasi:_ Garis virtual diletakkan sedikit maju di area kosong sebelum zebra cross agar kendaraan terdeteksi satu per satu saat mereka mulai bergerak menerobos.
2.  **Risiko Beban Komputasi 24 Jam:** Menjalankan model _deep learning_ tanpa henti dapat menyebabkan memori penuh (_memory leak_) atau laptop _overheat_.
    - _Mitigasi:_ Menggunakan model YOLOv8 versi paling ringan (`yolov8n.pt`) dan membatasi input video ke resolusi menengah (misal 720p).

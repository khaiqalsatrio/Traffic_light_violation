# 🚦 Traffic Light Violation Detection System
### Yogyakarta Edition — Sistem Deteksi Pelanggaran Lampu Merah Berbasis Computer Vision

---

## 📋 Deskripsi Proyek

Sistem otomatis berbasis **AI** untuk mendeteksi, melacak, dan merekam kendaraan yang menerobos lampu merah di persimpangan Yogyakarta. Sistem bekerja selama **1x24 jam** secara akumulatif menggunakan video CCTV statis.

---

## 🏗 Struktur Proyek

```
traffic-violation-jogja/
│
├── dataset/                  # File video sampel CCTV (siang & malam)
│   ├── sample_day.mp4
│   └── sample_night.mp4
│
├── weights/                  # Model YOLO pre-trained (.pt)
│   └── yolov8n.pt            # Auto-download saat pertama kali run
│
├── database/                 # Schema database
│   └── schema.sql            # DDL PostgreSQL
│
├── evidence_images/          # Folder penyimpanan foto bukti pelanggaran
│
├── src/                      # Source code inti
│   ├── __init__.py
│   ├── config.py             # Konfigurasi koordinat & parameter sistem
│   ├── traffic_engine.py     # Core engine (YOLO + Tracker + Logika)
│   └── db_manager.py         # Operasi database PostgreSQL
│
├── app.py                    # Dashboard visualisasi Streamlit
├── requirements.txt          # Daftar dependensi Python
├── .env                      # Kredensial database (JANGAN di-commit!)
├── .gitignore
└── README.md
```

---

## ⚙️ Stack Teknologi

| Komponen | Teknologi |
|---|---|
| Deteksi Objek | YOLOv8n (Ultralytics) |
| Object Tracking | DeepSORT Realtime |
| Pemrosesan Video | OpenCV |
| Streaming | yt-dlp (YouTube Live) |
| Database | **PostgreSQL** + psycopg2 |
| Dashboard | Streamlit + Plotly |

---

## 🚀 Cara Instalasi & Menjalankan

### 1. Clone & Buat Virtual Environment

```bash
git clone <repo-url>
cd Traffic-Light-Violation-Detection-System

python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 2. Install Dependensi

```bash
pip install -r requirements.txt
```

### 3. Konfigurasi PostgreSQL

Buat database di PostgreSQL:

```sql
CREATE DATABASE traffic_violations;
```

Edit file `.env` dengan kredensial Anda:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=traffic_violations
DB_USER=postgres
DB_PASSWORD=your_password_here
```

Inisialisasi tabel (otomatis saat pertama kali engine/dashboard dijalankan, atau bisa manual):

```bash
psql -U postgres -d traffic_violations -f database/schema.sql
```

### 4. Siapkan Video Dataset

Letakkan file video CCTV ke folder `dataset/`:
- `dataset/sample_day.mp4`  — rekaman siang hari
- `dataset/sample_night.mp4` — rekaman malam hari

Atau gunakan `yt-dlp` untuk merekam dari YouTube Live:

```bash
yt-dlp -f "best[height<=720]" -o "dataset/sample_day.mp4" "URL_YOUTUBE_CCTV"
```

### 5. Konfigurasi Koordinat Simpang

Edit `src/config.py` pada bagian `LOCATION_CONFIGS`, sesuaikan:
- **`stopline`**: Koordinat piksel garis henti virtual `(x1, y1, x2, y2)`
- **`traffic_light_roi`**: Koordinat area lampu lalu lintas `(x, y, width, height)`

> **Tips**: Gunakan skrip berikut untuk mencari koordinat piksel secara interaktif:
> ```python
> import cv2
> img = cv2.imread("frame_sample.jpg")
> cv2.imshow("Find Coords", img)
> cv2.setMouseCallback("Find Coords", lambda e,x,y,f,p: print(f"({x}, {y})") if e==1 else None)
> cv2.waitKey(0)
> ```

---

## ▶️ Menjalankan Sistem

### A. Core Detection Engine

```bash
# Mode demo (gunakan video lokal)
python src/traffic_engine.py --location demo

# Pilih lokasi spesifik
python src/traffic_engine.py --location simpang_tugu

# Mode headless (tanpa jendela preview, cocok untuk server)
python src/traffic_engine.py --location simpang_tugu --no-preview

# Lihat semua opsi
python src/traffic_engine.py --help
```

Tekan **Q** pada jendela preview untuk menghentikan engine.

### B. Dashboard Visualisasi

```bash
streamlit run app.py
```

Dashboard akan terbuka di browser: `http://localhost:8501`

---

## 🗄 Skema Database PostgreSQL

```sql
CREATE TABLE violations (
    id                SERIAL PRIMARY KEY,
    timestamp         TIMESTAMPTZ DEFAULT NOW(),
    cctv_location     TEXT NOT NULL,
    vehicle_type      TEXT NOT NULL,  -- 'car' | 'motorcycle' | 'bus' | 'truck'
    vehicle_id        INTEGER NOT NULL,
    evidence_img_path TEXT NOT NULL
);
```

---

## 📊 Fitur Dashboard

| Fitur | Deskripsi |
|---|---|
| **Live Counter** | Total pelanggaran hari ini secara real-time |
| **Tren Per Jam** | Grafik garis 24 jam dengan highlight jam rawan |
| **Breakdown Kendaraan** | Pie chart proporsi motor vs mobil |
| **Ringkasan 7 Hari** | Bar chart tren mingguan |
| **Log Tabel** | Tabel lengkap semua kejadian + export CSV |
| **Galeri Bukti** | Grid foto crop kendaraan pelanggar |
| **Auto-Refresh** | Update otomatis setiap 10 detik |

---

## ⚠️ Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| Kepadatan kendaraan tinggi (khas Jogja) → occlusion | Garis virtual diletakkan di area agak maju sebelum zebra cross |
| Beban komputasi 24 jam | YOLO hanya aktif saat lampu MERAH + Frame Skip setiap 2 frame |
| Memory leak jangka panjang | Model `yolov8n` (paling ringan) + resolusi dibatasi 720p |
| Stream YouTube terputus | Auto-retry hingga 5x dengan delay 10 detik |

---

## 📜 Lisensi

Proyek ini dikembangkan untuk keperluan penelitian dan pemantauan lalu lintas di Yogyakarta.

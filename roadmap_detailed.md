# Roadmap Detailed — Traffic Light Violation Detection System
**Yogyakarta Smart City & ATCS Edition**

---

## 1. Diagram Alur Sistem End-to-End

Berikut adalah alur pergerakan data dari video feed CCTV ATCS Yogyakarta hingga masuk ke basis data dan dashboard pemantauan Anda:

```mermaid
graph TD
    %% Styling box
    classDef stepBox fill:#1e293b,stroke:#3b82f6,stroke-width:1.5px,color:#f8fafc;
    classDef decisionBox fill:#1e293b,stroke:#f59e0b,stroke-width:1.5px,color:#f8fafc;
    classDef actionBox fill:#1e293b,stroke:#10b981,stroke-width:1.5px,color:#f8fafc;
    classDef alertBox fill:#1e293b,stroke:#ef4444,stroke-width:1.5px,color:#f8fafc;

    subgraph S1["1. Video Stream Ingestion"]
        A["📡 Live HLS Stream CCTV Jogja<br/>(cctv.jogjaprov.go.id / ATCS)"]:::stepBox
        A -->|"HTTP Live Streaming (.m3u8)"| B["🎥 Video Capture & Frame Resizer<br/>(OpenCV 1024x576 @ 30 FPS)"]:::stepBox
    end

    subgraph S2["2. AI Perception & Tracking Engine"]
        B -->|"Raw Video Frames"| C["🧠 YOLOv8n Object Detector<br/>(Class: Mobil, Sepeda Motor, Bus, Truk)"]:::stepBox
        C -->|"Bounding Boxes + Confidences"| D["🎯 ByteTrack Association<br/>(Tracking ID & Kecepatan Perpindahan)"]:::stepBox
    end

    subgraph S3["3. Traffic Light & Stopline Logic"]
        D --> E{"🚦 Cek Status Lampu Lalu Lintas"}:::decisionBox
        E -->|"Lampu Hijau"| F["🟢 Jalur Aman<br/>(Bebas Melintas / Jarak Netral)"]:::actionBox
        E -->|"Lampu Merah"| G["📏 Hitung Jarak Bumper ke Stopline<br/>(dist_px = Stopline_Y - Y2)"]:::stepBox
        
        G --> H{"Apakah Bumper Memotong /<br/>Melewati Garis Henti?"}:::decisionBox
        H -->|"Jarak > 0 px (Belum Lewat)"| I["⚠️ Status: Mendekati Garis<br/>(HUD Amber: ~X.X m)"]:::actionBox
        H -->|"Jarak <= 0 px (Memotong Garis)"| J["🚨 TRIGGER PELANGGARAN DETECTED!"]:::alertBox
    end

    subgraph S4["4. Evidence Capture & Persistence"]
        J --> K["📸 Auto-Crop Foto Bukti Pelanggaran<br/>(Annotated BBox + Timestamp Overlay)"]:::stepBox
        K --> L["💾 Simpan Snapshot ke Berkas Lokal<br/>(data/violations/evidence_*.jpg)"]:::stepBox
        L --> M["🗄️ Insert Record ke Database<br/>(PostgreSQL / SQLite violations table)"]:::stepBox
    end

    subgraph S5["5. Dashboard Visualization & Live Alert"]
        F --> N["🖥️ Streamlit Realtime Web Dashboard<br/>(HUD Frame, Status Lampu & Counter)"]:::stepBox
        I --> N
        M --> N
        M --> O["📊 Modul Analitik & Grafik Harian<br/>(Plotly: Jam Rawan & Distribusi Kendaraan)"]:::stepBox
        M --> P["🖼️ Tab Galeri Bukti Pelanggaran<br/>(Preview Foto, Nopol & Lokasi Simpang)"]:::stepBox
    end
```

---

## 2. Diagram Interaksi Siklus Hidup Deteksi Pelanggaran (Violation Lifecycle)

Diagram interaksi berikut menunjukkan bagaimana sebuah kendaraan dipantau dari saat pertama kali memasuki kamera hingga pencatatan bukti tilang:

```mermaid
sequenceDiagram
    autonumber
    actor Kendaraan as 🚗 Kendaraan di Simpang
    participant CCTV as 📹 CCTV ATCS Jogja
    participant Engine as ⚙️ TrafficViolationEngine
    participant YOLO as 🧠 YOLOv8 + ByteTrack
    participant Logic as 📏 Stopline & Light Logic
    participant DB as 🗄️ Database (PostgreSQL)
    participant UI as 🖥️ Dashboard Streamlit

    Kendaraan->>CCTV: Melintas di area persimpangan
    loop Setiap Frame Video (30 FPS)
        CCTV->>Engine: Stream HLS Video Chunk (.ts)
        Engine->>YOLO: Kirim frame citra (1024x576)
        activate YOLO
        YOLO-->>Engine: Hasil deteksi: Bounding Box [x1, y1, x2, y2] + ID unik
        deactivate YOLO
        
        Engine->>Logic: Evaluasi: Posisi Y bumper vs Garis Henti & Status Lampu
        
        alt Status Lampu: HIJAU
            Logic-->>Engine: Aman (Jalur Hijau)
            Engine->>UI: Render kotak deteksi HIJAU + Label Jarak
        else Status Lampu: MERAH & Jarak > 0 meter
            Logic-->>Engine: Peringatan (Mendekati Garis Henti)
            Engine->>UI: Render kotak deteksi ORANYE + Label Jarak (~2.5m)
        else Status Lampu: MERAH & Jarak <= 0 meter (Melanggar Garis)
            rect rgb(45, 20, 20)
                Logic-->>Engine: PELANGGARAN TERKONFIRMASI!
                Engine->>Engine: Crop frame bukti & render watermark teks
                Engine->>DB: INSERT INTO violations (timestamp, location, vehicle_type, vehicle_id, evidence_path)
                DB-->>Engine: Record tersimpan (ID: #102)
                Engine->>UI: Render kotak deteksi MERAH (LEWAT GARIS MELANGGAR!)
                Engine->>UI: Update Live Counter Pelanggaran (+1)
                Engine->>UI: Tambahkan foto bukti ke Galeri Pelanggaran
            end
        end
    end
```

---

## 3. Diagram Arsitektur Komponen Sistem (Component & Data Flow)

Diagram berikut memetakan keterhubungan antar modul kode sumber di dalam proyek:

```mermaid
graph LR
    classDef config fill:#1e293b,stroke:#64748b,stroke-width:1.5px,color:#f8fafc;
    classDef core fill:#1e3a5f,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef db fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef view fill:#4c1d95,stroke:#a855f7,stroke-width:2px,color:#f8fafc;

    subgraph CONFIG["⚙️ Konfigurasi Simpang"]
        CFG["src/config.py<br/>• LOCATION_CONFIGS (Stopline & ROI Lampu)<br/>• CCTV API Endpoints (cctv.jogjaprov.go.id)<br/>• Path & Direktori Bukti"]:::config
    end

    subgraph ENGINE["🧠 Core Processing Engine"]
        ENG["src/traffic_engine.py<br/>• _open_video_source() (HLS Reader)<br/>• _track_frame() (YOLOv8 + ByteTrack)<br/>• _draw_overlay() (Corner HUD & Distance)<br/>• _check_stopline_crossing()"]:::core
    end

    subgraph STORAGE["🗄️ Data Layer"]
        DBM["src/db_manager.py<br/>• DatabaseManager (PostgreSQL / SQLite)<br/>• add_violation()<br/>• get_violations_by_date()<br/>• get_hourly_stats()"]:::db
        SQL[("Database<br/>violations table")]:::db
    end

    subgraph APP["🖥️ Presentation Layer"]
        ST["app.py (Streamlit UI)<br/>• Tab 1: Live CCTV Lampu Merah<br/>• Tab 2: Engine Deteksi Realtime<br/>• Tab 3: Analitik & Grafik Harian<br/>• Tab 4: Log Data Pelanggaran<br/>• Tab 5: Galeri Bukti Foto"]:::view
    end

    CFG --> ENG
    ENG --> DBM
    DBM --> SQL
    ENG --> ST
    DBM --> ST
```

---

## 4. Rencana Tahapan Rilis (Milestones & Roadmap)

```mermaid
graph TD
    classDef done fill:#065f46,stroke:#34d399,stroke-width:2px,color:#fff;
    classDef active fill:#1e40af,stroke:#60a5fa,stroke-width:2px,color:#fff;
    classDef next fill:#374151,stroke:#9ca3af,stroke-width:1px,color:#e5e7eb;

    M1["✅ Milestone 1: Core AI & Live CCTV Jogja<br/>• Streaming HLS stabil 30 FPS<br/>• YOLOv8 + ByteTrack ID<br/>• Kalkulasi Jarak Bumper-ke-Garis<br/>• Auto-Snapshot & Database Logger"]:::done
    
    M2["🎯 Milestone 2: Multi-Simpang & Kalibrasi Metrik<br/>• Transformasi Perspektif (Bird's Eye View)<br/>• Estimasi Kecepatan (km/jam)<br/>• Poligon Garis Henti Miring Sesuai Simpang<br/>• Auto Deteksi Warna Lampu (HSV/CNN)"]:::active
    
    M3["💡 Milestone 3: ANPR / Identifikasi Plat Nomor<br/>• Deteksi Plat Nomor Standar Indonesia<br/>• Ekstraksi Huruf & Angka (PaddleOCR/EasyOCR)<br/>• Super-Resolution Plat Malam/Hujan"]:::next
    
    M4["⚙️ Milestone 4: Integrasi Tilang ETLE & Notifikasi<br/>• REST API Service (FastAPI)<br/>• Notifikasi Bot Instan (Telegram/WhatsApp)<br/>• Generator Surat Tilang PDF Otomatis"]:::next
    
    M5["🚀 Milestone 5: Smart City & Edge Deployment<br/>• Akselerasi TensorRT/ONNX (GPU Jetson)<br/>• Multi-Stream Worker (20+ Simpang Paralel)<br/>• S3 Cloud Storage untuk Arsip Bukti"]:::next

    M1 --> M2
    M2 --> M3
    M3 --> M4
    M4 --> M5
```

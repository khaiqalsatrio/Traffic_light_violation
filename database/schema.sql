-- =====================================================
-- Traffic Light Violation Detection System
-- Database Schema - PostgreSQL Edition
-- Yogyakarta Edition
-- =====================================================

-- Aktifkan ekstensi pgcrypto jika diperlukan (opsional)
-- CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Tabel utama untuk menyimpan log setiap pelanggaran
CREATE TABLE IF NOT EXISTS violations (
    id                SERIAL PRIMARY KEY,
    timestamp         TIMESTAMPTZ DEFAULT NOW(),
    cctv_location     TEXT NOT NULL,
    vehicle_type      TEXT NOT NULL CHECK (vehicle_type IN ('car', 'motorcycle', 'bus', 'truck')),
    vehicle_id        INTEGER NOT NULL,
    evidence_img_path TEXT NOT NULL
);

-- Tabel konfigurasi lokasi CCTV
CREATE TABLE IF NOT EXISTS cctv_locations (
    id                SERIAL PRIMARY KEY,
    name              TEXT UNIQUE NOT NULL,
    source_url        TEXT,
    stopline_y        INTEGER,
    stopline_x1       INTEGER,
    stopline_x2       INTEGER,
    traffic_light_x   INTEGER,
    traffic_light_y   INTEGER,
    is_active         BOOLEAN DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Indeks untuk mempercepat query berdasarkan waktu, lokasi, dan tipe kendaraan
CREATE INDEX IF NOT EXISTS idx_violations_timestamp     ON violations(timestamp);
CREATE INDEX IF NOT EXISTS idx_violations_location      ON violations(cctv_location);
CREATE INDEX IF NOT EXISTS idx_violations_vehicle_type  ON violations(vehicle_type);
CREATE INDEX IF NOT EXISTS idx_violations_date      ON violations(((timestamp AT TIME ZONE 'UTC')::date));

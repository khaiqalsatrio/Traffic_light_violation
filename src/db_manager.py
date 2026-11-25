# =====================================================
# db_manager.py - Manajemen Database PostgreSQL
# Traffic Light Violation Detection System
# Yogyakarta Edition
# =====================================================

import logging
import psycopg2
import psycopg2.extras
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# Import konfigurasi (relative import — file ini berada di dalam package src)
from .config import DB_CONFIG, SCHEMA_PATH

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Mengelola semua operasi baca/tulis ke database PostgreSQL.
    Menyimpan log pelanggaran lampu merah beserta path foto bukti.
    """

    def __init__(self, db_config: dict = None, schema_path: str = None):
        """
        Inisialisasi koneksi database PostgreSQL.

        Args:
            db_config: Dict konfigurasi koneksi (host, port, dbname, user, password).
                       Jika None, gunakan DB_CONFIG dari config.py.
            schema_path: Path ke file .sql untuk inisialisasi tabel.
        """
        self.db_config = db_config or DB_CONFIG
        self.schema_path = schema_path or str(SCHEMA_PATH)
        self._init_database()
        logger.info(
            f"✅ Database PostgreSQL terhubung: "
            f"{self.db_config['user']}@{self.db_config['host']}:{self.db_config['port']}"
            f"/{self.db_config['dbname']}"
        )

    @contextmanager
    def _get_connection(self):
        """Context manager: buat koneksi, lakukan operasi, tutup koneksi."""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except psycopg2.OperationalError as e:
            logger.error(f"❌ Koneksi ke PostgreSQL gagal: {e}")
            raise
        finally:
            if conn and not conn.closed:
                conn.close()

    def _init_database(self):
        """
        Menjalankan schema SQL untuk membuat tabel jika belum ada.
        Dipanggil sekali saat inisialisasi DatabaseManager.
        """
        schema_file = Path(self.schema_path)
        if not schema_file.exists():
            logger.warning(f"Schema file tidak ditemukan: {self.schema_path}")
            return

        with open(schema_file, "r", encoding="utf-8") as f:
            sql_script = f.read()

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql_script)
                conn.commit()
                logger.info("📋 Schema database berhasil diinisialisasi.")
        except psycopg2.Error as e:
            logger.error(f"❌ Gagal menginisialisasi schema: {e}")
            raise

    # --------------------------------------------------
    # FUNGSI TULIS (CREATE)
    # --------------------------------------------------

    def save_violation(
        self,
        cctv_location: str,
        vehicle_type: str,
        vehicle_id: int,
        evidence_img_path: str,
    ) -> Optional[int]:
        """
        Menyimpan satu kejadian pelanggaran ke database.

        Args:
            cctv_location:     Nama lokasi CCTV (mis: "simpang_tugu")
            vehicle_type:      Jenis kendaraan ('car' atau 'motorcycle')
            vehicle_id:        ID unik kendaraan dari tracker
            evidence_img_path: Path absolut ke file foto bukti

        Returns:
            ID baris yang baru dibuat (int), atau None jika gagal
        """
        sql = """
            INSERT INTO violations (cctv_location, vehicle_type, vehicle_id, evidence_img_path)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (cctv_location, vehicle_type, vehicle_id, evidence_img_path))
                    new_id = cur.fetchone()[0]
                conn.commit()
                logger.info(
                    f"✅ Pelanggaran tersimpan [ID:{new_id}] | "
                    f"{cctv_location} | {vehicle_type} #{vehicle_id}"
                )
                return new_id
        except psycopg2.Error as e:
            logger.error(f"❌ Gagal menyimpan pelanggaran: {e}")
            return None

    # --------------------------------------------------
    # FUNGSI BACA (READ)
    # --------------------------------------------------

    def get_total_today(self, location: str = None) -> int:
        """
        Menghitung total pelanggaran hari ini.

        Args:
            location: Filter berdasarkan lokasi (opsional)

        Returns:
            Jumlah total pelanggaran hari ini (int)
        """
        if location:
            sql = """
                SELECT COUNT(*) FROM violations
                WHERE DATE(timestamp AT TIME ZONE 'Asia/Jakarta') = CURRENT_DATE
                AND cctv_location = %s
            """
            params = (location,)
        else:
            sql = """
                SELECT COUNT(*) FROM violations
                WHERE DATE(timestamp AT TIME ZONE 'Asia/Jakarta') = CURRENT_DATE
            """
            params = ()

        rows = self._fetch_all(sql, params)
        return rows[0]["count"] if rows else 0

    def get_today_violations(self, location: str = None) -> List[Dict]:
        """
        Mengambil semua pelanggaran yang terjadi hari ini.

        Args:
            location: Filter berdasarkan lokasi CCTV (opsional)

        Returns:
            List of dicts data pelanggaran hari ini, terurut terbaru dulu
        """
        if location:
            sql = """
                SELECT id, timestamp AT TIME ZONE 'Asia/Jakarta' AS timestamp,
                       cctv_location, vehicle_type, vehicle_id, evidence_img_path
                FROM violations
                WHERE DATE(timestamp AT TIME ZONE 'Asia/Jakarta') = CURRENT_DATE
                AND cctv_location = %s
                ORDER BY timestamp DESC
            """
            params = (location,)
        else:
            sql = """
                SELECT id, timestamp AT TIME ZONE 'Asia/Jakarta' AS timestamp,
                       cctv_location, vehicle_type, vehicle_id, evidence_img_path
                FROM violations
                WHERE DATE(timestamp AT TIME ZONE 'Asia/Jakarta') = CURRENT_DATE
                ORDER BY timestamp DESC
            """
            params = ()

        return self._fetch_all(sql, params)

    def get_violations_by_hour(self, date: str = None, location: str = None) -> List[Dict]:
        """
        Mengambil jumlah pelanggaran per jam (0-23) untuk grafik tren.

        Args:
            date:     Tanggal format 'YYYY-MM-DD' (default: hari ini)
            location: Filter berdasarkan lokasi (opsional)

        Returns:
            List of dicts dengan kolom 'hour' (int) dan 'count' (int)
        """
        date_filter = date or "CURRENT_DATE"

        if location:
            sql = """
                SELECT EXTRACT(HOUR FROM timestamp AT TIME ZONE 'Asia/Jakarta')::INT AS hour,
                       COUNT(*) AS count
                FROM violations
                WHERE DATE(timestamp AT TIME ZONE 'Asia/Jakarta') = %s::DATE
                AND cctv_location = %s
                GROUP BY hour
                ORDER BY hour
            """
            params = (date_filter if date else datetime.now().strftime("%Y-%m-%d"), location)
        else:
            sql = """
                SELECT EXTRACT(HOUR FROM timestamp AT TIME ZONE 'Asia/Jakarta')::INT AS hour,
                       COUNT(*) AS count
                FROM violations
                WHERE DATE(timestamp AT TIME ZONE 'Asia/Jakarta') = %s::DATE
                GROUP BY hour
                ORDER BY hour
            """
            params = (date if date else datetime.now().strftime("%Y-%m-%d"),)

        return self._fetch_all(sql, params)

    def get_violations_by_vehicle_type(self, date: str = None, location: str = None) -> List[Dict]:
        """
        Breakdown pelanggaran berdasarkan jenis kendaraan.

        Returns:
            List of dicts dengan 'vehicle_type' dan 'count'
        """
        date_val = date or datetime.now().strftime("%Y-%m-%d")
        if location:
            sql = """
                SELECT vehicle_type, COUNT(*) AS count
                FROM violations
                WHERE DATE(timestamp AT TIME ZONE 'Asia/Jakarta') = %s::DATE
                AND cctv_location = %s
                GROUP BY vehicle_type
                ORDER BY count DESC
            """
            params = (date_val, location)
        else:
            sql = """
                SELECT vehicle_type, COUNT(*) AS count
                FROM violations
                WHERE DATE(timestamp AT TIME ZONE 'Asia/Jakarta') = %s::DATE
                GROUP BY vehicle_type
                ORDER BY count DESC
            """
            params = (date_val,)

        return self._fetch_all(sql, params)

    def get_recent_violations(self, limit: int = 20, location: str = None) -> List[Dict]:
        """
        Mengambil N pelanggaran terbaru untuk tabel log di dashboard.

        Args:
            limit:    Jumlah maksimum baris
            location: Filter berdasarkan lokasi (opsional)

        Returns:
            List of dicts pelanggaran terbaru
        """
        if location:
            sql = """
                SELECT id, timestamp AT TIME ZONE 'Asia/Jakarta' AS timestamp,
                       cctv_location, vehicle_type, vehicle_id, evidence_img_path
                FROM violations
                WHERE cctv_location = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            params = (location, limit)
        else:
            sql = """
                SELECT id, timestamp AT TIME ZONE 'Asia/Jakarta' AS timestamp,
                       cctv_location, vehicle_type, vehicle_id, evidence_img_path
                FROM violations
                ORDER BY timestamp DESC
                LIMIT %s
            """
            params = (limit,)

        return self._fetch_all(sql, params)

    def get_weekly_summary(self) -> List[Dict]:
        """
        Ringkasan jumlah pelanggaran per hari selama 7 hari terakhir.

        Returns:
            List of dicts dengan 'date' dan 'count'
        """
        sql = """
            SELECT DATE(timestamp AT TIME ZONE 'Asia/Jakarta') AS date,
                   COUNT(*) AS count
            FROM violations
            WHERE timestamp >= NOW() - INTERVAL '7 days'
            GROUP BY date
            ORDER BY date
        """
        return self._fetch_all(sql, ())

    def get_peak_hour(self, date: str = None) -> Optional[Dict]:
        """
        Mencari jam paling rawan pelanggaran pada tanggal tertentu.

        Returns:
            Dict {'hour': int, 'count': int} atau None jika tidak ada data
        """
        date_val = date or datetime.now().strftime("%Y-%m-%d")
        sql = """
            SELECT EXTRACT(HOUR FROM timestamp AT TIME ZONE 'Asia/Jakarta')::INT AS hour,
                   COUNT(*) AS count
            FROM violations
            WHERE DATE(timestamp AT TIME ZONE 'Asia/Jakarta') = %s::DATE
            GROUP BY hour
            ORDER BY count DESC
            LIMIT 1
        """
        rows = self._fetch_all(sql, (date_val,))
        return rows[0] if rows else None

    def get_all_locations(self) -> List[str]:
        """
        Mengambil daftar semua lokasi CCTV yang pernah tercatat.

        Returns:
            List of string nama lokasi
        """
        sql = "SELECT DISTINCT cctv_location FROM violations ORDER BY cctv_location"
        rows = self._fetch_all(sql, ())
        return [row["cctv_location"] for row in rows]

    # --------------------------------------------------
    # HELPER INTERNAL
    # --------------------------------------------------

    def _fetch_all(self, sql: str, params: tuple) -> List[Dict]:
        """
        Eksekusi query SELECT dan kembalikan semua baris sebagai list of dicts.

        Args:
            sql:    Query SQL string (gunakan %s sebagai placeholder)
            params: Tuple parameter untuk query

        Returns:
            List of dicts, atau list kosong jika error
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                    return [dict(row) for row in rows]
        except psycopg2.Error as e:
            logger.error(f"❌ Query gagal: {e}\nSQL: {sql}")
            return []

    def test_connection(self) -> bool:
        """
        Uji koneksi ke PostgreSQL server.

        Returns:
            True jika berhasil terhubung, False jika gagal
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    version = cur.fetchone()[0]
                    logger.info(f"🔗 PostgreSQL: {version}")
                    return True
        except psycopg2.Error as e:
            logger.error(f"❌ Koneksi gagal: {e}")
            return False

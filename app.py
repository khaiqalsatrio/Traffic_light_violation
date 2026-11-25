# =====================================================
# app.py - Dashboard Visualisasi Streamlit
# Traffic Light Violation Detection System
# Yogyakarta Edition
# =====================================================

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
from pathlib import Path
import os
import time
import copy
import threading
import queue
import requests
import base64
import cv2

# Import dari package src
from src.db_manager import DatabaseManager
from src.config import LOCATION_CONFIGS, DASHBOARD_REFRESH_INTERVAL, MAX_GALLERY_IMAGES, CCTV_JOGJA_API, FALLBACK_JOGJA_CCTV
from src.traffic_engine import TrafficViolationEngine, fetch_jogja_cctv_cameras

# =====================================================
# KONFIGURASI HALAMAN
# =====================================================
st.set_page_config(
    page_title="Traffic Violation Monitor – Yogyakarta",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================
# CUSTOM CSS – DARK THEME PREMIUM
# =====================================================
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    /* Root & background */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #0d1225 50%, #0a1628 100%);
        color: #e2e8f0;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1629 0%, #111827 100%);
        border-right: 1px solid rgba(99, 179, 237, 0.15);
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #63b3ed;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(15,22,48,0.9) 0%, rgba(17,24,39,0.9) 100%);
        border: 1px solid rgba(99,179,237,0.2);
        border-radius: 16px;
        padding: 20px 24px !important;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 24px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(99,179,237,0.15);
    }
    [data-testid="metric-container"] label {
        color: #94a3b8 !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #e2e8f0 !important;
        font-size: 2.4rem !important;
        font-weight: 700 !important;
        line-height: 1.1 !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-size: 0.82rem !important;
    }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #63b3ed;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 2px solid rgba(99,179,237,0.3);
    }

    /* Status badge */
    .badge-red {
        display: inline-block;
        background: linear-gradient(135deg, #7f1d1d, #991b1b);
        color: #fca5a5;
        border: 1px solid rgba(252,165,165,0.3);
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .badge-green {
        display: inline-block;
        background: linear-gradient(135deg, #14532d, #166534);
        color: #86efac;
        border: 1px solid rgba(134,239,172,0.3);
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.05em;
    }

    /* Stat card custom */
    .stat-card {
        background: linear-gradient(135deg, rgba(15,22,48,0.95), rgba(17,24,39,0.95));
        border: 1px solid rgba(99,179,237,0.18);
        border-radius: 14px;
        padding: 20px;
        text-align: center;
        backdrop-filter: blur(8px);
    }
    .stat-card .stat-value {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #63b3ed, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1;
    }
    .stat-card .stat-label {
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 6px;
    }

    /* Dataframe styling */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(99,179,237,0.15);
    }

    /* Plotly chart containers */
    .js-plotly-plot {
        border-radius: 14px;
    }

    /* Divider */
    hr {
        border-color: rgba(99,179,237,0.15) !important;
        margin: 24px 0 !important;
    }

    /* Image gallery */
    .evidence-card {
        background: rgba(15,22,48,0.9);
        border: 1px solid rgba(99,179,237,0.2);
        border-radius: 12px;
        padding: 8px;
        text-align: center;
        font-size: 0.72rem;
        color: #94a3b8;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(15,22,48,0.6);
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #64748b;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e40af, #1d4ed8) !important;
        color: white !important;
    }

    /* Selectbox */
    .stSelectbox > div > div {
        background: rgba(15,22,48,0.8) !important;
        border: 1px solid rgba(99,179,237,0.2) !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# INISIALISASI DATABASE (cached per session)
# =====================================================
@st.cache_resource(show_spinner="Menghubungkan ke database...")
def get_db() -> DatabaseManager:
    return DatabaseManager()


# =====================================================
# CCTV JOGJA ISTIMEWA API – LAMPU MERAH / SIMPANG
# (CCTV_JOGJA_API diimport dari src.config)
# =====================================================

# Kata kunci yang menandakan kamera berada di simpang / lampu merah
_SIMPANG_KEYWORDS = [
    "simpang", "simpangan", "perempatan", "persimpangan",
    "lampu merah", "traffic", "atcs", "bundaran",
    "pertigaan", "junction", "signal", "sinyal",
]

# Peta wilayah berdasarkan kata kunci dalam nama grup / nama kamera
_WILAYAH_MAP = {
    "Kota Yogyakarta":  ["kota", "yogyakarta", "jogja kota", "pemkot", "kominfosan"],
    "Sleman":           ["sleman"],
    "Bantul":           ["bantul"],
    "Kulon Progo":      ["kulon progo", "kulonprogo"],
    "Gunungkidul":      ["gunungkidul", "gunung kidul"],
}

def _is_traffic_light_cam(attrs: dict) -> bool:
    """Return True jika kamera kemungkinan di simpang / lampu merah."""
    haystack = " ".join([
        (attrs.get("alias_name") or ""),
        (attrs.get("name") or ""),
        (attrs.get("group_name") or ""),
    ]).lower()
    return any(kw in haystack for kw in _SIMPANG_KEYWORDS)

def _get_wilayah(attrs: dict) -> str:
    """Tebak wilayah dari group_name / name kamera."""
    haystack = " ".join([
        (attrs.get("group_name") or ""),
        (attrs.get("alias_name") or ""),
        (attrs.get("name") or ""),
    ]).lower()
    for wilayah, keywords in _WILAYAH_MAP.items():
        if any(kw in haystack for kw in keywords):
            return wilayah
    return "Lainnya / DIY"

@st.cache_data(ttl=300, show_spinner="Mengambil daftar CCTV lampu merah Jogja...")
def fetch_jogja_cctv_list():
    """Ambil semua CCTV dari API Jogja Istimewa (publik, tanpa API key)."""
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
            resp = requests.get(f"{CCTV_JOGJA_API}/location-pins", params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", [])
            if not items:
                break
            all_data.extend(items)
            meta = data.get("meta", {}).get("page", {})
            if page >= meta.get("lastPage", 1):
                break
            page += 1
    except Exception:
        # Jika API publik tidak dapat diakses (404, offline, atau timeout),
        # gunakan basis data cadangan kamera ATCS Yogyakarta secara otomatis
        all_data = copy.deepcopy(FALLBACK_JOGJA_CCTV)

    if not all_data:
        all_data = copy.deepcopy(FALLBACK_JOGJA_CCTV)

    return all_data

def fetch_traffic_light_cctv():
    """Ambil hanya kamera CCTV yang berada di simpang / lampu merah."""
    all_items = fetch_jogja_cctv_list()
    filtered = [
        item for item in all_items
        if item.get("attributes", {}).get("stream_url")
        and item.get("attributes", {}).get("pin_type") == "cctv"
        and _is_traffic_light_cam(item.get("attributes", {}))
    ]
    return filtered if filtered else copy.deepcopy(FALLBACK_JOGJA_CCTV)

@st.cache_data
def get_sample_video_b64(filename: str = "sample_day.mp4") -> str:
    """Ambil base64 dari video rekaman CCTV real di folder dataset agar video selalu dapat diputar."""
    video_path = Path("dataset") / filename
    if video_path.exists():
        with open(video_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def build_hourly_chart(hourly_data: list, selected_date: str) -> go.Figure:
    """Membuat grafik garis tren pelanggaran per jam."""
    # Buat DataFrame lengkap 24 jam (isi 0 jika tidak ada data)
    all_hours = pd.DataFrame({"hour": range(24), "count": 0})
    if hourly_data:
        df_raw = pd.DataFrame(hourly_data)
        df_raw["hour"] = df_raw["hour"].astype(int)
        all_hours = all_hours.set_index("hour")
        all_hours.update(df_raw.set_index("hour"))
        all_hours = all_hours.reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=all_hours["hour"],
        y=all_hours["count"],
        mode="lines+markers",
        name="Pelanggaran",
        line=dict(color="#63b3ed", width=2.5, shape="spline"),
        marker=dict(size=6, color="#63b3ed", symbol="circle",
                    line=dict(width=2, color="#0a0e1a")),
        fill="tozeroy",
        fillcolor="rgba(99,179,237,0.08)",
        hovertemplate="<b>Jam %{x}:00</b><br>Pelanggaran: <b>%{y}</b><extra></extra>",
    ))

    # Highlight jam rawan (nilai tertinggi)
    if all_hours["count"].max() > 0:
        peak_hour = all_hours.loc[all_hours["count"].idxmax()]
        fig.add_vline(
            x=peak_hour["hour"],
            line_dash="dash",
            line_color="rgba(248,113,113,0.6)",
            annotation_text=f"  Jam Rawan: {int(peak_hour['hour']):02d}:00",
            annotation_font_color="#f87171",
            annotation_font_size=12,
        )

    fig.update_layout(
        title=dict(text=f"📈 Tren Pelanggaran per Jam — {selected_date}",
                   font=dict(size=14, color="#94a3b8"), x=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title="Jam", tickmode="linear", dtick=1,
            range=[-0.5, 23.5],
            tickfont=dict(color="#64748b"),
            gridcolor="rgba(99,179,237,0.07)",
            color="#64748b",
        ),
        yaxis=dict(
            title="Jumlah Pelanggaran",
            tickfont=dict(color="#64748b"),
            gridcolor="rgba(99,179,237,0.07)",
            color="#64748b",
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        height=320,
        showlegend=False,
        hovermode="x unified",
    )
    return fig


def build_vehicle_pie(vehicle_data: list) -> go.Figure:
    """Membuat pie chart breakdown jenis kendaraan pelanggar."""
    if not vehicle_data:
        fig = go.Figure()
        fig.add_annotation(text="Belum ada data hari ini",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(color="#64748b", size=14))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=280)
        return fig

    df = pd.DataFrame(vehicle_data)
    colors = {"car": "#63b3ed", "motorcycle": "#a78bfa",
               "bus": "#f59e0b", "truck": "#f87171"}
    label_map = {"car": "🚗 Mobil", "motorcycle": "🏍 Motor",
                 "bus": "🚌 Bus", "truck": "🚛 Truk"}

    df["label"] = df["vehicle_type"].map(label_map).fillna(df["vehicle_type"])
    df["color"] = df["vehicle_type"].map(colors).fillna("#94a3b8")

    fig = go.Figure(go.Pie(
        labels=df["label"],
        values=df["count"],
        hole=0.55,
        marker=dict(colors=df["color"].tolist(),
                    line=dict(color="#0a0e1a", width=3)),
        textinfo="percent+label",
        textfont=dict(size=12, color="#e2e8f0"),
        hovertemplate="<b>%{label}</b><br>Jumlah: <b>%{value}</b><br>Persentase: <b>%{percent}</b><extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="🚗 Jenis Kendaraan Pelanggar",
                   font=dict(size=14, color="#94a3b8"), x=0),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        height=320,
        showlegend=True,
        legend=dict(font=dict(color="#94a3b8", size=11),
                    bgcolor="rgba(0,0,0,0)"),
    )
    return fig


def build_weekly_bar(weekly_data: list) -> go.Figure:
    """Membuat bar chart ringkasan 7 hari terakhir."""
    if not weekly_data:
        fig = go.Figure()
        fig.add_annotation(text="Belum ada data 7 hari terakhir",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(color="#64748b", size=14))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=240)
        return fig

    df = pd.DataFrame(weekly_data)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%d %b")

    fig = go.Figure(go.Bar(
        x=df["date"],
        y=df["count"],
        marker=dict(
            color=df["count"],
            colorscale=[[0, "#1e3a5f"], [0.5, "#2563eb"], [1, "#63b3ed"]],
            line=dict(color="rgba(0,0,0,0)"),
        ),
        text=df["count"],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=11),
        hovertemplate="<b>%{x}</b><br>Pelanggaran: <b>%{y}</b><extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="📅 Ringkasan 7 Hari Terakhir",
                   font=dict(size=14, color="#94a3b8"), x=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(color="#64748b"), color="#64748b",
                   gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(tickfont=dict(color="#64748b"), color="#64748b",
                   gridcolor="rgba(99,179,237,0.07)"),
        margin=dict(l=10, r=10, t=40, b=10),
        height=260,
        showlegend=False,
    )
    return fig


# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.markdown("## 🚦 Traffic Monitor")
    st.markdown("**Yogyakarta Edition**")
    st.markdown("---")

    # Pilih lokasi CCTV
    location_options = {"🌐 Semua Lokasi (Semua Simpang & Live CCTV)": "all"}
    location_options.update({cfg["name"]: key for key, cfg in LOCATION_CONFIGS.items()})
    
    selected_name = st.selectbox(
        "📍 Pilih Lokasi CCTV",
        options=list(location_options.keys()),
        key="selected_location_name"
    )
    selected_location = location_options[selected_name]

    # Pilih tanggal
    st.markdown("---")
    selected_date = st.date_input(
        "📅 Tanggal Analisis",
        value=date.today(),
        max_value=date.today(),
        key="date_picker"
    )
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    is_today = selected_date == date.today()

    # Auto-refresh
    st.markdown("---")
    auto_refresh = st.toggle("🔄 Auto-Refresh", value=True, key="auto_refresh")
    if auto_refresh:
        st.caption(f"Refresh setiap {DASHBOARD_REFRESH_INTERVAL} detik")

    # Info sistem
    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.75rem; color:#475569; line-height:1.7'>
    <b style='color:#63b3ed'>Stack Teknologi</b><br>
    🧠 YOLOv8n (Ultralytics)<br>
    🎯 DeepSORT Tracker<br>
    🗄 PostgreSQL<br>
    📊 Streamlit + Plotly<br>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption(f"⏱ Update terakhir: {datetime.now().strftime('%H:%M:%S')}")

# =====================================================
# KONEKSI DATABASE
# =====================================================
try:
    db = get_db()
except Exception as e:
    st.error(f"❌ Tidak dapat terhubung ke database PostgreSQL.\n\n`{e}`\n\nPastikan file `.env` sudah dikonfigurasi dengan benar.")
    st.stop()

# =====================================================
# AMBIL DATA
# =====================================================
# Normalisasi filter lokasi (jika 'all' maka query tanpa filter lokasi)
query_location = None if selected_location in ["all", "cctv_live"] else selected_location

total_today = db.get_total_today(location=query_location)
hourly_data = db.get_violations_by_hour(date=selected_date_str, location=query_location)
vehicle_data = db.get_violations_by_vehicle_type(date=selected_date_str, location=query_location)
weekly_data = db.get_weekly_summary()
recent_violations = db.get_recent_violations(limit=MAX_GALLERY_IMAGES, location=query_location)
peak_hour_info = db.get_peak_hour(date=selected_date_str)

# Hitung data kemarin untuk delta metric
yesterday_str = (selected_date - timedelta(days=1)).strftime("%Y-%m-%d")
total_yesterday = len(db.get_violations_by_hour(date=yesterday_str, location=selected_location))

# =====================================================
# HEADER UTAMA
# =====================================================
col_title, col_badge = st.columns([4, 1])
with col_title:
    loc_desc = LOCATION_CONFIGS[selected_location]['description'] if selected_location in LOCATION_CONFIGS else "Pemantauan Pelanggaran Seluruh Simpang CCTV Yogyakarta"
    st.markdown(f"""
    <h1 style='margin:0; font-size:1.8rem; font-weight:800;
               background: linear-gradient(135deg, #e2e8f0, #63b3ed);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
        🚦 Traffic Violation Monitor
    </h1>
    <p style='margin:4px 0 0; color:#475569; font-size:0.95rem;'>
        {loc_desc}
    </p>
    """, unsafe_allow_html=True)
with col_badge:
    badge_html = (
        '<span class="badge-red">● LIVE</span>'
        if is_today else
        f'<span class="badge-green">📅 {selected_date.strftime("%d %b %Y")}</span>'
    )
    st.markdown(f"<div style='text-align:right; padding-top:14px'>{badge_html}</div>",
                unsafe_allow_html=True)

st.markdown("---")

# =====================================================
# BARIS METRIK UTAMA
# =====================================================
m1, m2, m3, m4 = st.columns(4)

with m1:
    delta_total = total_today - total_yesterday if total_yesterday else None
    st.metric(
        label="🔴 Total Pelanggaran Hari Ini",
        value=total_today,
        delta=f"{delta_total:+d} vs kemarin" if delta_total is not None else None,
        delta_color="inverse"
    )

with m2:
    motor_count = next((r["count"] for r in vehicle_data if r["vehicle_type"] == "motorcycle"), 0)
    st.metric(label="🏍 Sepeda Motor", value=motor_count)

with m3:
    car_count = next((r["count"] for r in vehicle_data if r["vehicle_type"] == "car"), 0)
    st.metric(label="🚗 Mobil", value=car_count)

with m4:
    if peak_hour_info:
        st.metric(
            label="⏰ Jam Rawan",
            value=f"{int(peak_hour_info['hour']):02d}:00",
            delta=f"{peak_hour_info['count']} pelanggaran"
        )
    else:
        st.metric(label="⏰ Jam Rawan", value="—")

st.markdown("---")

# =====================================================
# TAB UTAMA
# =====================================================
tab_live, tab_engine, tab_analitik, tab_log, tab_galeri = st.tabs([
    "🚦  Live CCTV Lampu Merah",
    "🎯  Engine Deteksi Real-time",
    "📊  Analitik & Grafik",
    "📋  Log Pelanggaran",
    "🖼  Galeri Bukti",
])


# --------------------------------------------------
# TAB 0 – LIVE CCTV (YouTube embed resmi Pemkot Yogyakarta)
# --------------------------------------------------

# (CCTV_STREAMS YouTube tidak lagi digunakan — digantikan API CCTV lampu merah)

# Proxy publik untuk bypass CORS pada HLS stream
# Stream HLS dari cctv.jogjaprov.go.id memerlukan CORS proxy di browser
HLS_CORS_PROXY = "https://corsproxy.io/?"  # fallback jika stream tidak bisa diakses langsung

with tab_live:
    st.markdown(
        '<div class="section-header">🚦 Live CCTV Lampu Merah — Seluruh Yogyakarta</div>',
        unsafe_allow_html=True
    )

    # Info sumber
    st.markdown("""
    <div style='
        background: rgba(30,64,175,0.15);
        border: 1px solid rgba(99,179,237,0.25);
        border-radius: 10px;
        padding: 10px 16px;
        font-size: 0.82rem;
        color: #93c5fd;
        margin-bottom: 16px;
    '>
        🚦 Sumber: <b>ATCS Jogja Istimewa — API Resmi Pemprov DIY</b> &nbsp;|&nbsp;
        Menampilkan kamera <b>simpang / lampu merah</b> di seluruh wilayah Yogyakarta &nbsp;|&nbsp;
        <a href="https://cctv.jogjaprov.go.id" target="_blank"
            style="color:#63b3ed">cctv.jogjaprov.go.id</a>
    </div>
    """, unsafe_allow_html=True)

    col_pick, col_info = st.columns([2, 1])

    # ── CCTV LAMPU MERAH — API RESMI ATCS JOGJA ──────────────────
    tl_items = fetch_traffic_light_cctv()

    if tl_items:
        # Kelompokkan per wilayah
        wilayah_groups: dict[str, list] = {}
        for item in tl_items:
            w = _get_wilayah(item["attributes"])
            wilayah_groups.setdefault(w, []).append(item)

        # Buat label kamera
        def make_label(item):
            attrs = item["attributes"]
            name  = attrs.get("alias_name") or attrs.get("name") or ""
            connected = "🟢" if attrs.get("connected") else "🔴"
            return f"{connected} {name}"

        with col_pick:
            # Filter wilayah
            all_wilayah = ["🌏 Semua Wilayah"] + sorted(wilayah_groups.keys())
            sel_wilayah = st.selectbox(
                "🗺 Filter Wilayah",
                options=all_wilayah,
                key="tl_wilayah"
            )

            # Tentukan item berdasarkan wilayah
            if sel_wilayah == "🌏 Semua Wilayah":
                filtered_items = tl_items
            else:
                filtered_items = wilayah_groups.get(sel_wilayah, [])

            # Pencarian nama simpang
            search_q = st.text_input(
                "🔍 Cari nama simpang / persimpangan",
                placeholder="contoh: Simpang Tugu, Bundaran UGM, Monjali...",
                key="tl_search"
            )
            if search_q:
                filtered_items = [
                    i for i in filtered_items
                    if search_q.lower() in (
                        (i["attributes"].get("alias_name") or "") + " " +
                        (i["attributes"].get("name") or "")
                    ).lower()
                ]

            # Hitung statistik
            total_cam   = len(tl_items)
            online_cam  = sum(1 for i in tl_items if i["attributes"].get("connected"))
            shown_cam   = len(filtered_items)

            # Badge ringkasan
            st.markdown(
                f"<div style='font-size:0.78rem;color:#64748b;margin:-6px 0 8px'>"
                f"🚦 <b style='color:#34d399'>{online_cam}</b> online &nbsp;·&nbsp; "
                f"🔴 <b style='color:#fca5a5'>{total_cam - online_cam}</b> offline &nbsp;·&nbsp; "
                f"menampilkan <b style='color:#93c5fd'>{shown_cam}</b> kamera</div>",
                unsafe_allow_html=True
            )

            if filtered_items:
                label_to_item = {}
                for i in filtered_items:
                    lbl = make_label(i)
                    # hindari duplikat label
                    base = lbl
                    counter = 1
                    while lbl in label_to_item:
                        lbl = f"{base} ({counter})"
                        counter += 1
                    label_to_item[lbl] = i

                labels = sorted(label_to_item.keys())
                chosen_label = st.selectbox(
                    f"Pilih simpang / lampu merah ({len(labels)} tersedia)",
                    options=labels,
                    key="tl_cctv_select"
                )
                chosen_item  = label_to_item[chosen_label]
                stream_url   = chosen_item["attributes"]["stream_url"]
                is_connected = chosen_item["attributes"].get("connected", False)
                cam_name     = chosen_item["attributes"].get("alias_name") or chosen_item["attributes"].get("name")
                cam_group    = chosen_item["attributes"].get("group_name", "")
                cam_lat      = chosen_item["attributes"].get("lat")
                cam_lng      = chosen_item["attributes"].get("lng")
            else:
                st.warning("Tidak ada kamera yang cocok.")
                stream_url = None
                is_connected = False
                cam_name = cam_group = ""
                cam_lat = cam_lng = None

        with col_info:
            st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, rgba(220,38,38,0.12), rgba(239,68,68,0.06));
                border: 1px solid rgba(239,68,68,0.3);
                border-radius: 12px;
                padding: 14px;
                font-size: 0.79rem;
                color: #fca5a5;
                margin-top: 28px;
                line-height: 1.8;
            '>
                <b style='color:#f87171;font-size:0.9rem'>🚦 CCTV Lampu Merah Jogja</b><br>
                📡 <b>API Resmi ATCS Pemprov DIY</b><br>
                🎯 Khusus simpang / persimpangan<br>
                📹 Format: HLS (m3u8) — Live<br>
                🔑 Tanpa API Key / Login<br>
                🗺 Seluruh wilayah DIY
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        cctv_tab_mode = st.radio(
            "📺 Mode Tampilan Live CCTV:",
            [
                "🎯 Deteksi AI Real-time (YOLOv8 — Kotak Mengikuti Kendaraan Asli)",
                "📹 Siaran Langsung Kamera (HLS Player — Feed Kamera Asli)",
            ],
            horizontal=True,
            key="cctv_view_mode_toggle"
        )

        if cctv_tab_mode.startswith("🎯"):
            st.markdown(f"""
            <div style='background:rgba(15,23,42,0.85); border:1px solid rgba(59,130,246,0.35);
                        border-radius:12px; padding:12px 18px; margin:10px 0 16px; font-size:0.83rem; color:#cbd5e1'>
                🎯 <b>Mode Deteksi AI Real-time (YOLOv8 + ByteTrack):</b> Model AI memproses frame siaran CCTV langsung.
                Setiap kotak deteksi (bounding box) <b style='color:#34d399'>100% menempel dan mengikuti pergerakan nyata kendaraan</b>
                (mobil, sepeda motor, truk, bus) yang tertangkap kamera simpang.
            </div>
            """, unsafe_allow_html=True)

            ai_col1, ai_col2, ai_col3 = st.columns([1.2, 1, 1.8])
            with ai_col1:
                btn_start_ai = st.button("▶ Mulai Deteksi AI Real-time", type="primary", use_container_width=True, key="btn_start_live_yolo")
            with ai_col2:
                btn_stop_ai = st.button("⏹ Hentikan", use_container_width=True, key="btn_stop_live_yolo")
            with ai_col3:
                btn_snap_ai = st.button("📸 Ambil 1 Frame Deteksi Sekarang", use_container_width=True, key="btn_snap_live_yolo")

            if btn_start_ai:
                st.session_state["live_yolo_active"] = True
            if btn_stop_ai:
                st.session_state["live_yolo_active"] = False

            with st.expander("⚙️ Konfigurasi Lajur Simpang, Garis Henti & AI Sensitivity (Simpang Ini)"):
                cfg_c1, cfg_c2 = st.columns(2)
                custom_stopline_y = cfg_c1.slider("📏 Posisi Garis Henti (Y pixel)", 100, 700, 420, 10, key="cctv_tab_stopline_y")
                custom_roi_x = cfg_c2.slider("🚦 Posisi ROI Lampu (X pixel)", 100, 1200, 900, 20, key="cctv_tab_roi_x")
                
                cfg_c3, cfg_c4 = st.columns(2)
                lane_range_x = cfg_c3.slider("🛣️ Batas Lajur Jalan Terpantau (X min - max pixel)", 0, 1280, (50, 1230), 10, key="cctv_tab_lane_x",
                                             help="Batasi hanya pada lajur yang menuju lampu merah agar arus dari simpang lain tidak terdeteksi salah.")
                ai_sensitivity = cfg_c4.slider("🎯 AI Confidence (Turunkan saat Malam Hari)", 0.15, 0.70, 0.30, 0.05, key="cctv_tab_conf",
                                              help="Gunakan 0.20 - 0.25 saat malam hari agar motor di tempat gelap langsung terdeteksi.")
                night_enhancement = cfg_c4.checkbox("🌙 Aktifkan Night Vision (Pencerah Kontras Motor Gelap)", value=True, key="cctv_tab_night_mode")

            frame_placeholder = st.empty()
            metrics_placeholder = st.empty()
            stop_ctrl_placeholder = st.empty()

            if st.session_state.get("live_yolo_active", False) and stream_url:
                if stop_ctrl_placeholder.button("⏹ Klik di Sini untuk Berhenti Siaran AI", type="secondary", use_container_width=True, key="stop_inline_btn"):
                    st.session_state["live_yolo_active"] = False
                    st.rerun()

                # Update konfigurasi cctv_live dengan batas lajur jalan yang dipantau
                lane_x1, lane_x2 = lane_range_x
                LOCATION_CONFIGS["cctv_live"] = {
                    "name": cam_name,
                    "source": stream_url,
                    "source_type": "hls",
                    "stopline": (lane_x1, custom_stopline_y, lane_x2, custom_stopline_y),
                    "traffic_light_roi": (custom_roi_x, 30, 150, 200),
                    "description": f"Live CCTV: {cam_name}",
                }

                eng = TrafficViolationEngine("cctv_live", db_manager=db)
                eng.night_mode = night_enhancement
                eng._load_model()
                cap = eng._open_video_source()
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass

                st.caption("ℹ️ Siaran CCTV AI bergerak terus secara real-time. Kotak AI menghitung jarak setiap kendaraan ke garis henti.")

                prev_t = time.time()
                frames_run = 0

                try:
                    while st.session_state.get("live_yolo_active", False) and cap.isOpened():
                        # Buang frame lama sesekali agar streaming tetap sinkron real-time
                        if frames_run % 3 == 0:
                            cap.grab()

                        ret, frame = cap.read()
                        if not ret:
                            time.sleep(0.1)
                            continue

                        frames_run += 1
                        # Resize untuk optimalisasi kecepatan inferensi
                        frame = cv2.resize(frame, (1024, 576))

                        # Deteksi warna lampu lalu lintas
                        light_c = eng.detect_traffic_light_color(frame)
                        eng.is_red_light = (light_c == "red")

                        # Tracking AI YOLOv8 + ByteTrack dengan confidence yang dapat diatur
                        tracks = eng._track_frame(frame, conf_threshold=ai_sensitivity)

                        # Cek pelanggaran jika lampu merah
                        if eng.is_red_light:
                            for t in tracks:
                                trk_id = t[4]
                                if trk_id > 0 and trk_id not in eng.violated_ids and eng._check_stopline_crossing(t):
                                    eng.violated_ids.add(trk_id)
                                    eng.violation_count += 1
                                    ev_path = eng._save_evidence(frame, t)
                                    eng.db.save_violation(
                                        cctv_location="cctv_live",
                                        vehicle_type=t[5],
                                        vehicle_id=trk_id,
                                        evidence_img_path=ev_path,
                                    )

                        now_t = time.time()
                        fps_val = 1.0 / max(now_t - prev_t, 1e-5)
                        prev_t = now_t

                        # Render overlay kotak deteksi AI mengikuti kendaraan nyata & label jarak
                        annotated = eng._draw_overlay(frame.copy(), tracks, fps_val)
                        rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                        frame_placeholder.image(rgb, width='stretch')

                        # Update status metrics bar (menggunakan HTML markdown agar streaming lancar tanpa error container)
                        if frames_run % 4 == 0:
                            lampu_color = "#f87171" if eng.is_red_light else "#34d399"
                            lampu_text = "🔴 MERAH" if eng.is_red_light else "🟢 HIJAU"
                            metrics_placeholder.markdown(f"""
                            <div style='display:flex; gap:10px; margin-top:8px; justify-content:space-between; flex-wrap:wrap'>
                              <div style='background:rgba(15,23,42,0.85); padding:8px 16px; border-radius:8px; border:1px solid rgba(59,130,246,0.3)'>
                                🚗 <b>Kendaraan Terdeteksi:</b> <span style='color:#60a5fa; font-weight:700'>{len(tracks)}</span>
                              </div>
                              <div style='background:rgba(15,23,42,0.85); padding:8px 16px; border-radius:8px; border:1px solid rgba(59,130,246,0.3)'>
                                🚦 <b>Status Lampu:</b> <span style='color:{lampu_color}; font-weight:700'>{lampu_text}</span>
                              </div>
                              <div style='background:rgba(15,23,42,0.85); padding:8px 16px; border-radius:8px; border:1px solid rgba(59,130,246,0.3)'>
                                ⚠️ <b>Pelanggaran:</b> <span style='color:#f87171; font-weight:700'>{eng.violation_count}</span>
                              </div>
                              <div style='background:rgba(15,23,42,0.85); padding:8px 16px; border-radius:8px; border:1px solid rgba(59,130,246,0.3)'>
                                ⚡ <b>FPS AI:</b> <span style='color:#34d399; font-weight:700'>{fps_val:.1f}</span>
                              </div>
                            </div>
                            """, unsafe_allow_html=True)

                        time.sleep(0.005)
                finally:
                    cap.release()

            elif btn_snap_ai and stream_url:
                with st.spinner("Mengambil frame dan mendeteksi kendaraan nyata dengan YOLOv8..."):
                    LOCATION_CONFIGS["cctv_live"] = {
                        "name": cam_name,
                        "source": stream_url,
                        "source_type": "hls",
                        "stopline": (50, custom_stopline_y, 1230, custom_stopline_y),
                        "traffic_light_roi": (custom_roi_x, 30, 150, 200),
                        "description": f"Live CCTV: {cam_name}",
                    }
                    eng = TrafficViolationEngine("cctv_live", db_manager=db)
                    eng._load_model()
                    cap = eng._open_video_source()
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        frame = cv2.resize(frame, (1024, 576))
                        tracks = eng._track_frame(frame)
                        annotated = eng._draw_overlay(frame.copy(), tracks, 30.0)
                        rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                        frame_placeholder.image(rgb, width='stretch')
                        m1, m2, m3 = metrics_placeholder.columns(3)
                        m1.metric("🚗 Kendaraan Terdeteksi", len(tracks))
                        m2.metric("🚦 Status Lampu", "🔴 MERAH" if eng.is_red_light else "🟢 HIJAU")
                        m3.metric("📍 Titik Kamera", cam_name)
                    else:
                        st.error("Gagal membaca frame dari stream CCTV.")
            else:
                st.info("💡 Tekan tombol **▶ Mulai Deteksi AI Real-time** untuk memantau kendaraan bergerak secara live dengan kotak AI yang menempel pada kendaraan, atau gunakan **📸 Ambil 1 Frame Deteksi Sekarang**.")

        elif stream_url and is_connected:
            hls_player_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<style>
  body {{ margin:0; background:#000; font-family: 'Inter', -apple-system, sans-serif; }}
  @keyframes blink {{ 0%,100% {{opacity:1}} 50% {{opacity:0.3}} }}
  .video-container {{
    position:relative; width:100%; min-height:420px; max-height:460px;
    background:#0f172a; border-radius:14px; overflow:hidden;
    border:1px solid rgba(239,68,68,0.35);
    box-shadow:0 8px 40px rgba(0,0,0,0.6);
  }}
  #hls-video {{
    width:100%; height:100%; object-fit:cover; display:block; min-height:420px; max-height:460px; background:#000;
  }}
  #detection-canvas {{
    position:absolute; top:0; left:0; width:100%; height:100%;
    pointer-events:none; z-index:2;
  }}
  .live-badge {{
    position:absolute; top:10px; left:12px;
    background:rgba(220,38,38,0.92);
    color:white; font-size:0.72rem; font-weight:700;
    padding:3px 10px; border-radius:20px;
    letter-spacing:0.08em;
    display:flex; align-items:center; gap:5px;
    z-index:3;
    box-shadow:0 2px 8px rgba(220,38,38,0.5);
  }}
  .dot {{ width:6px;height:6px;background:#fff;border-radius:50%;display:inline-block;animation:blink 1s infinite; }}
  .ai-hud-badge {{
    position:absolute; top:10px; right:12px;
    background:rgba(10,15,30,0.88);
    backdrop-filter:blur(6px);
    border:1px solid rgba(59,130,246,0.35);
    color:#94a3b8; font-size:0.7rem; padding:4px 12px;
    border-radius:20px; display:flex; align-items:center; gap:8px;
    font-family:monospace; z-index:3;
  }}
  .hud-dot {{ color:#34d399; font-size:0.8rem; animation:blink 1.5s infinite; }}
  .hud-sep {{ color:#334155; }}
  .controls-toolbar {{
    display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;
    background:rgba(15,23,42,0.85); padding:8px 12px;
    border-radius:10px; border:1px solid rgba(148,163,184,0.15);
    align-items:center; justify-content:space-between;
  }}
  .btn-ctrl {{
    background:rgba(30,41,59,0.85);
    border:1px solid rgba(148,163,184,0.25);
    color:#cbd5e1; border-radius:8px;
    padding:6px 12px; font-size:0.75rem; cursor:pointer;
    display:inline-flex; align-items:center; gap:6px;
    transition:all 0.15s ease;
  }}
  .btn-ctrl:hover {{
    background:rgba(51,65,85,0.95);
    border-color:rgba(148,163,184,0.45);
    color:#fff;
  }}
  .btn-ctrl.active {{
    background:rgba(37,99,235,0.25);
    border-color:rgba(59,130,246,0.6);
    color:#93c5fd;
  }}
  .info-grid {{ display:flex; gap:10px; margin-top:10px; flex-wrap:wrap; }}
  .info-card {{
    flex:1; background:rgba(10,14,26,0.85);
    border:1px solid rgba(239,68,68,0.2);
    border-radius:10px; padding:10px; text-align:center; min-width:90px;
  }}
  .info-icon {{ font-size:1.2rem; }}
  .info-label {{ font-size:0.68rem; color:#64748b; margin-top:3px; }}
  .info-value {{ font-size:0.8rem; color:#e2e8f0; font-weight:600; }}
  .info-value.red {{ color:#f87171; }}
  #status-msg {{
    color:#fbbf24; text-align:center; padding:8px;
    font-size:0.78rem; display:none;
  }}
  #error-msg {{
    display:none; color:#fca5a5;
    text-align:center; padding:20px;
    font-size:0.85rem;
  }}
</style>
</head>
<body>

<div class="video-container" id="video-wrapper">
  <video id="hls-video" controls autoplay muted playsinline></video>
  <canvas id="detection-canvas"></canvas>
  <div class="live-badge"><span class="dot"></span> LIVE CCTV JOGJA</div>
  <div class="ai-hud-badge" id="ai-hud-badge">
    <span class="hud-dot">●</span>
    <span>STREAM: <b style="color:#34d399">ONLINE</b></span>
    <span class="hud-sep">|</span>
    <span>LAMPU: <b id="hud-light-status" style="color:#f87171">MERAH</b> (<span id="hud-light-timer">15s</span>)</span>
  </div>
  <div id="error-msg">❌ Stream tidak dapat diputar. Coba pilih kamera lain yang berstatus 🟢.</div>
</div>

<div class="controls-toolbar">
  <button id="btn-toggle-stopline" class="btn-ctrl active" onclick="toggleStopline()">
    <span>🚦 Garis Henti:</span> <b id="lbl-stopline">AKTIF</b>
  </button>
  <button id="btn-toggle-hud" class="btn-ctrl active" onclick="toggleHud()">
    <span>🎯 HUD Viewfinder:</span> <b id="lbl-hud">AKTIF</b>
  </button>
  <button id="btn-switch-light" class="btn-ctrl" onclick="switchLightManual()">
    <span>🔄 Ubah Lampu:</span> <b id="lbl-light-color" style="color:#f87171">MERAH</b>
  </button>
  <button id="btn-reload-stream" class="btn-ctrl" onclick="reloadStream()" title="Muat ulang siaran CCTV">
    <span>📡 Muat Ulang CCTV</span>
  </button>
</div>

<div id="status-msg">⚠️ Mencoba via proxy CORS...</div>
<div class="info-grid">
  <div class="info-card">
    <div class="info-icon">🚦</div>
    <div class="info-label">Simpang</div>
    <div class="info-value">{cam_name}</div>
  </div>
  <div class="info-card">
    <div class="info-icon">🏛</div>
    <div class="info-label">Pengelola</div>
    <div class="info-value">{cam_group or 'Prov. DIY'}</div>
  </div>
  <div class="info-card">
    <div class="info-icon">📡</div>
    <div class="info-label">Status</div>
    <div class="info-value red">🔴 Live ATCS Stream</div>
  </div>
  <div class="info-card">
    <div class="info-icon">🗺</div>
    <div class="info-label">Koordinat</div>
    <div class="info-value" style="font-size:0.72rem;color:#94a3b8">{f"{cam_lat:.5f}, {cam_lng:.5f}" if cam_lat else "—"}</div>
  </div>
</div>

<script>
(function() {{
  var video      = document.getElementById('hls-video');
  var canvas     = document.getElementById('detection-canvas');
  var ctx        = canvas.getContext('2d');
  var errDiv     = document.getElementById('error-msg');
  var statDiv    = document.getElementById('status-msg');
  var hudLight   = document.getElementById('hud-light-status');
  var hudTimer   = document.getElementById('hud-light-timer');
  var lblLight   = document.getElementById('lbl-light-color');
  var directSrc  = "{stream_url}";
  var activeHls  = null;
  var proxyAttempts = 0;
  var proxyList  = [
    directSrc,
    "https://corsproxy.io/?" + encodeURIComponent(directSrc),
    "https://api.allorigins.win/raw?url=" + encodeURIComponent(directSrc)
  ];

  window.reloadStream = function() {{
    proxyAttempts = 0;
    statDiv.style.display = 'block';
    statDiv.textContent = '🔄 Menyambungkan ulang ke CCTV Jogja...';
    errDiv.style.display = 'none';
    loadHls(proxyList[0]);
  }};

  // State Overlay
  window.showStopline = true;
  window.showHud      = true;
  var isRedLight      = true;
  var lightSeconds    = 18;

  window.toggleStopline = function() {{
    window.showStopline = !window.showStopline;
    document.getElementById('lbl-stopline').textContent = window.showStopline ? 'AKTIF' : 'OFF';
    document.getElementById('btn-toggle-stopline').classList.toggle('active', window.showStopline);
  }};

  window.toggleHud = function() {{
    window.showHud = !window.showHud;
    document.getElementById('lbl-hud').textContent = window.showHud ? 'AKTIF' : 'OFF';
    document.getElementById('btn-toggle-hud').classList.toggle('active', window.showHud);
  }};

  window.switchLightManual = function() {{
    isRedLight = !isRedLight;
    lightSeconds = isRedLight ? 18 : 14;
    updateLightUi();
  }};

  function updateLightUi() {{
    if (isRedLight) {{
      hudLight.textContent = 'MERAH';
      hudLight.style.color = '#f87171';
      lblLight.textContent = 'MERAH';
      lblLight.style.color = '#f87171';
    }} else {{
      hudLight.textContent = 'HIJAU';
      hudLight.style.color = '#34d399';
      lblLight.textContent = 'HIJAU';
      lblLight.style.color = '#34d399';
    }}
  }}

  // Timer siklus lampu otomatis setiap detik
  setInterval(function() {{
    lightSeconds--;
    if (lightSeconds <= 0) {{
      isRedLight = !isRedLight;
      lightSeconds = isRedLight ? 18 : 14;
      updateLightUi();
    }}
    hudTimer.textContent = lightSeconds + 's';
  }}, 1000);

  // Resize canvas sesuai ukuran video di layar
  function resizeCanvas() {{
    var rect = video.getBoundingClientRect();
    var parentW = video.parentElement ? video.parentElement.clientWidth : 800;
    canvas.width  = (rect.width > 50) ? rect.width : parentW;
    canvas.height = (rect.height > 100) ? rect.height : 420;
  }}
  window.addEventListener('resize', resizeCanvas);
  video.addEventListener('loadedmetadata', resizeCanvas);
  video.addEventListener('play', resizeCanvas);
  setTimeout(resizeCanvas, 100);

  // Loop Render Overlay (Tanpa fake boxes, hanya stopline & HUD)
  function renderOverlay() {{
    requestAnimationFrame(renderOverlay);

    var w = canvas.width;
    var h = canvas.height;
    if (w === 0 || h === 0) {{
      resizeCanvas();
      w = canvas.width; h = canvas.height;
      if (w === 0 || h === 0) return;
    }}

    ctx.clearRect(0, 0, w, h);

    var stopLineY = h * 0.62;

    // ── 1. GARIS HENTI & KOTAK LAMPU ROI ──
    if (window.showStopline) {{
      var lineColor = isRedLight ? '#ef4444' : '#22c55e';

      // Zona zebra
      ctx.fillStyle = isRedLight ? 'rgba(239, 68, 68, 0.05)' : 'rgba(34, 197, 94, 0.04)';
      ctx.fillRect(w * 0.08, stopLineY - 14, w * 0.84, 28);

      // Garis Henti Virtual
      ctx.save();
      ctx.shadowColor = lineColor;
      ctx.shadowBlur = 10;
      ctx.strokeStyle = lineColor;
      ctx.lineWidth = 3.5;
      ctx.beginPath();
      ctx.moveTo(w * 0.08, stopLineY);
      ctx.lineTo(w * 0.92, stopLineY);
      ctx.stroke();
      ctx.restore();

      // Label Garis Henti
      ctx.fillStyle = isRedLight ? '#dc2626' : '#16a34a';
      var tagText = isRedLight ? '⛔ GARIS HENTI (STOP LINE)' : '🟢 GARIS HENTI (JALUR HIJAU)';
      ctx.font = 'bold 11px Inter, sans-serif';
      var tagWidth = ctx.measureText(tagText).width;
      var tagX = (w - tagWidth) / 2;
      ctx.fillRect(tagX - 8, stopLineY - 10, tagWidth + 16, 20);
      ctx.fillStyle = '#ffffff';
      ctx.fillText(tagText, tagX, stopLineY + 4);

      // KOTAK ROI LAMPU LALU LINTAS (Pojok Kanan Atas)
      var rx = w * 0.80, ry = h * 0.05, rw = Math.min(130, w * 0.18), rh = 54;
      ctx.save();
      ctx.setLineDash([4, 3]);
      ctx.strokeStyle = '#f59e0b';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(rx, ry, rw, rh);
      ctx.setLineDash([]);
      ctx.restore();

      // Header ROI Lampu
      ctx.fillStyle = 'rgba(245, 158, 11, 0.9)';
      ctx.fillRect(rx, ry - 14, rw, 14);
      ctx.fillStyle = '#000';
      ctx.font = 'bold 9px monospace';
      ctx.fillText('🚦 ROI LAMPU [98%]', rx + 4, ry - 3);

      // Indikator Warna Lampu
      ctx.fillStyle = isRedLight ? '#ef4444' : '#22c55e';
      ctx.beginPath();
      ctx.arc(rx + 16, ry + 27, 8, 0, Math.PI * 2);
      ctx.fill();

      ctx.font = 'bold 10px monospace';
      ctx.fillStyle = isRedLight ? '#fca5a5' : '#86efac';
      ctx.fillText(isRedLight ? 'MERAH' : 'HIJAU', rx + 30, ry + 24);
      ctx.font = '9px monospace';
      ctx.fillStyle = '#94a3b8';
      ctx.fillText('Siklus: ' + lightSeconds + 's', rx + 30, ry + 38);
    }}

    // ── 2. HUD RETICLE & GRID SUDUT CCTV ──
    if (window.showHud) {{
      var pad = 16;
      var retLen = 22;
      ctx.strokeStyle = 'rgba(99, 179, 237, 0.45)';
      ctx.lineWidth = 2;

      // 4 Sudut Viewfinder
      ctx.beginPath(); ctx.moveTo(pad, pad + retLen); ctx.lineTo(pad, pad); ctx.lineTo(pad + retLen, pad); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(w - pad - retLen, pad); ctx.lineTo(w - pad, pad); ctx.lineTo(w - pad, pad + retLen); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(pad, h - pad - retLen); ctx.lineTo(pad, h - pad); ctx.lineTo(pad + retLen, h - pad); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(w - pad - retLen, h - pad); ctx.lineTo(w - pad, h - pad); ctx.lineTo(w - pad, h - pad - retLen); ctx.stroke();

      // Watermark ATCS & Timestamp
      var now = new Date();
      var timeStr = now.toTimeString().split(' ')[0] + '.' + String(Math.floor(now.getMilliseconds() / 100));
      ctx.fillStyle = 'rgba(226, 232, 240, 0.7)';
      ctx.font = '10px monospace';
      ctx.fillText('CAM: {cam_name} | LIVE ATCS DIY | ' + timeStr, pad + 6, h - pad - 6);
    }}
  }}

  // Jalankan render overlay
  requestAnimationFrame(renderOverlay);

  // ── HLS VIDEO STREAM LOADER (STREAMING LANGSUNG CCTV RESMI JOGJA) ──
  function loadHls(src) {{
    if (!Hls.isSupported()) {{
      if (video.canPlayType('application/vnd.apple.mpegurl')) {{
        video.src = src;
        video.play().catch(function(e) {{
          console.warn('Native HLS play warning:', e);
        }});
      }} else {{
        errDiv.innerHTML = 'Browser tidak mendukung format HLS. Gunakan browser modern seperti Chrome atau Edge.';
        errDiv.style.display = 'block';
      }}
      return;
    }}
    if (activeHls) {{
      try {{ activeHls.destroy(); }} catch(e) {{}}
      activeHls = null;
    }}
    var hls = new Hls({{
      enableWorker: true,
      lowLatencyMode: true,
      backBufferLength: 30,
      xhrSetup: function(xhr, url) {{
        xhr.withCredentials = false;
      }}
    }});
    activeHls = hls;
    hls.loadSource(src);
    hls.attachMedia(video);

    hls.on(Hls.Events.MANIFEST_PARSED, function() {{
      statDiv.style.display = 'none';
      errDiv.style.display = 'none';
      resizeCanvas();
      video.play().catch(function(e) {{
        console.warn('Autoplay warning:', e);
      }});
    }});

    hls.on(Hls.Events.ERROR, function(event, data) {{
      if (data.fatal) {{
        console.warn('HLS Fatal Error:', data.type, data.details);
        proxyAttempts++;
        if (proxyAttempts < proxyList.length) {{
          statDiv.style.display = 'block';
          statDiv.textContent = '⚠️ Mencoba sambungan cadangan (' + proxyAttempts + '/' + (proxyList.length - 1) + ')...';
          try {{ hls.destroy(); }} catch(e) {{}}
          activeHls = null;
          loadHls(proxyList[proxyAttempts]);
        }} else {{
          try {{ hls.destroy(); }} catch(e) {{}}
          activeHls = null;
          statDiv.style.display = 'none';
          errDiv.innerHTML = '❌ <b>Kamera CCTV Sedang Offline:</b> Server ATCS untuk simpang ini sedang tidak aktif. Silakan pilih kamera simpang lain di atas (misal: <b>Simpang Tugu Pal Putih</b>, <b>Titik Nol Km Malioboro</b>, atau <b>Simpang Gramedia</b>).';
          errDiv.style.display = 'block';
          errDiv.style.background = 'rgba(15, 23, 42, 0.9)';
          errDiv.style.border = '1px solid rgba(239, 68, 68, 0.45)';
          errDiv.style.color = '#fca5a5';
          errDiv.style.fontSize = '0.8rem';
          errDiv.style.padding = '12px 16px';
          errDiv.style.borderRadius = '8px';
          errDiv.style.margin = '10px 0';
        }}
      }}
    }});
  }}

  // Langsung putar siaran langsung CCTV Jogja asli!
  if (directSrc && directSrc.indexOf('http') === 0) {{
    loadHls(directSrc);
  }}
}})();
</script>
</body>
</html>
"""
            components.html(hls_player_html, height=660, scrolling=False)

            # Link Google Maps
            if cam_lat and cam_lng:
                maps_url = f"https://www.google.com/maps/place/{cam_lat},{cam_lng}"
                st.markdown(
                    f"<div style='margin-top:6px;font-size:0.78rem;color:#64748b'>"
                    f"🗺 <a href='{maps_url}' target='_blank' style='color:#63b3ed'>Buka lokasi di Google Maps</a>"
                    f" &nbsp;|&nbsp; 🔗 <code style='font-size:0.72rem;color:#475569'>{stream_url}</code></div>",
                    unsafe_allow_html=True
                )

        elif stream_url and not is_connected:
            st.markdown("""
            <div style='background:rgba(127,29,29,0.2); border:1px solid rgba(252,165,165,0.3);
                        border-radius:12px; padding:20px; text-align:center; margin-top:10px'>
                <div style='font-size:3rem'>📵</div>
                <div style='color:#fca5a5; font-weight:600; margin-top:8px'>Kamera Offline</div>
                <div style='color:#64748b; font-size:0.82rem; margin-top:4px'>
                    Kamera ini sedang tidak tersambung. Pilih kamera lain yang berstatus 🟢.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Pilih simpang / lampu merah dari daftar di atas.")

    else:
        st.error("❌ Gagal mengambil daftar CCTV lampu merah. Periksa koneksi internet atau coba refresh.")





# --------------------------------------------------
# TAB ENGINE – DETEKSI REAL-TIME
# --------------------------------------------------
# State engine disimpan di session_state agar persisten lintas rerun
if "engine_thread" not in st.session_state:
    st.session_state.engine_thread = None
# Gunakan dict yang bisa diakses dari thread secara aman
if "engine_state" not in st.session_state:
    st.session_state.engine_state = {"instance": None, "running": False}
if "engine_log_queue" not in st.session_state:
    st.session_state.engine_log_queue = queue.Queue(maxsize=200)
if "engine_running" not in st.session_state:
    st.session_state.engine_running = False
if "engine_cam_name" not in st.session_state:
    st.session_state.engine_cam_name = ""

with tab_engine:
    st.markdown(
        '<div class="section-header">🎯 Engine Deteksi Pelanggaran — Real-time HLS CCTV</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div style='
        background: rgba(30,64,175,0.15);
        border: 1px solid rgba(99,179,237,0.25);
        border-radius: 10px;
        padding: 10px 16px;
        font-size: 0.82rem;
        color: #93c5fd;
        margin-bottom: 16px;
    '>
        🎯 Jalankan engine YOLOv8 + ByteTrack secara real-time pada stream HLS dari kamera
        CCTV ATCS Jogja Istimewa. Engine berjalan di <b>background thread</b> dan
        menyimpan pelanggaran langsung ke database PostgreSQL.
    </div>
    """, unsafe_allow_html=True)

    ecol1, ecol2 = st.columns([2, 1])

    with ecol1:
        st.markdown("#### 📡 Pilih Kamera CCTV Real-time")

        # Cache fetch kamera 5 menit
        @st.cache_data(ttl=300, show_spinner="Mengambil daftar kamera CCTV Jogja...")
        def _cached_engine_cams():
            return fetch_jogja_cctv_cameras(traffic_light_only=True)

        engine_cams = _cached_engine_cams()

        if engine_cams:
            # Filter hanya kamera yang online
            online_cams = [c for c in engine_cams if c.get("connected")]
            all_cams = engine_cams

            cam_filter = st.radio(
                "🔍 Tampilkan kamera:",
                ["🟢 Online saja", "🌐 Semua kamera"],
                horizontal=True,
                key="engine_cam_filter"
            )
            cams_to_show = online_cams if cam_filter == "🟢 Online saja" else all_cams

            if cams_to_show:
                cam_labels = {
                    f"{'🟢' if c.get('connected') else '🔴'} {c['name']} ({c.get('group_name','DIY')})": c
                    for c in cams_to_show
                }
                chosen_cam_label = st.selectbox(
                    f"Pilih simpang / lampu merah ({len(cams_to_show)} tersedia)",
                    options=list(cam_labels.keys()),
                    key="engine_cam_select"
                )
                chosen_cam = cam_labels[chosen_cam_label]

                st.markdown(f"""
                <div style='
                    background: rgba(15,22,48,0.8);
                    border: 1px solid rgba(99,179,237,0.2);
                    border-radius: 10px;
                    padding: 12px 16px;
                    font-size: 0.8rem;
                    color: #94a3b8;
                    margin-top: 8px;
                    line-height: 1.8;
                '>
                    <b style='color:#e2e8f0'>{chosen_cam['name']}</b><br>
                    📡 Stream: <code style='color:#63b3ed;font-size:0.72rem'>{chosen_cam['stream_url']}</code><br>
                    🏛 Pengelola: {chosen_cam.get('group_name','Pemprov DIY')}<br>
                    🗺 Koordinat: {f"{chosen_cam['lat']:.5f}, {chosen_cam['lng']:.5f}" if chosen_cam.get('lat') else '—'}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Tidak ada kamera online saat ini.")
                chosen_cam = None
        else:
            st.error("❌ Gagal mengambil daftar kamera dari API ATCS Jogja. Periksa koneksi internet.")
            chosen_cam = None

    with ecol2:
        st.markdown("#### ⚙️ Konfigurasi Engine")
        engine_location_key = "cctv_live"

        # Slider konfigurasi garis henti
        stop_line_y = st.slider(
            "📏 Garis Henti (Y-koordinat pixel)",
            min_value=100, max_value=700, value=400, step=10,
            key="engine_stopline_y",
            help="Posisi garis henti horizontal dalam pixel dari atas frame"
        )
        tl_roi_x = st.slider(
            "🚦 ROI Lampu (X dari kanan, pixel)",
            min_value=0, max_value=1200, value=900, step=20,
            key="engine_tl_roi_x"
        )
        tl_roi_y = st.slider(
            "🚦 ROI Lampu (Y dari atas, pixel)",
            min_value=0, max_value=400, value=30, step=10,
            key="engine_tl_roi_y"
        )

        # Status engine — cek apakah thread masih hidup
        is_alive = (
            st.session_state.engine_thread is not None
            and st.session_state.engine_thread.is_alive()
        )
        # Sync flag
        if not is_alive:
            st.session_state.engine_running = False
            st.session_state.engine_state["running"] = False
        status_html = (
            "<span class='badge-red'>● BERJALAN</span>"
            if is_alive else
            "<span class='badge-green'>⏹ BERHENTI</span>"
        )
        st.markdown(
            f"<div style='margin:12px 0 4px'><b>Status Engine:</b> {status_html}</div>",
            unsafe_allow_html=True
        )
        if is_alive:
            st.caption(f"📍 Kamera: {st.session_state.engine_cam_name}")

    st.markdown("---")

    # Tombol START / STOP
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])

    with btn_col1:
        start_disabled = (
            chosen_cam is None
            or not chosen_cam.get("connected")
            or is_alive
        )
        if st.button(
            "▶ Mulai Deteksi Real-time",
            disabled=start_disabled,
            key="engine_start_btn",
            use_container_width=True,
            type="primary"
        ):
            import copy as _copy
            # Buat salinan konfigurasi lokasi dan isi source dari kamera yang dipilih
            live_cfg = _copy.deepcopy(LOCATION_CONFIGS["cctv_live"])
            live_cfg["source"] = chosen_cam["stream_url"]
            live_cfg["source_type"] = "hls"
            live_cfg["name"] = chosen_cam["name"]
            live_cfg["description"] = f"CCTV Real-time: {chosen_cam['name']}"
            live_cfg["stopline"] = (50, stop_line_y, 1230, stop_line_y)
            live_cfg["traffic_light_roi"] = (tl_roi_x, tl_roi_y, 150, 200)

            # Patch LOCATION_CONFIGS runtime (hanya untuk sesi ini)
            LOCATION_CONFIGS["cctv_live"] = live_cfg

            log_q = st.session_state.engine_log_queue
            # Bersihkan log lama
            while not log_q.empty():
                try:
                    log_q.get_nowait()
                except queue.Empty:
                    break
            st.session_state.engine_log_history = []

            # Gunakan shared dict yang bisa diakses dari dalam thread
            engine_state = st.session_state.engine_state

            def _run_engine(cfg_snapshot, log_queue, _engine_state):
                """Target thread untuk engine deteksi."""
                from src.db_manager import DatabaseManager as _DBM
                from src.traffic_engine import TrafficViolationEngine as _TVE
                try:
                    db_inst = _DBM()
                    engine = _TVE(
                        location_key="cctv_live",
                        db_manager=db_inst
                    )
                    # Simpan ke shared dict agar bisa di-stop dari luar thread
                    _engine_state["instance"] = engine
                    _engine_state["running"] = True
                    log_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] ▶ Engine dimulai: {cfg_snapshot['name']}")
                    log_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 Stream: {cfg_snapshot['source']}")
                    engine.start(show_preview=False)
                except Exception as ex:
                    import traceback
                    log_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {ex}")
                    log_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Detail: {traceback.format_exc()[-300:]}")
                finally:
                    _engine_state["running"] = False
                    _engine_state["instance"] = None
                    log_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] ⏹ Engine berhenti.")

            t = threading.Thread(
                target=_run_engine,
                args=(live_cfg, log_q, engine_state),
                daemon=True
            )
            t.start()
            st.session_state.engine_thread = t
            st.session_state.engine_cam_name = chosen_cam["name"]
            st.session_state.engine_running = True
            st.success(f"✅ Engine deteksi dimulai pada: **{chosen_cam['name']}**")
            time.sleep(0.8)
            st.rerun()

    with btn_col2:
        stop_disabled = not is_alive
        if st.button(
            "⏹ Hentikan Engine",
            disabled=stop_disabled,
            key="engine_stop_btn",
            use_container_width=True
        ):
            engine_inst = st.session_state.engine_state.get("instance")
            if engine_inst is not None:
                engine_inst.stop()
                st.warning("⏹ Sinyal stop dikirim ke engine. Tunggu beberapa detik...")
            else:
                st.warning("⏹ Engine sudah tidak berjalan.")
            time.sleep(2)
            st.rerun()

    # Log real-time
    st.markdown("#### 📝 Log Engine")
    log_container = st.container()
    log_messages = []
    while not st.session_state.engine_log_queue.empty():
        try:
            log_messages.append(st.session_state.engine_log_queue.get_nowait())
        except queue.Empty:
            break

    if "engine_log_history" not in st.session_state:
        st.session_state.engine_log_history = []
    st.session_state.engine_log_history.extend(log_messages)
    # Simpan hanya 30 log terakhir
    st.session_state.engine_log_history = st.session_state.engine_log_history[-30:]

    with log_container:
        if st.session_state.engine_log_history:
            log_text = "\n".join(reversed(st.session_state.engine_log_history))
            st.code(log_text, language=None)
        else:
            st.markdown(
                "<div style='color:#475569;font-size:0.82rem;padding:12px'>"
                "Belum ada log. Mulai engine untuk melihat output real-time.</div>",
                unsafe_allow_html=True
            )

    # Live stats dari engine (jika sedang berjalan)
    _live_eng = st.session_state.engine_state.get("instance")
    if is_alive and _live_eng is not None:
        st.markdown("#### 📊 Statistik Live Engine")
        es1, es2, es3, es4 = st.columns(4)
        es1.metric("🔴 Lampu Merah", "YA" if _live_eng.is_red_light else "Tidak")
        es2.metric("⚠️ Pelanggaran Sesi", _live_eng.violation_count)
        es3.metric("🎞 Frame Diproses", _live_eng.frame_count)
        avg_fps = sum(_live_eng.fps_history[-20:]) / len(_live_eng.fps_history[-20:]) if _live_eng.fps_history else 0
        es4.metric("⚡ FPS Rata-rata", f"{avg_fps:.1f}")

        # Live Preview Frame dengan Kotak Deteksi (Bounding Box)
        st.markdown("#### 📺 Live Preview Deteksi CCTV (Kotak Bounding Box Real-time)")
        latest_annotated = getattr(_live_eng, "latest_annotated_frame", None)
        if latest_annotated is not None:
            import cv2
            rgb_frame = cv2.cvtColor(latest_annotated, cv2.COLOR_BGR2RGB)
            st.image(
                rgb_frame,
                caption=f"🎯 Visualisasi Bounding Box & Pelacakan: {st.session_state.engine_cam_name}",
                use_container_width=True
            )
        else:
            st.info("⏳ Memuat frame deteksi pertama dari stream CCTV...")

    # Info petunjuk
    with st.expander("ℹ️ Petunjuk Penggunaan Engine Real-time"):
        st.markdown("""
        **Cara menggunakan Engine Deteksi Real-time:**

        1. **Pilih kamera** dari daftar CCTV ATCS Jogja yang berstatus 🟢 Online
        2. **Sesuaikan garis henti** (Y-koordinat): Posisi garis horizontal yang dianggap
           sebagai batas henti kendaraan. Gunakan preview HLS di tab "Live CCTV" untuk
           menentukan posisi yang tepat.
        3. **Sesuaikan ROI Lampu Merah**: Area pada frame di mana engine akan mengecek
           warna lampu (merah/hijau) menggunakan analisis HSV.
        4. **Klik "Mulai Deteksi Real-time"**: Engine berjalan di background thread,
           membaca stream HLS dari CCTV yang dipilih, menjalankan YOLOv8 + ByteTrack,
           dan menyimpan pelanggaran ke PostgreSQL secara otomatis.
        5. **Monitor di tab Analitik & Log**: Pelanggaran yang terdeteksi akan langsung
           muncul di tab Log Pelanggaran dan Galeri Bukti.
        6. **Hentikan** dengan tombol "⏹ Hentikan Engine" jika sudah selesai.

        > ⚠️ **Catatan:** Engine memerlukan OpenCV yang di-build dengan dukungan FFmpeg
        > agar bisa membaca stream HLS (m3u8). Pastikan `opencv-python` versi >= 4.5
        > sudah terinstall. Jika stream tidak terbuka, coba pilih kamera lain yang online.
        """)


# --------------------------------------------------
# TAB 1 – ANALITIK
# --------------------------------------------------
with tab_analitik:
    col_chart1, col_chart2 = st.columns([3, 2])

    with col_chart1:
        hourly_fig = build_hourly_chart(hourly_data, selected_date_str)
        st.plotly_chart(hourly_fig, width='stretch', config={"displayModeBar": False})

    with col_chart2:
        vehicle_fig = build_vehicle_pie(vehicle_data)
        st.plotly_chart(vehicle_fig, width='stretch', config={"displayModeBar": False})

    st.markdown("---")

    col_weekly, col_stats = st.columns([3, 2])

    with col_weekly:
        weekly_fig = build_weekly_bar(weekly_data)
        st.plotly_chart(weekly_fig, width='stretch', config={"displayModeBar": False})

    with col_stats:
        st.markdown('<div class="section-header">📌 Ringkasan Statistik</div>',
                    unsafe_allow_html=True)

        # Rata-rata per jam
        avg_per_hour = round(total_today / 24, 1) if total_today else 0

        # Persentase motor
        motor_pct = round((motor_count / total_today * 100), 1) if total_today else 0

        stats_html = f"""
        <div style='display: flex; flex-direction: column; gap: 12px; margin-top: 8px'>
            <div class='stat-card'>
                <div class='stat-value'>{avg_per_hour}</div>
                <div class='stat-label'>Rata-rata / jam</div>
            </div>
            <div class='stat-card'>
                <div class='stat-value'>{motor_pct}%</div>
                <div class='stat-label'>Dominasi motor</div>
            </div>
            <div class='stat-card'>
                <div class='stat-value'>{len(weekly_data)}</div>
                <div class='stat-label'>Hari aktif (7 hari)</div>
            </div>
        </div>
        """
        st.markdown(stats_html, unsafe_allow_html=True)

# --------------------------------------------------
# TAB 2 – LOG PELANGGARAN
# --------------------------------------------------
with tab_log:
    st.markdown('<div class="section-header">📋 Log Kejadian Terbaru</div>',
                unsafe_allow_html=True)

    if recent_violations:
        df_log = pd.DataFrame(recent_violations)

        # Format kolom
        if "timestamp" in df_log.columns:
            df_log["timestamp"] = pd.to_datetime(df_log["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")

        # Rename dan pilih kolom untuk ditampilkan
        display_cols = {
            "id": "ID",
            "timestamp": "Waktu",
            "cctv_location": "Lokasi",
            "vehicle_type": "Jenis Kendaraan",
            "vehicle_id": "ID Kendaraan",
            "evidence_img_path": "Foto Bukti"
        }
        df_display = df_log[[c for c in display_cols if c in df_log.columns]].rename(columns=display_cols)

        # Ganti kode lokasi dengan nama lengkap
        if "Lokasi" in df_display.columns:
            df_display["Lokasi"] = df_display["Lokasi"].map(
                {k: v["name"] for k, v in LOCATION_CONFIGS.items()}
            ).fillna(df_display["Lokasi"])

        # Ganti vehicle_type dengan emoji
        if "Jenis Kendaraan" in df_display.columns:
            df_display["Jenis Kendaraan"] = df_display["Jenis Kendaraan"].map({
                "car": "🚗 Mobil",
                "motorcycle": "🏍 Sepeda Motor",
                "bus": "🚌 Bus",
                "truck": "🚛 Truk",
            }).fillna(df_display["Jenis Kendaraan"])

        st.dataframe(
            df_display,
            width='stretch',
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn(width="small"),
                "Waktu": st.column_config.TextColumn(width="medium"),
                "Foto Bukti": st.column_config.TextColumn(width="large"),
            }
        )

        # Tombol download CSV
        csv = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇ Download Log sebagai CSV",
            data=csv,
            file_name=f"violations_{selected_date_str}.csv",    
            mime="text/csv",
        )
    else:
        st.info("🎉 Belum ada pelanggaran tercatat untuk filter yang dipilih.")

# --------------------------------------------------
# TAB 3 – GALERI BUKTI
# --------------------------------------------------
with tab_galeri:
    st.markdown('<div class="section-header">🖼 Galeri Foto Bukti Pelanggaran</div>',
                unsafe_allow_html=True)

    if recent_violations:
        # Filter hanya yang file fotonya ada
        valid_violations = [
            v for v in recent_violations
            if v.get("evidence_img_path") and Path(v["evidence_img_path"]).exists()
        ]

        if valid_violations:
            cols_per_row = 4
            for i in range(0, len(valid_violations), cols_per_row):
                row_cols = st.columns(cols_per_row)
                for j, col in enumerate(row_cols):
                    idx = i + j
                    if idx < len(valid_violations):
                        v = valid_violations[idx]
                        with col:
                            ts = v.get("timestamp", "")
                            if hasattr(ts, "strftime"):
                                ts_str = ts.strftime("%H:%M:%S")
                            else:
                                ts_str = str(ts)[:19] if ts else "—"

                            vtype_map = {
                                "car": "🚗 Mobil",
                                "motorcycle": "🏍 Motor",
                                "bus": "🚌 Bus",
                                "truck": "🚛 Truk",
                            }
                            vtype = vtype_map.get(v.get("vehicle_type", ""), v.get("vehicle_type", ""))

                            st.image(
                                v["evidence_img_path"],
                                caption=f"{vtype} | ID #{v.get('vehicle_id')} | {ts_str}",
                                width='stretch',
                            )
        else:
            st.info("📁 File foto bukti tidak ditemukan di disk. Pastikan engine sudah berjalan dan menyimpan gambar ke folder `evidence_images/`.")
    else:
        st.info("🎉 Belum ada foto bukti untuk ditampilkan.")

# =====================================================
# AUTO-REFRESH
# =====================================================
if auto_refresh and is_today:
    time.sleep(DASHBOARD_REFRESH_INTERVAL)
    st.rerun()

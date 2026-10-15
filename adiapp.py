import base64
import html
import io
import json
import random
import re
import time
import urllib.parse
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURATION & CONSTANTS ---
SHOP_NAME = "Cartel Shop"
WHATSAPP_NUMBER = "918089523293"  # WhatsApp business number with country code
SUPPORT_EMAIL = ""
ADMIN_PAGE_KEY = "rootcartel"  # Open admin dashboard via ?page=rootcartel
ADMIN_USERNAME = st.secrets.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "adithyan1234")
CURRENCY = "Rs."

ORDER_COLS = ["Order ID", "TimeStamp", "Custumer Name", "Phone Number",
              "PIN Code", "Full Adress", "Order Items & Total", "Status"]
PRODUCT_COLS = ["Products", "Product ID", "Title", "Price", "Description",
                "Image 1", "Image 2", "Image 3", "Active",
                "Colors", "Keywords", "Bulk Qty", "Bulk Disc %"]
CUSTOMER_COLS = ["Customer ID", "Name", "Phone Number", "State", "District",
                 "PIN Code", "Full Adress", "Created"]
STATUS_OPTIONS = ["Pending", "Confirmed", "In Transit", "Delivered", "Cancelled"]

# Edit these terms to match your shop policy (shown only in the Profile tab)
TERMS = [
    "Orders are confirmed by our team on WhatsApp before dispatch.",
    "Prices shown are as listed in the shop and may change without notice.",
    "Delivery time depends on your location and product availability.",
    "Please keep your phone reachable so we can confirm your order and address.",
    "For cancellations or issues, contact us on WhatsApp as soon as possible.",
]

STATES = ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
          "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
          "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
          "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
          "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
          "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir", "Ladakh",
          "Lakshadweep", "Puducherry"]

_D = {
    "Kerala": "Alappuzha,Ernakulam,Idukki,Kannur,Kasaragod,Kollam,Kottayam,Kozhikode,Malappuram,Palakkad,Pathanamthitta,Thiruvananthapuram,Thrissur,Wayanad",
    "Tamil Nadu": "Ariyalur,Chengalpattu,Chennai,Coimbatore,Cuddalore,Dharmapuri,Dindigul,Erode,Kallakurichi,Kanchipuram,Kanyakumari,Karur,Krishnagiri,Madurai,Mayiladuthurai,Nagapattinam,Namakkal,Nilgiris,Perambalur,Pudukkottai,Ramanathapuram,Ranipet,Salem,Sivaganga,Tenkasi,Thanjavur,Theni,Thoothukudi,Tiruchirappalli,Tirunelveli,Tirupathur,Tiruppur,Tiruvallur,Tiruvannamalai,Tiruvarur,Vellore,Viluppuram,Virudhunagar",
    "Karnataka": "Bagalkot,Ballari,Belagavi,Bengaluru Rural,Bengaluru Urban,Bidar,Chamarajanagar,Chikkaballapur,Chikkamagaluru,Chitradurga,Dakshina Kannada,Davanagere,Dharwad,Gadag,Hassan,Haveri,Kalaburagi,Kodagu,Kolar,Koppal,Mandya,Mysuru,Raichur,Ramanagara,Shivamogga,Tumakuru,Udupi,Uttara Kannada,Vijayanagara,Vijayapura,Yadgir",
    "Maharashtra": "Ahmednagar,Akola,Amravati,Aurangabad,Beed,Bhandara,Buldhana,Chandrapur,Dhule,Gadchiroli,Gondia,Hingoli,Jalgaon,Jalna,Kolhapur,Latur,Mumbai City,Mumbai Suburban,Nagpur,Nanded,Nandurbar,Nashik,Osmanabad,Palghar,Parbhani,Pune,Raigad,Ratnagiri,Sangli,Satara,Sindhudurg,Solapur,Thane,Wardha,Washim,Yavatmal",
    "Delhi": "Central Delhi,East Delhi,New Delhi,North Delhi,North East Delhi,North West Delhi,Shahdara,South Delhi,South East Delhi,South West Delhi,West Delhi",
    "Telangana": "Adilabad,Hyderabad,Karimnagar,Khammam,Mahabubnagar,Medak,Nalgonda,Nizamabad,Rangareddy,Sangareddy,Warangal",
    "Andhra Pradesh": "Anantapur,Chittoor,East Godavari,Guntur,Krishna,Kurnool,Nellore,Prakasam,Srikakulam,Visakhapatnam,Vizianagaram,West Godavari,YSR Kadapa",
    "Gujarat": "Ahmedabad,Amreli,Anand,Bharuch,Bhavnagar,Gandhinagar,Jamnagar,Junagadh,Kutch,Mehsana,Rajkot,Surat,Vadodara,Valsad",
    "Rajasthan": "Ajmer,Alwar,Bharatpur,Bikaner,Jaipur,Jaisalmer,Jodhpur,Kota,Sikar,Udaipur",
    "Uttar Pradesh": "Agra,Aligarh,Allahabad (Prayagraj),Bareilly,Ghaziabad,Gorakhpur,Kanpur Nagar,Lucknow,Meerut,Mathura,Noida (Gautam Buddha Nagar),Varanasi",
    "Madhya Pradesh": "Bhopal,Gwalior,Indore,Jabalpur,Sagar,Satna,Ujjain",
    "West Bengal": "Darjeeling,Hooghly,Howrah,Kolkata,North 24 Parganas,South 24 Parganas,Murshidabad,Nadia,Siliguri (Darjeeling)",
    "Bihar": "Bhagalpur,Darbhanga,Gaya,Muzaffarpur,Patna,Purnia",
    "Odisha": "Bhubaneswar (Khordha),Cuttack,Ganjam,Puri,Rourkela (Sundargarh),Sambalpur",
    "Punjab": "Amritsar,Bathinda,Jalandhar,Ludhiana,Mohali,Patiala",
    "Haryana": "Ambala,Faridabad,Gurugram,Hisar,Karnal,Panipat,Rohtak",
    "Assam": "Dibrugarh,Guwahati (Kamrup Metro),Jorhat,Silchar (Cachar),Tezpur (Sonitpur)",
    "Jharkhand": "Bokaro,Dhanbad,Jamshedpur (East Singhbhum),Ranchi",
    "Chhattisgarh": "Bilaspur,Durg,Raipur,Raigarh",
    "Uttarakhand": "Dehradun,Haridwar,Nainital,Udham Singh Nagar",
    "Himachal Pradesh": "Kangra,Mandi,Shimla,Solan",
    "Goa": "North Goa,South Goa",
    "Puducherry": "Karaikal,Mahe,Puducherry,Yanam",
    "Chandigarh": "Chandigarh",
    "Jammu and Kashmir": "Jammu,Srinagar,Anantnag,Baramulla",
}
DISTRICTS = {k: v.split(",") for k, v in _D.items()}

st.set_page_config(page_title=SHOP_NAME, page_icon="🛒", layout="centered",
                   initial_sidebar_state="collapsed")

# --- STYLES ---
CSS = """
<style>
:root { --accent:#FF5722; --accent-dark:#E64A19; --ink:#111827; --muted:#6B7280; --bg:#F4F6F9; }
#MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {display:none !important;}
.stApp {background:var(--bg);}
.block-container {padding:0.4rem 1rem 7rem 1rem !important; max-width:520px;}
h1,h2,h3,p,span,div,label {font-family:'Inter','Segoe UI',sans-serif;}

.hdr {display:flex; justify-content:space-between; align-items:center; margin:0 0 .8rem 0;}
.hdr .hi {font-size:.85rem; color:var(--muted);}
.hdr .nm {font-size:1.25rem; font-weight:800; color:var(--ink); letter-spacing:.2px;}
.hdr .badge {width:42px; height:42px; border-radius:14px; background:#fff; display:flex;
  align-items:center; justify-content:center; box-shadow:0 2px 10px rgba(0,0,0,.06);}

.banner {background:linear-gradient(135deg,#1e1b4b,#312e81); border-radius:20px; padding:1.2rem 1.2rem;
  margin:.4rem 0 1rem 0; color:#fff; position:relative; overflow:hidden;}
.banner::after {content:""; position:absolute; right:-30px; top:-30px; width:140px; height:140px;
  border-radius:50%; background:rgba(255,255,255,.08);}
.banner .t {font-size:1.1rem; color:#cbd5e1; font-weight:600;}
.banner .s {font-size:1.5rem; font-weight:800; color:#f97316; margin-top:.2rem;}

.sec {display:flex; justify-content:space-between; align-items:center; margin:.4rem 0 .6rem 0;}
.sec .a {font-size:1.05rem; font-weight:800; color:var(--ink);}

.pc {background:#fff; border-radius:18px; padding:.55rem; box-shadow:0 2px 12px rgba(0,0,0,.05); margin-bottom:.4rem;}
.car {display:flex; overflow-x:auto; scroll-snap-type:x mandatory; scrollbar-width:none; border-radius:14px;
  aspect-ratio:1/1; background:#EEF0F4; -webkit-overflow-scrolling:touch;}
.car::-webkit-scrollbar {display:none;}
.car img {flex:0 0 100%; width:100%; height:100%; object-fit:cover; scroll-snap-align:start;}
.pt {font-size:.88rem; font-weight:700; color:var(--ink); margin-top:.5rem; height:2.4em; overflow:hidden;
  line-height:1.2em;}
.pp {font-size:.95rem; font-weight:800; color:var(--accent-dark); margin:.15rem 0 .1rem 0;}
.bk {font-size:.68rem; color:#047857; font-weight:700; height:1.1em; overflow:hidden; white-space:nowrap;}
.dots {height:18px; display:flex; gap:5px; align-items:center; margin:.15rem 0 .3rem 0;}
.dots span {width:13px; height:13px; border-radius:50%; box-shadow:0 0 0 1.5px #fff, 0 0 0 2.5px #cbd5e1; display:inline-block;}

/* Buttons */
.stButton > button, .stDownloadButton > button, .stLinkButton > a, .stFormSubmitButton > button {
  border-radius:12px !important; font-weight:700 !important; border:1px solid #E5E7EB !important;
  background:#fff !important; color:var(--ink) !important; width:100%;}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"], .stLinkButton > a[kind="primary"] {
  background:var(--accent) !important; color:#fff !important; border:none !important;}
.stButton > button[kind="primary"]:hover {background:var(--accent-dark) !important;}

/* Search with animated lens */
.st-key-searchbox {position:relative;}
.st-key-searchbox::before {content:""; position:absolute; left:14px; top:50%; width:18px; height:18px; margin-top:-9px; z-index:5;
  pointer-events:none; animation:lens 2.4s ease-in-out infinite;
  background:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23FF5722' stroke-width='2.4' stroke-linecap='round'><circle cx='10.5' cy='10.5' r='6.5'/><line x1='15.5' y1='15.5' x2='21' y2='21'/></svg>") no-repeat center/contain;}
@keyframes lens {0%,100% {transform:scale(1) rotate(0);} 50% {transform:scale(1.18) rotate(-12deg);}}
.st-key-searchbox [data-baseweb="select"] > div {padding-left:34px; border-radius:14px !important; background:#fff !important;}
.stTextInput input {border-radius:14px !important; background:#fff !important;}

/* Bottom Nav */
.st-key-bottomnav {position:fixed; left:0; right:0; bottom:0; z-index:999; background:#fff;
  padding:.45rem .6rem calc(.45rem + env(safe-area-inset-bottom)); box-shadow:0 -4px 20px rgba(0,0,0,.08);
  border-radius:20px 20px 0 0;}
.st-key-bottomnav [data-testid="stHorizontalBlock"] {flex-wrap:nowrap !important; gap:.3rem; max-width:520px; margin:0 auto;}
.st-key-bottomnav [data-testid="stColumn"] {min-width:0 !important; flex:1 1 0 !important;}
.st-key-bottomnav .stButton > button {border:none !important; background:transparent !important;
  font-size:.72rem !important; padding:.25rem 0 !important; color:var(--muted) !important;
  flex-direction:column; height:auto;}
.st-key-bottomnav .stButton > button[kind="primary"] {background:transparent !important; color:var(--accent) !important;}

.cartrow {background:#fff; border-radius:16px; padding:.5rem; display:flex; gap:.7rem; align-items:center;
  box-shadow:0 2px 10px rgba(0,0,0,.05); margin-bottom:.3rem;}
.cartrow img {width:64px; height:64px; border-radius:12px; object-fit:cover; background:#EEF0F4;}
.cartrow .ct {font-weight:700; font-size:.9rem; color:var(--ink);}
.cartrow .cs {font-size:.72rem; color:var(--muted);}
.cartrow .cp {font-weight:800; font-size:.9rem; color:var(--accent-dark);}
.sumbox {background:#fff; border-radius:16px; padding:.8rem 1rem; margin:.6rem 0;
  box-shadow:0 2px 10px rgba(0,0,0,.05);}
.sumbox .r {display:flex; justify-content:space-between; font-size:.9rem; color:var(--muted); padding:.15rem 0; gap:.6rem;}
.sumbox .tot {font-weight:800; color:var(--ink); font-size:1.05rem;}
.foot {text-align:center; color:var(--muted); font-size:.78rem; margin-top:1.5rem;}
.ostat {display:inline-block; padding:.1rem .6rem; border-radius:999px; font-size:.72rem; font-weight:700;
  background:#FFEDD5; color:var(--accent-dark); white-space:nowrap;}
.ostat.ok {background:#D1FAE5; color:#047857;}
.ostat.bad {background:#FEE2E2; color:#B91C1C;}

/* Tracking steps */
.steps {display:flex; justify-content:space-between; margin:.6rem 0 .2rem 0;}
.steps div {flex:1; text-align:center; font-size:.68rem; color:var(--muted); position:relative;}
.steps div::before {content:""; display:block; width:14px; height:14px; border-radius:50%; background:#E5E7EB; margin:0 auto .3rem;}
.steps div.on {color:var(--ink); font-weight:700;}
.steps div.on::before {background:var(--accent);}

/* Admin KPI cards */
.kpis {display:grid; grid-template-columns:1fr 1fr; gap:.6rem; margin:.4rem 0 .8rem 0;}
.kpi {background:#fff; border-radius:16px; padding:.7rem .9rem; box-shadow:0 2px 10px rgba(0,0,0,.05);}
.kpi .l {font-size:.72rem; color:var(--muted); font-weight:600; text-transform:uppercase; letter-spacing:.4px;}
.kpi .v {font-size:1.35rem; font-weight:800; color:var(--ink);}
.kpi.hot .v {color:var(--accent-dark);}
.chip {display:inline-flex; align-items:center; gap:.4rem; background:#fff; border-radius:999px; padding:.2rem .7rem;
  font-size:.8rem; margin:0 .3rem .3rem 0; box-shadow:0 1px 6px rgba(0,0,0,.08);}
.chip i {width:14px; height:14px; border-radius:50%; display:inline-block; box-shadow:0 0 0 1.5px #cbd5e1;}

/* Order placed truck animation */
.trk {background:#fff; border-radius:18px; padding:.6rem; margin:.4rem 0 .8rem 0; box-shadow:0 2px 10px rgba(0,0,0,.05); overflow:hidden;}
.trk svg {width:100%; height:auto; display:block;}
.trk .truck {animation:drive 3.6s ease-in infinite;}
.trk .box {animation:dropbox 3.6s ease-out infinite;}
.trk .road {animation:road .5s linear infinite;}
@keyframes drive {0%,32% {transform:translateX(0); opacity:1;} 92% {transform:translateX(210px); opacity:1;} 100% {transform:translateX(250px); opacity:0;}}
@keyframes dropbox {0% {transform:translateY(-70px); opacity:0;} 8% {opacity:1;} 28%,100% {transform:translateY(0); opacity:1;}}
@keyframes road {to {stroke-dashoffset:-18;}}

/* Always-visible typed text (fixes white-on-white in dark mode) */
:root, .stApp {color-scheme:light;}
.stApp label, .stApp [data-testid="stWidgetLabel"] p, .stApp [data-testid="stCaptionContainer"] {color:#374151 !important;}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {color:var(--ink) !important;}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p, [data-testid="stMain"] [data-testid="stMarkdownContainer"] li {color:var(--ink);}
.stButton button p, .stLinkButton a p, .stFormSubmitButton button p {color:inherit !important;}
.stButton button[kind="primary"] p, .stFormSubmitButton button[kind="primary"] p, .stLinkButton a[kind="primary"] p {color:#fff !important;}
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input,
[data-baseweb="select"] input, [data-baseweb="select"] [class*="singleValue"], [data-baseweb="select"] div {
  color:#111827 !important; -webkit-text-fill-color:#111827 !important; caret-color:#111827;}
.stTextInput input, .stTextArea textarea, .stNumberInput input {background:#fff !important;}
.stTextInput > div > div, .stTextArea > div > div, .stNumberInput > div > div, [data-baseweb="select"] > div {
  background:#fff !important; border-color:#E5E7EB !important;}
input::placeholder, textarea::placeholder {color:#9CA3AF !important; -webkit-text-fill-color:#9CA3AF !important; opacity:1 !important;}
[data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="menu"] {background:#fff !important; color:#111827 !important;}
[data-baseweb="popover"] li * {color:#111827 !important; -webkit-text-fill-color:#111827 !important;}
[data-testid="stDialog"] > div, div[role="dialog"] {background:#fff !important; color:#111827;}
[data-testid="stExpander"] details {background:#fff; border-radius:14px;}
[data-testid="stExpander"] summary p {color:var(--ink) !important;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

TRUCK_SVG = """
<div class="trk"><svg viewBox="0 0 360 130" xmlns="http://www.w3.org/2000/svg">
  <line class="road" x1="0" y1="112" x2="360" y2="112" stroke="#cbd5e1" stroke-width="3" stroke-dasharray="10 8"/>
  <g class="truck">
    <rect x="30" y="48" width="120" height="52" rx="6" fill="#312e81"/>
    <path d="M150 62 h34 l18 20 v18 h-52 z" fill="#FF5722"/>
    <rect x="168" y="68" width="16" height="13" rx="2" fill="#fff" opacity=".85"/>
    <circle cx="64" cy="104" r="11" fill="#111827"/><circle cx="64" cy="104" r="4" fill="#9ca3af"/>
    <circle cx="176" cy="104" r="11" fill="#111827"/><circle cx="176" cy="104" r="4" fill="#9ca3af"/>
    <g class="box"><rect x="62" y="22" width="44" height="26" rx="3" fill="#F59E0B"/>
      <rect x="62" y="31" width="44" height="5" fill="#B45309"/></g>
  </g>
</svg></div>
"""

# --- DATA LAYER ---
conn = st.connection("gsheets", type=GSheetsConnection)

PLACEHOLDER_IMG = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'>"
                   "<rect width='300' height='300' fill='%23EEF0F4'/></svg>")


def sval(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip()
    return "" if s.lower() == "nan" else s


def _clean(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols].dropna(how="all").reset_index(drop=True)
    return df


def read_sheet(name: str, cols: list, strict: bool = False) -> pd.DataFrame:
    """strict=True raises on failure (used before any write so a failed read can never wipe data)."""
    try:
        df = conn.read(worksheet=name, ttl=0)
        df = _clean(df, cols)
        if df.empty and name == "products":
            rows = [
                ("P101", "Cartel Signature Tee", 499, "Premium cotton streetwear t-shirt."),
                ("P102", "Tactical Utility Pouch", 699, "Durable multi-purpose gear pouch."),
                ("P103", "Custom Engraved Dog Tag", 299, "Stainless steel personalized ID tag."),
            ]
            default_df = pd.DataFrame([
                {**{c: "" for c in cols}, "Products": i + 1, "Product ID": r[0], "Title": r[1],
                 "Price": r[2], "Description": r[3], "Active": "Yes"} for i, r in enumerate(rows)])
            conn.update(worksheet="products", data=default_df)
            return default_df
        return df
    except Exception:
        if strict:
            raise
        return pd.DataFrame(columns=cols)


def write_sheet(name: str, df: pd.DataFrame):
    conn.update(worksheet=name, data=df)


def is_active(v) -> bool:
    return str(v).strip().lower() in ("yes", "true", "1", "y", "active", "1.0")


def load_products(force: bool = False) -> pd.DataFrame:
    if force or "products_df" not in st.session_state:
        df = read_sheet("products", PRODUCT_COLS)
        df = df[df["Product ID"].notna()].reset_index(drop=True)
        st.session_state.products_df = df
    return st.session_state.products_df


def to_price(v) -> float:
    try:
        x = float(v)
        return 0.0 if pd.isna(x) else x
    except Exception:
        return 0.0


def to_int(v) -> int:
    return int(to_price(v))


def fmt(v: float) -> str:
    return f"{CURRENCY} {v:,.0f}" if float(v).is_integer() else f"{CURRENCY} {v:,.2f}"


def img_of(row, i=1) -> str:
    return sval(row.get(f"Image {i}"))


def images_of(row) -> list:
    return [x for x in (img_of(row, i) for i in (1, 2, 3)) if x] or [PLACEHOLDER_IMG]


def process_upload(file) -> str:
    img = Image.open(file).convert("RGB")
    for size, quality in [(520, 72), (440, 65), (360, 58), (300, 50), (240, 45)]:
        im = img.copy()
        im.thumbnail((size, size))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=quality, optimize=True)
        data = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        if len(data) < 45000:
            return data
    return data


# colours are stored in one cell as  Name:#hex|Name:#hex
def parse_colors(s) -> list:
    out = []
    for part in sval(s).split("|"):
        if ":" in part:
            n, h = part.rsplit(":", 1)
            n, h = n.strip(), h.strip()
            if n and re.fullmatch(r"#[0-9a-fA-F]{6}", h):
                out.append((n, h))
    return out


def pack_colors(items) -> str:
    return "|".join(f"{n}:{h}" for n, h in items)


def clean_name(s: str) -> str:
    return re.sub(r"[|:~,]", " ", s).strip()


def unit_price(row, total_qty_of_product: int):
    p = to_price(row.get("Price"))
    bq, bd = to_int(row.get("Bulk Qty")), to_price(row.get("Bulk Disc %"))
    if bq > 0 and bd > 0 and total_qty_of_product >= bq:
        return round(p * (1 - bd / 100), 2), True
    return p, False


def bulk_text(row) -> str:
    bq, bd = to_int(row.get("Bulk Qty")), to_price(row.get("Bulk Disc %"))
    if bq > 0 and bd > 0:
        return f"Buy {bq}+ and save {bd:g}%"
    return ""


def safe_id(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", s)


# --- STATE ---
def parse_cart(s: str) -> dict:
    cart = {}
    for part in (s or "").split(","):
        if "~" in part:
            k, q = part.rsplit("~", 1)
            if q.isdigit() and int(q) > 0 and k:
                cart[k] = int(q)
    return cart


if "cart" not in st.session_state:
    st.session_state.cart = parse_cart(st.query_params.get("cart", ""))
if "tab" not in st.session_state:
    st.session_state.tab = "Home"
for _k, _v in (("last_order", None), ("customer", None), ("checkout", False), ("fly", None)):
    if _k not in st.session_state:
        st.session_state[_k] = _v


def sync_cart():
    """Keep the cart in the page URL so it survives a browser refresh."""
    val = ",".join(f"{k}~{q}" for k, q in st.session_state.cart.items() if q > 0)
    if val:
        if st.query_params.get("cart") != val:
            st.query_params["cart"] = val
    elif "cart" in st.query_params:
        del st.query_params["cart"]


def cart_count() -> int:
    return sum(st.session_state.cart.values())


def commit_add(row, color: str = "", qty: int = 1):
    pid = str(row["Product ID"])
    key = f"{pid}|{color}"
    st.session_state.cart[key] = st.session_state.cart.get(key, 0) + int(qty)
    st.session_state.fly = {"id": time.time(), "img": images_of(row)[0]}
    st.toast("Added to cart")


def footer():
    contact = f"WhatsApp: +{WHATSAPP_NUMBER}"
    if SUPPORT_EMAIL:
        contact += f" &nbsp;|&nbsp; {html.escape(SUPPORT_EMAIL)}"
    st.markdown(f"<div class='foot'>{SHOP_NAME} &nbsp;|&nbsp; {contact}</div>", unsafe_allow_html=True)


FX_JS = """
<script>
const P = __PAYLOAD__;
const W = window.parent, D = W.document;
if (!W.__cx) {
  W.__cx = true;
  D.addEventListener('click', e => { W.__lx = e.clientX; W.__ly = e.clientY; }, true);
  D.addEventListener('touchstart', e => {
    const c = e.target.closest && e.target.closest('.car'); if (c) c.__hold = Date.now();
  }, {passive: true});
}
if (W.__carT) W.clearInterval(W.__carT);
W.__carT = W.setInterval(() => {
  D.querySelectorAll('.car').forEach(c => {
    if (c.scrollWidth <= c.clientWidth + 4) return;
    if (c.__hold && Date.now() - c.__hold < 6000) return;
    const n = c.scrollLeft + c.clientWidth;
    c.scrollTo({left: n >= c.scrollWidth - 4 ? 0 : n, behavior: 'smooth'});
  });
}, 3200);
if (W.__phT) W.clearInterval(W.__phT);
if (P.titles.length) {
  let i = 0;
  W.__phT = W.setInterval(() => {
    const el = D.querySelector('.st-key-searchbox input');
    if (el && !el.value) el.placeholder = 'Search ' + P.titles[i % P.titles.length];
    i++;
  }, 2200);
}
if (P.fly && W.__lastFly !== P.fly.id) {
  W.__lastFly = P.fly.id;
  const btn = D.querySelector('.st-key-nav_Cart');
  if (btn) {
    const r = btn.getBoundingClientRect();
    const im = D.createElement('img');
    im.src = P.fly.img;
    im.style.cssText = 'position:fixed;z-index:99999;width:72px;height:72px;object-fit:cover;border-radius:14px;' +
      'box-shadow:0 6px 20px rgba(0,0,0,.25);pointer-events:none;transition:all .85s cubic-bezier(.55,-.15,.75,.45);' +
      'left:' + ((W.__lx || W.innerWidth / 2) - 36) + 'px;top:' + ((W.__ly || W.innerHeight / 2) - 36) + 'px;';
    D.body.appendChild(im);
    requestAnimationFrame(() => {
      im.style.left = (r.left + r.width / 2 - 10) + 'px';
      im.style.top = (r.top + r.height / 2 - 10) + 'px';
      im.style.width = '20px'; im.style.height = '20px'; im.style.opacity = '.35';
    });
    setTimeout(() => im.remove(), 950);
    btn.animate([{transform: 'scale(1)'}, {transform: 'scale(1.3)'}, {transform: 'scale(1)'}], {duration: 420, delay: 850});
  }
}
</script>
"""


def fx(titles=None):
    fly = st.session_state.get("fly")
    payload = json.dumps({"titles": titles or [], "fly": fly})
    components.html(FX_JS.replace("__PAYLOAD__", payload), height=0)
    st.session_state.fly = None


# =====================================================================
# SHARED UI PIECES
# =====================================================================
def carousel(images: list) -> str:
    imgs = "".join(f'<img src="{html.escape(i, quote=True)}" loading="lazy">' for i in images)
    return f"<div class='car'>{imgs}</div>"


def address_form(prefix: str, prefill: dict = None) -> dict:
    """State + district + PIN + address. Same widget everywhere (checkout and Create Customer ID)."""
    if prefill and not st.session_state.get(f"{prefix}_filled"):
        stt = sval(prefill.get("State"))
        if stt in STATES:
            st.session_state[f"{prefix}_state"] = stt
            dist = sval(prefill.get("District"))
            dk = f"{prefix}_dist_{safe_id(stt)}"
            if dist in DISTRICTS.get(stt, []):
                st.session_state[dk] = dist
            elif dist:
                st.session_state[dk] = "Other"
                st.session_state[f"{prefix}_dist_other"] = dist
        st.session_state[f"{prefix}_pin"] = sval(prefill.get("PIN Code")).replace(".0", "")
        st.session_state[f"{prefix}_addr"] = sval(prefill.get("Full Adress"))
        st.session_state[f"{prefix}_filled"] = True

    state = st.selectbox("State", STATES, index=None, placeholder="Select state", key=f"{prefix}_state")
    opts = (DISTRICTS.get(state, []) + ["Other"]) if state else []
    district = st.selectbox("District", opts, index=None, placeholder="Select district",
                            key=f"{prefix}_dist_{safe_id(state or 'none')}", disabled=not state)
    if district == "Other":
        district = st.text_input("Type your district", key=f"{prefix}_dist_other").strip()
    pin = st.text_input("PIN code", max_chars=6, key=f"{prefix}_pin")
    addr = st.text_area("House / street / landmark", key=f"{prefix}_addr")
    return {"State": state or "", "District": district or "", "PIN Code": pin.strip(), "Full Adress": addr.strip()}


def address_error(a: dict):
    if not a["State"]:
        return "Please select your state."
    if not a["District"]:
        return "Please select or type your district."
    if not (a["PIN Code"].isdigit() and len(a["PIN Code"]) == 6):
        return "Enter a valid 6-digit PIN code."
    if len(a["Full Adress"]) < 5:
        return "Please enter your full address."
    return None


def ring_picker(pid: str, colors: list, skey: str):
    """Coloured rings only (no names) with a selection animation."""
    sid = safe_id(pid)
    per = 6
    for r0 in range(0, len(colors), per):
        cols = st.columns(per)
        for j, _ in enumerate(colors[r0:r0 + per]):
            if cols[j].button(".", key=f"ring_{sid}_{r0 + j}"):
                st.session_state[skey] = colors[r0 + j][0]
    sel = st.session_state.get(skey)
    css = ""
    for i, (n, h) in enumerate(colors):
        on = n == sel
        css += (f".st-key-ring_{sid}_{i} .stButton > button {{width:34px !important; min-width:34px !important; "
                f"height:34px !important; min-height:34px !important; padding:0 !important; border-radius:50% !important; "
                f"background:{h} !important; border:2px solid #fff !important; "
                f"box-shadow:0 0 0 {3 if on else 2}px {'#FF5722' if on else '#cbd5e1'} !important; "
                f"transform:scale({1.18 if on else 1}); transition:all .2s ease; color:transparent !important;}} "
                f".st-key-ring_{sid}_{i} .stButton > button p {{font-size:0 !important;}} ")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    return sel


@st.dialog("Choose colour")
def colour_dialog(row):
    pid = str(row["Product ID"])
    skey = f"sel_{pid}"
    st.markdown(f"**{html.escape(sval(row['Title']))}**")
    ring_picker(pid, parse_colors(row.get("Colors")), skey)
    if st.button("Confirm", type="primary", key=f"conf_{safe_id(pid)}"):
        sel = st.session_state.get(skey)
        if not sel:
            st.error("Please pick a colour.")
        else:
            commit_add(row, sel, 1)
            st.session_state.pop(skey, None)
            st.rerun()


@st.dialog("Product details")
def product_dialog(row):
    pid = str(row["Product ID"])
    skey = f"sel_{pid}"
    colors = parse_colors(row.get("Colors"))
    st.markdown(carousel(images_of(row)), unsafe_allow_html=True)
    st.markdown(f"### {sval(row['Title'])}")
    st.markdown(f"**{fmt(to_price(row['Price']))}**")
    if bulk_text(row):
        st.markdown(f"<div class='bk'>{bulk_text(row)}</div>", unsafe_allow_html=True)
    if sval(row.get("Description")):
        st.write(sval(row["Description"]))
    if colors:
        st.caption("Choose a colour")
        ring_picker(pid, colors, skey)
    qty = st.number_input("Quantity", min_value=1, max_value=999, value=1, key=f"dq_{safe_id(pid)}")
    if st.button("Add to Cart", type="primary", key=f"dadd_{safe_id(pid)}"):
        sel = st.session_state.get(skey, "")
        if colors and not sel:
            st.error("Please choose a colour first.")
        else:
            commit_add(row, sel, int(qty))
            st.session_state.pop(skey, None)
            st.rerun()


def delivery_label(status) -> tuple:
    s = sval(status).lower()
    if s == "delivered":
        return "Delivered", "ok"
    if s == "in transit":
        return "In transit", ""
    if s == "cancelled":
        return "Cancelled", "bad"
    return "Not delivered", ""


def steps_html(status) -> str:
    idx = {"pending": 0, "confirmed": 1, "in transit": 2, "delivered": 3}.get(sval(status).lower(), 0)
    names = ["Placed", "Confirmed", "In transit", "Delivered"]
    return "<div class='steps'>" + "".join(
        f"<div class='{'on' if i <= idx else ''}'>{n}</div>" for i, n in enumerate(names)) + "</div>"


def norm_phone(v) -> str:
    return re.sub(r"\D", "", sval(v).replace(".0", ""))[-10:]


def wa_url(text: str, number: str = None) -> str:
    return f"https://wa.me/{number or WHATSAPP_NUMBER}?text=" + urllib.parse.quote(text)


def parse_full_address(full: str, pin: str = "") -> dict:
    """Orders store 'street, district, state' in one cell; split it back for pre-filling."""
    parts = [p.strip() for p in sval(full).split(",")]
    state = dist = ""
    if parts and parts[-1] in STATES:
        state = parts.pop()
        if parts:
            dist = parts.pop()
    return {"State": state, "District": dist, "PIN Code": sval(pin).replace(".0", ""),
            "Full Adress": ", ".join(p for p in parts if p)}


def customer_from_phone(phone: str):
    """Login by the phone number used when ordering (falls back to the optional customers sheet)."""
    odf = read_sheet("orders", ORDER_COLS)
    m = odf[odf["Phone Number"].apply(norm_phone) == phone]
    if not m.empty:
        last = m.iloc[-1]
        a = parse_full_address(last["Full Adress"], last["PIN Code"])
        return {"Customer ID": "", "Name": sval(last["Custumer Name"]), "Phone Number": phone, **a}
    try:
        cdf = read_sheet("customers", CUSTOMER_COLS, strict=True)
        h = cdf[cdf["Phone Number"].apply(norm_phone) == phone]
        if not h.empty:
            return {k: sval(v) for k, v in h.iloc[0].to_dict().items()}
    except Exception:
        pass
    return None


def order_message(order_id, ts, name, phone, addr, lines, total) -> str:
    out = [f"*New Order - {SHOP_NAME}*", f"Order ID: {order_id}", f"Date: {ts}", "",
           "*Customer details*", f"Name: {name}", f"Phone: {phone}", "",
           "*Delivery address*", f"House / street: {addr['Full Adress']}", f"District: {addr['District']}",
           f"State: {addr['State']}", f"PIN code: {addr['PIN Code']}", "", "*Items*"]
    for n, ln in enumerate(lines, 1):
        label = sval(ln["row"]["Title"]) + (f" ({ln['color']})" if ln["color"] else "")
        note = "  [bulk discount applied]" if ln["bulk"] else ""
        out.append(f"{n}. {label} - {ln['qty']} x {fmt(ln['unit'])} = {fmt(ln['unit'] * ln['qty'])}{note}")
    out += ["", f"*Total: {fmt(total)}*", "", "Please confirm my order and delivery."]
    return "\n".join(out)


def cart_enquiry_message(lines, total) -> str:
    out = [f"Hello {SHOP_NAME}, I would like to enquire about these items:", ""]
    for n, ln in enumerate(lines, 1):
        label = sval(ln["row"]["Title"]) + (f" ({ln['color']})" if ln["color"] else "")
        out.append(f"{n}. {label} - {ln['qty']} x {fmt(ln['unit'])}")
    out += ["", f"Total: {fmt(total)}", "", "Is this available?"]
    return "\n".join(out)


def chat_message(cust=None, last_order: str = "") -> str:
    out = [f"Hello {SHOP_NAME}, I need help."]
    if cust:
        out += ["", f"Name: {cust.get('Name', '')}", f"Phone: {norm_phone(cust.get('Phone Number'))}"]
        if last_order:
            out.append(f"Order ID: {last_order}")
    else:
        out += ["", "Name:", "Phone:", "Order ID (if any):"]
    out += ["", "My question: "]
    return "\n".join(out)


# =====================================================================
# ADMIN DASHBOARD
# =====================================================================
def order_total(txt: str) -> float:
    m = re.search(r"Total:\s*Rs\.?\s*([\d,\.]+)", sval(txt))
    try:
        return float(m.group(1).replace(",", "")) if m else 0.0
    except Exception:
        return 0.0


def admin_login_form(prefix: str):
    with st.form(f"admin_login_{prefix}"):
        user = st.text_input("Admin username", key=f"{prefix}_user")
        pw = st.text_input("Admin password", type="password", key=f"{prefix}_pw")
        if st.form_submit_button("Login as admin", type="primary"):
            if user.strip() == ADMIN_USERNAME and pw == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.session_state.admin_mode = True
                st.rerun()
            else:
                st.error("Incorrect username or password")


def admin_page():
    st.markdown(f"<div class='hdr'><div><div class='hi'>Admin</div><div class='nm'>{SHOP_NAME} Dashboard</div></div></div>",
                unsafe_allow_html=True)
    if not st.session_state.get("is_admin"):
        admin_login_form("adm")
        return

    tab_orders, tab_products = st.tabs(["Orders", "Manage Products"])

    # ---------------- Orders ----------------
    with tab_orders:
        if st.button("Refresh", key="ref_orders"):
            st.session_state.pop("admin_orders", None)
        if "admin_orders" not in st.session_state:
            st.session_state.admin_orders = read_sheet("orders", ORDER_COLS)
        odf = st.session_state.admin_orders.copy()
        if odf.empty:
            st.info("No orders yet.")
        else:
            odf["Status"] = odf["Status"].apply(lambda s: sval(s) or "Pending")
            revenue = sum(order_total(t) for t, s in zip(odf["Order Items & Total"], odf["Status"]) if s != "Cancelled")
            pending = int((odf["Status"] == "Pending").sum())
            st.markdown(f"""
            <div class='kpis'>
              <div class='kpi'><div class='l'>Orders</div><div class='v'>{len(odf)}</div></div>
              <div class='kpi hot'><div class='l'>Pending</div><div class='v'>{pending}</div></div>
              <div class='kpi'><div class='l'>Delivered</div><div class='v'>{int((odf['Status'] == 'Delivered').sum())}</div></div>
              <div class='kpi'><div class='l'>Revenue</div><div class='v'>{fmt(revenue)}</div></div>
            </div>""", unsafe_allow_html=True)
            days = pd.to_datetime(odf["TimeStamp"], errors="coerce").dt.date.dropna()
            if len(days):
                st.caption("Orders per day")
                st.bar_chart(days.value_counts().sort_index(), color="#FF5722", height=140)
            st.markdown("**All orders**")
            flt = st.selectbox("Show", ["All"] + STATUS_OPTIONS, key="ord_filter", label_visibility="collapsed")
            shown = odf if flt == "All" else odf[odf["Status"] == flt]
            for _, o in shown.iloc[::-1].iterrows():
                oid, nm_, ph_ = sval(o["Order ID"]), sval(o["Custumer Name"]), norm_phone(o["Phone Number"])
                with st.expander(f"{oid}  |  {nm_}  |  {o['Status']}"):
                    st.markdown(
                        f"**Customer:** {nm_}  \n**Phone:** {ph_}  \n**Placed:** {sval(o['TimeStamp'])}  \n"
                        f"**PIN:** {sval(o['PIN Code']).replace('.0', '')}  \n**Address:** {sval(o['Full Adress'])}  \n"
                        f"**Items & total:** {sval(o['Order Items & Total'])}  \n**Status:** {o['Status']}")
                    if len(ph_) == 10:
                        st.link_button("Message customer on WhatsApp", wa_url(
                            f"Hello {nm_}, your order {oid} from {SHOP_NAME} is now: {o['Status']}.", "91" + ph_))
            st.markdown("**Update order status**")
            view = odf.iloc[::-1].reset_index(drop=True)
            edited = st.data_editor(
                view, hide_index=True, use_container_width=True, key="orders_editor",
                disabled=[c for c in ORDER_COLS if c != "Status"],
                column_config={"Status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS, required=True)},
            )
            if st.button("Save status changes", type="primary"):
                try:
                    new = edited.iloc[::-1].reset_index(drop=True)[ORDER_COLS]
                    write_sheet("orders", new)
                    st.session_state.admin_orders = new
                    st.success("Orders updated")
                except Exception:
                    st.error("Could not save. Check the sheet is shared with the service account.")

    # ---------------- Products ----------------
    with tab_products:
        st.markdown("**Add new product**")
        if "adm_colors" not in st.session_state:
            st.session_state.adm_colors = []
        st.caption("Colours (optional): pick a colour, name it, then add")
        c1, c2, c3 = st.columns([1, 2, 1])
        hexv = c1.color_picker("Colour", "#FF5722", key="cp_hex", label_visibility="collapsed")
        cname = c2.text_input("Colour name", placeholder="Colour name", key="cp_name", label_visibility="collapsed")
        if c3.button("Add", key="cp_add"):
            nm = clean_name(cname)
            if nm:
                st.session_state.adm_colors.append((nm, hexv))
            else:
                st.warning("Give the colour a name.")
        if st.session_state.adm_colors:
            st.markdown("".join(f"<span class='chip'><i style='background:{h}'></i>{html.escape(n)}</span>"
                                for n, h in st.session_state.adm_colors), unsafe_allow_html=True)
            if st.button("Clear colours", key="cp_clear"):
                st.session_state.adm_colors = []
                st.rerun()

        if "up_n" not in st.session_state:
            st.session_state.up_n = 0
        if st.session_state.get("flash"):
            st.success(st.session_state.pop("flash"))
        files = st.file_uploader("Product images (up to 3)", type=["png", "jpg", "jpeg", "webp"],
                                 accept_multiple_files=True, key=f"up_{st.session_state.up_n}")
        if files:
            pc = st.columns(3)
            for i, f in enumerate(files[:3]):
                pc[i].image(f, use_container_width=True)
            if len(files) > 3:
                st.caption("Only the first 3 images are used.")
        with st.form("add_product", clear_on_submit=True):
            title = st.text_input("Title")
            price = st.number_input("Price", min_value=0.0, step=1.0)
            desc = st.text_area("Description")
            keywords = st.text_input("Search keywords (comma separated)")
            b1, b2 = st.columns(2)
            bulk_q = b1.number_input("Bulk discount: minimum pieces", min_value=0, step=1, value=0)
            bulk_d = b2.number_input("Bulk discount %", min_value=0.0, max_value=90.0, step=1.0, value=0.0)
            urls = st.text_input("...or image URL (optional, used if no image is uploaded)")
            if st.form_submit_button("Upload product", type="primary"):
                if not title.strip():
                    st.error("Title is required")
                else:
                    try:
                        imgs = [process_upload(f) for f in (files or [])[:3]]
                        if not imgs and urls.strip():
                            imgs = [urls.strip()]
                        imgs += [""] * (3 - len(imgs))
                        pdf = read_sheet("products", PRODUCT_COLS, strict=True)
                        row = {"Products": len(pdf) + 1, "Product ID": f"P{int(time.time())}",
                               "Title": title.strip(), "Price": price, "Description": desc.strip(),
                               "Image 1": imgs[0], "Image 2": imgs[1], "Image 3": imgs[2], "Active": "Yes",
                               "Colors": pack_colors(st.session_state.adm_colors), "Keywords": keywords.strip(),
                               "Bulk Qty": int(bulk_q), "Bulk Disc %": float(bulk_d)}
                        pdf = pd.concat([pdf, pd.DataFrame([row])], ignore_index=True)
                        write_sheet("products", pdf[PRODUCT_COLS])
                        st.session_state.adm_colors = []
                        st.session_state.pop("products_df", None)
                        st.session_state.pop("admin_products", None)
                        st.session_state.up_n += 1
                        st.session_state.flash = "Product added"
                        st.rerun()
                    except Exception:
                        st.error("Could not save the product. Check the sheet connection.")

        st.divider()
        st.markdown("**Manage products**")
        if "admin_products" not in st.session_state:
            st.session_state.admin_products = read_sheet("products", PRODUCT_COLS)
        pdf = st.session_state.admin_products.copy()
        if pdf.empty:
            st.info("No products yet.")
        else:
            view = pdf[["Product ID", "Title", "Price", "Description", "Colors", "Keywords", "Bulk Qty", "Bulk Disc %"]].copy()
            for c in ("Colors", "Keywords", "Description"):
                view[c] = view[c].apply(sval)
            view["Bulk Qty"] = view["Bulk Qty"].apply(to_int)
            view["Bulk Disc %"] = view["Bulk Disc %"].apply(to_price)
            view["Active"] = pdf["Active"].apply(is_active)
            view["Delete"] = False
            st.caption("Colours format:  Red:#ff0000|Blue:#0000ff")
            edited = st.data_editor(
                view, hide_index=True, use_container_width=True, key="products_editor", disabled=["Product ID"],
                column_config={"Price": st.column_config.NumberColumn("Price", min_value=0.0),
                               "Bulk Qty": st.column_config.NumberColumn("Bulk Qty", min_value=0, step=1),
                               "Bulk Disc %": st.column_config.NumberColumn("Bulk Disc %", min_value=0.0, max_value=90.0),
                               "Active": st.column_config.CheckboxColumn("Active"),
                               "Delete": st.column_config.CheckboxColumn("Delete")})
            if st.button("Save product changes", type="primary"):
                try:
                    out = pdf.copy()
                    for i in range(len(out)):
                        for c in ("Title", "Price", "Description", "Keywords", "Bulk Qty", "Bulk Disc %"):
                            out.loc[i, c] = edited.loc[i, c]
                        out.loc[i, "Colors"] = pack_colors(parse_colors(edited.loc[i, "Colors"]))
                        out.loc[i, "Active"] = "Yes" if edited.loc[i, "Active"] else "No"
                    keep = ~edited["Delete"].fillna(False).values
                    out = out[keep].reset_index(drop=True)
                    out["Products"] = range(1, len(out) + 1)
                    write_sheet("products", out[PRODUCT_COLS])
                    st.session_state.admin_products = out[PRODUCT_COLS]
                    st.session_state.pop("products_df", None)
                    st.success("Products updated")
                except Exception:
                    st.error("Could not save. Check the sheet connection.")

        if not pdf.empty:
            with st.expander("Current products and images"):
                for _, r in pdf.iterrows():
                    ic, tc = st.columns([1, 3])
                    ic.image(images_of(r)[0], use_container_width=True)
                    tc.markdown(f"**{sval(r['Title'])}**  \n{fmt(to_price(r['Price']))}  \n"
                                f"{'Active' if is_active(r['Active']) else 'Hidden'}")
            with st.expander("Replace product images"):
                labels = {f"{sval(r['Title'])} ({r['Product ID']})": r["Product ID"] for _, r in pdf.iterrows()}
                sel = st.selectbox("Product", list(labels.keys()), key="repl_sel")
                newf = st.file_uploader("New images (up to 3)", type=["png", "jpg", "jpeg", "webp"],
                                        accept_multiple_files=True, key="repl_imgs")
                if st.button("Replace images", key="repl_btn") and newf:
                    try:
                        full = read_sheet("products", PRODUCT_COLS, strict=True)
                        imgs = [process_upload(f) for f in newf[:3]]
                        imgs += [""] * (3 - len(imgs))
                        idx = full.index[full["Product ID"].astype(str) == str(labels[sel])][0]
                        full.loc[idx, ["Image 1", "Image 2", "Image 3"]] = imgs
                        write_sheet("products", full[PRODUCT_COLS])
                        st.session_state.admin_products = full[PRODUCT_COLS]
                        st.session_state.pop("products_df", None)
                        st.success("Images replaced")
                    except Exception:
                        st.error("Could not replace the images. Check the sheet connection.")

    st.write("")
    if st.button("Logout"):
        st.session_state.is_admin = False
        st.session_state.admin_mode = False
        st.rerun()


# =====================================================================
# CUSTOMER PAGES
# =====================================================================
def search_options(df) -> list:
    s = set()
    for _, r in df.iterrows():
        if sval(r["Title"]):
            s.add(sval(r["Title"]))
        for k in sval(r.get("Keywords")).split(","):
            if k.strip():
                s.add(k.strip())
    return sorted(s, key=str.lower)


def home_page():
    products = load_products()
    products = products[products["Active"].apply(is_active)].reset_index(drop=True)

    st.markdown(f"""
    <div class='hdr'>
      <div><div class='hi'>Welcome to</div><div class='nm'>{html.escape(SHOP_NAME)}</div></div>
      <div class='badge'>🛒</div>
    </div>""", unsafe_allow_html=True)

    with st.container(key="searchbox"):
        try:
            q = st.selectbox("Search", search_options(products), index=None, accept_new_options=True,
                             placeholder="Search products", label_visibility="collapsed", key="search_q")
        except TypeError:  # older Streamlit without accept_new_options
            q = st.text_input("Search", placeholder="Search products", label_visibility="collapsed", key="search_q")
    q = (q or "").strip()

    st.markdown("""
    <div class='banner'>
      <div class='t'>Special Discount</div>
      <div class='s'>50% OFF</div>
      <div style='font-size:12px; opacity:0.9; margin-top:4px;'>On all seasonal collection items!</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("<div class='sec'><span class='a'>Popular Products</span></div>", unsafe_allow_html=True)

    if q:
        toks = q.lower().split()
        hay = (products["Title"].apply(sval) + " " + products["Description"].apply(sval) + " " +
               products["Keywords"].apply(sval) + " " +
               products["Colors"].apply(lambda s: " ".join(n for n, _ in parse_colors(s)))).str.lower()
        mask = hay.apply(lambda h: all(t in h for t in toks))
        products = products[mask].reset_index(drop=True)

    if products.empty:
        st.info("No products found." if q else "No products available right now.")
        fx([])
        return

    products = products.iloc[::-1].reset_index(drop=True)
    for i in range(0, len(products), 2):
        cols = st.columns(2)
        for col, j in zip(cols, (i, i + 1)):
            if j >= len(products):
                continue
            row = products.loc[j]
            pid = str(row["Product ID"])
            colors = parse_colors(row.get("Colors"))
            dots = "".join(f"<span style='background:{h}'></span>" for _, h in colors[:6])
            with col:
                st.markdown(f"""
                <div class='pc'>
                  {carousel(images_of(row))}
                  <div class='pt'>{html.escape(sval(row['Title']))}</div>
                  <div class='pp'>{fmt(to_price(row['Price']))}</div>
                  <div class='bk'>{html.escape(bulk_text(row)) or '&nbsp;'}</div>
                  <div class='dots'>{dots}</div>
                </div>""", unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                if b1.button("View", key=f"v_{safe_id(pid)}"):
                    product_dialog(row)
                if b2.button("Add", key=f"a_{safe_id(pid)}", type="primary"):
                    if colors:
                        colour_dialog(row)
                    else:
                        commit_add(row, "", 1)
                        st.rerun()
    fx(search_options(products)[:12])


def cart_lines(prod_idx):
    cart = st.session_state.cart
    per_pid = {}
    for key, qty in cart.items():
        per_pid[key.split("|")[0]] = per_pid.get(key.split("|")[0], 0) + qty
    lines, subtotal = [], 0.0
    for key, qty in list(cart.items()):
        pid, _, color = key.partition("|")
        if pid not in prod_idx.index:
            cart.pop(key, None)
            continue
        row = prod_idx.loc[pid]
        unit, bulk = unit_price(row, per_pid.get(pid, qty))
        subtotal += unit * qty
        lines.append({"key": key, "row": row, "color": color, "qty": qty, "unit": unit, "bulk": bulk})
    return lines, subtotal


def cart_page():
    st.markdown("<div class='hdr'><div class='nm'>My Cart</div></div>", unsafe_allow_html=True)

    if st.session_state.last_order:
        o = st.session_state.last_order
        st.markdown(TRUCK_SVG, unsafe_allow_html=True)
        st.success(f"Order {o['id']} placed successfully.")
        st.info("Tap the button to send your order, details and delivery address to the shop on WhatsApp.")
        st.link_button("Send order details on WhatsApp", o["wa"], type="primary")
        with st.expander("Preview message"):
            st.text(o.get("msg", ""))
        if st.button("Done"):
            st.session_state.last_order = None
            st.rerun()
        return

    cart = st.session_state.cart
    if not cart:
        st.session_state.checkout = False
        st.info("Your cart is empty.")
        footer()
        return

    pdf = load_products()
    prod_idx = pdf.set_index(pdf["Product ID"].astype(str))
    lines, subtotal = cart_lines(prod_idx)
    if not lines:
        st.info("Your cart is empty.")
        return

    for n, ln in enumerate(lines):
        row = ln["row"]
        sub = f"<div class='cs'>Colour: {html.escape(ln['color'])}</div>" if ln["color"] else ""
        sub += "<div class='cs'>Bulk discount applied</div>" if ln["bulk"] else ""
        left, right = st.columns([3, 2])
        left.markdown(f"""
        <div class='cartrow'><img src="{html.escape(images_of(row)[0], quote=True)}">
        <div><div class='ct'>{html.escape(sval(row['Title']))}</div>{sub}
        <div class='cp'>{fmt(ln['unit'])}</div></div></div>""", unsafe_allow_html=True)
        with right:
            m, q, p = st.columns(3)
            if m.button("-", key=f"m_{n}"):
                if ln["qty"] <= 1:
                    cart.pop(ln["key"], None)
                else:
                    cart[ln["key"]] = ln["qty"] - 1
                st.rerun()
            q.markdown(f"<div style='text-align:center;font-weight:800;padding-top:.45rem'>{ln['qty']}</div>",
                       unsafe_allow_html=True)
            if p.button("+", key=f"p_{n}"):
                cart[ln["key"]] = ln["qty"] + 1
                st.rerun()

    st.markdown(f"""
    <div class='sumbox'>
      <div class='r'><span>Items</span><span>{cart_count()}</span></div>
      <div class='r tot'><span>Total</span><span>{fmt(subtotal)}</span></div>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.checkout:
        st.link_button("Ask about these items on WhatsApp", wa_url(cart_enquiry_message(lines, subtotal)))
        if st.button("Proceed to checkout", type="primary"):
            st.session_state.checkout = True
            st.rerun()
        footer()
        return

    st.markdown("**Delivery details**")
    cust = st.session_state.customer
    if cust and "co_name" not in st.session_state:
        st.session_state["co_name"] = cust.get("Name", "")
    if cust and "co_phone" not in st.session_state:
        st.session_state["co_phone"] = norm_phone(cust.get("Phone Number"))
    name = st.text_input("Full name", key="co_name")
    phone = st.text_input("Phone number", max_chars=10, key="co_phone")
    addr = address_form("co", cust)

    b1, b2 = st.columns(2)
    if b1.button("Back to cart"):
        st.session_state.checkout = False
        st.rerun()
    if b2.button("Place order", type="primary"):
        err = None
        if not name.strip():
            err = "Please enter your name."
        elif not (phone.isdigit() and len(phone) == 10):
            err = "Enter a valid 10-digit phone number."
        else:
            err = address_error(addr)
        if err:
            st.error(err)
        else:
            try:
                # fetch fresh product data for the final decision
                fresh = load_products(force=True)
                fidx = fresh.set_index(fresh["Product ID"].astype(str))
                flines, total = cart_lines(fidx)
                parts = []
                for ln in flines:
                    label = sval(ln["row"]["Title"]) + (f" ({ln['color']})" if ln["color"] else "")
                    parts.append(f"{label} x{ln['qty']} @ {fmt(ln['unit'])} = {fmt(ln['unit'] * ln['qty'])}")
                items_txt = "; ".join(parts) + f" | Total: {fmt(total)}"
                full_addr = f"{addr['Full Adress']}, {addr['District']}, {addr['State']}"
                order_id = "CS" + datetime.now().strftime("%y%m%d%H%M%S")
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                odf = read_sheet("orders", ORDER_COLS, strict=True)
                new = pd.DataFrame([{"Order ID": order_id, "TimeStamp": ts, "Custumer Name": name.strip(),
                                     "Phone Number": phone, "PIN Code": addr["PIN Code"], "Full Adress": full_addr,
                                     "Order Items & Total": items_txt, "Status": "Pending"}])
                write_sheet("orders", pd.concat([odf, new], ignore_index=True)[ORDER_COLS])
                msg = order_message(order_id, ts, name.strip(), phone, addr, flines, total)
                st.session_state.last_order = {"id": order_id, "wa": wa_url(msg), "msg": msg}
                if not st.session_state.customer:
                    st.session_state.customer = {"Customer ID": "", "Name": name.strip(), "Phone Number": phone, **addr}
                st.session_state.cart = {}
                st.session_state.checkout = False
                st.rerun()
            except Exception:
                st.error("Could not place the order right now. Please try again, or contact us on WhatsApp.")
    footer()


def new_customer_id(existing: list) -> str:
    while True:
        cid = "CS" + str(random.randint(10000, 99999))
        if cid not in existing:
            return cid


def profile_page():
    cust = st.session_state.customer
    last_oid = ""
    if cust:
        st.markdown(f"<div class='hdr'><div><div class='hi'>Signed in</div><div class='nm'>{html.escape(cust['Name'])}</div></div></div>",
                    unsafe_allow_html=True)
        cid_row = (f"<div class='r'><span>Customer ID</span><span><b>{html.escape(cust['Customer ID'])}</b></span></div>"
                   if cust.get("Customer ID") else "")
        st.markdown(f"<div class='sumbox'>{cid_row}"
                    f"<div class='r'><span>Phone</span><span>{html.escape(norm_phone(cust['Phone Number']))}</span></div></div>",
                    unsafe_allow_html=True)
        st.markdown("**Ordered items**")
        odf = read_sheet("orders", ORDER_COLS)
        mine = odf[odf["Phone Number"].apply(norm_phone) == norm_phone(cust["Phone Number"])]
        if mine.empty:
            st.info("No orders yet.")
        else:
            last_oid = sval(mine.iloc[-1]["Order ID"])
        for n, (_, o) in enumerate(mine.iloc[::-1].iterrows()):
            label, cls = delivery_label(o["Status"])
            st.markdown(f"""
            <div class='sumbox'><div class='r'><span><b>{html.escape(sval(o['Order ID']))}</b></span>
            <span class='ostat {cls}'>{label}</span></div>
            <div class='r'><span>{html.escape(sval(o['Order Items & Total']))}</span></div>
            <div class='r'><span>{html.escape(sval(o['TimeStamp']))}</span></div></div>""", unsafe_allow_html=True)
            with st.expander("Track order", icon=":material/local_shipping:"):
                st.markdown(steps_html(o["Status"]), unsafe_allow_html=True)
        if st.button("Log out"):
            st.session_state.customer = None
            for k in [k for k in st.session_state if k.startswith("co_")]:
                del st.session_state[k]
            st.rerun()
    else:
        st.markdown("<div class='hdr'><div><div class='hi'>Profile</div><div class='nm'>Welcome</div></div></div>",
                    unsafe_allow_html=True)
        t_login, t_admin = st.tabs(["Customer login", "Admin"])
        with t_login:
            st.caption("Log in with the phone number you used when ordering.")
            ph = st.text_input("Phone number", max_chars=10, key="lg_ph").strip()
            if st.button("Login", type="primary", key="lg_btn"):
                if not (ph.isdigit() and len(ph) == 10):
                    st.error("Enter a valid 10-digit phone number.")
                else:
                    found = customer_from_phone(ph)
                    if found:
                        st.session_state.customer = found
                        st.rerun()
                    else:
                        st.error("No orders found for this number yet. Place an order first, then log in.")
        with t_admin:
            admin_login_form("prof")

    st.markdown("**Need help?**")
    st.link_button("Chat on WhatsApp", wa_url(chat_message(cust, last_oid)), type="primary")
    with st.expander("Terms & Conditions"):
        for t in TERMS:
            st.markdown(f"- {t}")
    footer()


def bottom_nav():
    with st.container(key="bottomnav"):
        c1, c2, c3 = st.columns(3)
        items = [(c1, "Home", ":material/home:", "Home"),
                 (c2, "Cart", ":material/shopping_bag:", f"Cart ({cart_count()})" if cart_count() else "Cart"),
                 (c3, "Profile", ":material/person:", "Profile")]
        for col, key, icon, label in items:
            with col:
                active = st.session_state.tab == key
                if st.button(label, icon=icon, key=f"nav_{key}", type="primary" if active else "secondary"):
                    st.session_state.tab = key
                    st.rerun()


# --- ROUTER ---
if st.query_params.get("page") == ADMIN_PAGE_KEY or st.session_state.get("admin_mode"):
    admin_page()
else:
    tab = st.session_state.tab
    if tab == "Home":
        home_page()
        footer()
    elif tab == "Cart":
        cart_page()
        fx([])
    else:
        profile_page()
        fx([])
    sync_cart()
    bottom_nav()

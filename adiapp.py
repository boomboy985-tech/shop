import base64
import html
import io
import time
import urllib.parse
from datetime import datetime

import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURATION & CONSTANTS ---
SHOP_NAME = "Cartel Shop"
WHATSAPP_NUMBER = "918089523293"  # WhatsApp business number with country code
SUPPORT_EMAIL = ""  
ADMIN_PAGE_KEY = "rootcartel"  # Open admin dashboard via ?page=rootcartel
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "adithyan1234")
CURRENCY = "Rs."

ORDER_COLS = ["Order ID", "TimeStamp", "Custumer Name", "Phone Number",
              "PIN Code", "Full Adress", "Order Items & Total", "Status"]
PRODUCT_COLS = ["Products", "Product ID", "Title", "Price", "Description",
                "Image 1", "Image 2", "Image 3", "Active"]
STATUS_OPTIONS = ["Pending", "Confirmed", "In Transit", "Delivered", "Cancelled"]

st.set_page_config(page_title=SHOP_NAME, page_icon="🛒", layout="centered",
                   initial_sidebar_state="collapsed")

# --- STYLES ---
st.markdown("""
<style>
:root { --accent:#FF5722; --accent-dark:#E64A19; --ink:#111827; --muted:#6B7280; --bg:#F4F6F9; }
#MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {display:none !important;}
.stApp {background:var(--bg);}
.block-container {padding:0.8rem 1rem 7rem 1rem !important; max-width:520px;}
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
.pimg {width:100%; aspect-ratio:1/1; border-radius:14px; background:#EEF0F4; overflow:hidden;
  display:flex; align-items:center; justify-content:center;}
.pimg img {width:100%; height:100%; object-fit:cover;}
.pt {font-size:.88rem; font-weight:700; color:var(--ink); margin-top:.5rem; height:2.4em; overflow:hidden;
  line-height:1.2em;}
.pp {font-size:.95rem; font-weight:800; color:var(--accent-dark); margin:.15rem 0 .3rem 0;}

/* Buttons */
.stButton > button, .stDownloadButton > button, .stLinkButton > a, .stFormSubmitButton > button {
  border-radius:12px !important; font-weight:700 !important; border:1px solid #E5E7EB !important;
  background:#fff !important; color:var(--ink) !important; width:100%;}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"], .stLinkButton > a[kind="primary"] {
  background:var(--accent) !important; color:#fff !important; border:none !important;}
.stButton > button[kind="primary"]:hover {background:var(--accent-dark) !important;}

/* Search */
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
.cartrow .cp {font-weight:800; font-size:.9rem; color:var(--accent-dark);}
.sumbox {background:#fff; border-radius:16px; padding:.8rem 1rem; margin:.6rem 0;
  box-shadow:0 2px 10px rgba(0,0,0,.05);}
.sumbox .r {display:flex; justify-content:space-between; font-size:.9rem; color:var(--muted); padding:.15rem 0;}
.sumbox .tot {font-weight:800; color:var(--ink); font-size:1.05rem;}
.foot {text-align:center; color:var(--muted); font-size:.78rem; margin-top:1.5rem;}
.ostat {display:inline-block; padding:.1rem .6rem; border-radius:999px; font-size:.72rem; font-weight:700;
  background:#FFEDD5; color:var(--accent-dark);}
</style>
""", unsafe_allow_html=True)

# --- DATA LAYER ---
conn = st.connection("gsheets", type=GSheetsConnection)

PLACEHOLDER_IMG = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'>"
                   "<rect width='300' height='300' fill='%23EEF0F4'/></svg>")


def _clean(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols].dropna(how="all").reset_index(drop=True)
    return df


def read_sheet(name: str, cols: list) -> pd.DataFrame:
    try:
        df = conn.read(worksheet=name, ttl=0)
        df = _clean(df, cols)
        if df.empty and name == "products":
            default_df = pd.DataFrame([
                {"Products": 1, "Product ID": "P101", "Title": "Cartel Signature Tee", "Price": 499, "Description": "Premium cotton streetwear t-shirt.", "Image 1": "", "Image 2": "", "Image 3": "", "Active": "Yes"},
                {"Products": 2, "Product ID": "P102", "Title": "Tactical Utility Pouch", "Price": 699, "Description": "Durable multi-purpose gear pouch.", "Image 1": "", "Image 2": "", "Image 3": "", "Active": "Yes"},
                {"Products": 3, "Product ID": "P103", "Title": "Custom Engraved Dog Tag", "Price": 299, "Description": "Stainless steel personalized ID tag.", "Image 1": "", "Image 2": "", "Image 3": "", "Active": "Yes"}
            ])
            conn.update(worksheet="products", data=default_df)
            return default_df
        return df
    except Exception:
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
        return float(v)
    except Exception:
        return 0.0


def fmt(v: float) -> str:
    return f"{CURRENCY} {v:,.0f}" if float(v).is_integer() else f"{CURRENCY} {v:,.2f}"


def img_of(row, i=1) -> str:
    v = row.get(f"Image {i}")
    if v is None or (isinstance(v, float) and pd.isna(v)) or not str(v).strip():
        return ""
    return str(v).strip()


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


# --- STATE ---
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "tab" not in st.session_state:
    st.session_state.tab = "Home"
if "last_order" not in st.session_state:
    st.session_state.last_order = None


def cart_count() -> int:
    return sum(st.session_state.cart.values())


def add_to_cart(pid: str, qty: int = 1):
    st.session_state.cart[pid] = st.session_state.cart.get(pid, 0) + qty
    st.toast("Added to cart")


def footer():
    contact = f"WhatsApp: +{WHATSAPP_NUMBER}"
    if SUPPORT_EMAIL:
        contact += f" &nbsp;|&nbsp; {html.escape(SUPPORT_EMAIL)}"
    st.markdown(f"<div class='foot'>{SHOP_NAME} &nbsp;|&nbsp; {contact}</div>", unsafe_allow_html=True)


# =====================================================================
# ADMIN DASHBOARD
# =====================================================================
def admin_page():
    st.markdown(f"<div class='hdr'><div><div class='hi'>Admin</div><div class='nm'>{SHOP_NAME} Dashboard</div></div></div>",
                unsafe_allow_html=True)
    if not st.session_state.get("is_admin"):
        with st.form("admin_login"):
            pw = st.text_input("Admin password", type="password")
            if st.form_submit_button("Login", type="primary"):
                if pw == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Incorrect password")
        return

    tab_orders, tab_products = st.tabs(["Orders", "Manage Products"])

    # ---- Orders ----
    with tab_orders:
        if st.button("Refresh orders", key="ref_orders"):
            st.session_state.pop("admin_orders", None)
        if "admin_orders" not in st.session_state:
            st.session_state.admin_orders = read_sheet("orders", ORDER_COLS)
        odf = st.session_state.admin_orders.copy()
        if odf.empty:
            st.info("No orders yet.")
        else:
            odf = odf.iloc[::-1].reset_index(drop=True)
            odf["Status"] = odf["Status"].fillna("Pending")
            edited = st.data_editor(
                odf, hide_index=True, use_container_width=True, key="orders_editor",
                disabled=[c for c in ORDER_COLS if c != "Status"],
                column_config={"Status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS, required=True)},
            )
            if st.button("Save status changes", type="primary"):
                new = edited.iloc[::-1].reset_index(drop=True)
                write_sheet("orders", new[ORDER_COLS])
                st.session_state.admin_orders = new[ORDER_COLS]
                st.success("Orders updated")

    # ---- Products ----
    with tab_products:
        st.markdown("**Add new product**")
        with st.form("add_product", clear_on_submit=True):
            title = st.text_input("Title")
            price = st.number_input("Price", min_value=0.0, step=1.0)
            desc = st.text_area("Description")
            files = st.file_uploader("Images (up to 3)", type=["png", "jpg", "jpeg", "webp"],
                                     accept_multiple_files=True)
            urls = st.text_input("...or image URL (optional)")
            if st.form_submit_button("Upload product", type="primary"):
                if not title.strip():
                    st.error("Title is required")
                else:
                    imgs = [process_upload(f) for f in (files or [])[:3]]
                    if not imgs and urls.strip():
                        imgs = [urls.strip()]
                    imgs += [""] * (3 - len(imgs))
                    pdf = read_sheet("products", PRODUCT_COLS)
                    row = {"Products": len(pdf) + 1, "Product ID": f"P{int(time.time())}",
                           "Title": title.strip(), "Price": price, "Description": desc.strip(),
                           "Image 1": imgs[0], "Image 2": imgs[1], "Image 3": imgs[2], "Active": "Yes"}
                    pdf = pd.concat([pdf, pd.DataFrame([row])], ignore_index=True)
                    write_sheet("products", pdf)
                    st.session_state.pop("products_df", None)
                    st.session_state.pop("admin_products", None)
                    st.success("Product added")

        st.divider()
        st.markdown("**Manage products**")
        if "admin_products" not in st.session_state:
            st.session_state.admin_products = read_sheet("products", PRODUCT_COLS)
        pdf = st.session_state.admin_products.copy()
        if pdf.empty:
            st.info("No products yet.")
        else:
            view = pdf[["Product ID", "Title", "Price", "Description"]].copy()
            view["Active"] = pdf["Active"].apply(is_active)
            view["Delete"] = False
            edited = st.data_editor(
                view, hide_index=True, use_container_width=True, key="products_editor",
                disabled=["Product ID"],
                column_config={"Price": st.column_config.NumberColumn("Price", min_value=0.0),
                               "Active": st.column_config.CheckboxColumn("Active"),
                               "Delete": st.column_config.CheckboxColumn("Delete")},
            )
            if st.button("Save product changes", type="primary"):
                out = pdf.copy()
                for i in range(len(out)):
                    out.loc[i, "Title"] = edited.loc[i, "Title"]
                    out.loc[i, "Price"] = edited.loc[i, "Price"]
                    out.loc[i, "Description"] = edited.loc[i, "Description"]
                    out.loc[i, "Active"] = "Yes" if edited.loc[i, "Active"] else "No"
                keep = ~edited["Delete"].fillna(False).values
                out = out[keep].reset_index(drop=True)
                out["Products"] = range(1, len(out) + 1)
                write_sheet("products", out[PRODUCT_COLS])
                st.session_state.admin_products = out[PRODUCT_COLS]
                st.session_state.pop("products_df", None)
                st.success("Products updated")

    st.write("")
    if st.button("Logout"):
        st.session_state.is_admin = False
        st.rerun()


# =====================================================================
# CUSTOMER PAGES
# =====================================================================
@st.dialog("Product details")
def product_dialog(row):
    pid = str(row["Product ID"])
    imgs = [img_of(row, i) for i in (1, 2, 3) if img_of(row, i)]
    if imgs:
        cols = st.columns(len(imgs))
        for c, im in zip(cols, imgs):
            c.image(im, use_container_width=True)
    st.markdown(f"### {row['Title']}")
    st.markdown(f"**{fmt(to_price(row['Price']))}**")
    if str(row.get("Description") or "").strip() and str(row.get("Description")) != "nan":
        st.write(row["Description"])
    qty = st.number_input("Quantity", min_value=1, max_value=99, value=1, key=f"dq_{pid}")
    if st.button("Add to Cart", type="primary", key=f"dadd_{pid}"):
        add_to_cart(pid, int(qty))
        st.rerun()


def home_page():
    products = load_products()
    products = products[products["Active"].apply(is_active)].reset_index(drop=True)

    st.markdown(f"""
    <div class='hdr'>
      <div><div class='hi'>Welcome to</div><div class='nm'>{html.escape(SHOP_NAME)}</div></div>
      <div class='badge'>🛒</div>
    </div>""", unsafe_allow_html=True)

    q = st.text_input("Search", placeholder="Search products", label_visibility="collapsed", key="search_q")

    st.markdown("""
    <div class='banner'>
      <div class='t'>Special Discount</div>
      <div class='s'>50% OFF</div>
      <div style='font-size:12px; opacity:0.9; margin-top:4px;'>On all seasonal collection items!</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div class='sec'><span class='a'>Popular Products</span></div>", unsafe_allow_html=True)

    if q.strip():
        ql = q.strip().lower()
        mask = products["Title"].astype(str).str.lower().str.contains(ql, regex=False) | \
            products["Description"].astype(str).str.lower().str.contains(ql, regex=False)
        products = products[mask].reset_index(drop=True)

    if products.empty:
        st.info("No products available right now.")
        return

    products = products.iloc[::-1].reset_index(drop=True)
    for i in range(0, len(products), 2):
        cols = st.columns(2)
        for col, j in zip(cols, (i, i + 1)):
            if j >= len(products):
                continue
            row = products.loc[j]
            pid = str(row["Product ID"])
            src = img_of(row, 1) or PLACEHOLDER_IMG
            with col:
                st.markdown(f"""
                <div class='pc'>
                  <div class='pimg'><img src="{html.escape(src, quote=True)}"></div>
                  <div class='pt'>{html.escape(str(row['Title']))}</div>
                  <div class='pp'>{fmt(to_price(row['Price']))}</div>
                </div>""", unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                if b1.button("View", key=f"v_{pid}"):
                    product_dialog(row)
                if b2.button("Add", key=f"a_{pid}", type="primary"):
                    add_to_cart(pid)
                    st.rerun()


def cart_page():
    st.markdown("<div class='hdr'><div class='nm'>My Cart</div></div>", unsafe_allow_html=True)

    if st.session_state.last_order:
        o = st.session_state.last_order
        st.success(f"Order {o['id']} placed successfully.")
        st.link_button("Send order details on WhatsApp", o["wa"], type="primary")
        if st.button("Done"):
            st.session_state.last_order = None
            st.rerun()
        return

    cart = st.session_state.cart
    if not cart:
        st.info("Your cart is empty.")
        footer()
        return

    products = load_products().set_index(load_products()["Product ID"].astype(str))
    subtotal = 0.0
    for pid, qty in list(cart.items()):
        if pid not in products.index:
            cart.pop(pid, None)
            continue
        row = products.loc[pid]
        price = to_price(row["Price"])
        subtotal += price * qty
        src = img_of(row, 1) or PLACEHOLDER_IMG
        left, right = st.columns([3, 2])
        left.markdown(f"""
        <div class='cartrow'><img src="{html.escape(src, quote=True)}">
        <div><div class='ct'>{html.escape(str(row['Title']))}</div>
        <div class='cp'>{fmt(price)}</div></div></div>""", unsafe_allow_html=True)
        with right:
            m, n, p = st.columns(3)
            if m.button("-", key=f"m_{pid}"):
                if qty <= 1:
                    cart.pop(pid)
                else:
                    cart[pid] = qty - 1
                st.rerun()
            n.markdown(f"<div style='text-align:center;font-weight:800;padding-top:.45rem'>{qty}</div>",
                       unsafe_allow_html=True)
            if p.button("+", key=f"p_{pid}"):
                cart[pid] = qty + 1
                st.rerun()

    if not cart:
        st.rerun()

    st.markdown(f"""
    <div class='sumbox'>
      <div class='r'><span>Items</span><span>{cart_count()}</span></div>
      <div class='r tot'><span>Total</span><span>{fmt(subtotal)}</span></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("**Delivery details**")
    with st.form("checkout"):
        name = st.text_input("Full name")
        phone = st.text_input("Phone number", max_chars=10)
        pin = st.text_input("PIN code", max_chars=6)
        addr = st.text_area("Full address")
        submit = st.form_submit_button("Place order", type="primary")

    if submit:
        if not name.strip() or not addr.strip():
            st.error("Please enter your name and address.")
        elif not (phone.isdigit() and len(phone) == 10):
            st.error("Enter a valid 10-digit phone number.")
        elif not (pin.isdigit() and len(pin) == 6):
            st.error("Enter a valid 6-digit PIN code.")
        else:
            fresh = load_products(force=True)
            fresh = fresh.set_index(fresh["Product ID"].astype(str))
            lines, total = [], 0.0
            for pid, qty in cart.items():
                if pid in fresh.index:
                    r = fresh.loc[pid]
                    pr = to_price(r["Price"])
                    total += pr * qty
                    lines.append(f"{r['Title']} x{qty} = {fmt(pr * qty)}")
            items_txt = "; ".join(lines) + f" | Total: {fmt(total)}"
            order_id = "CS" + datetime.now().strftime("%y%m%d%H%M%S")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            odf = read_sheet("orders", ORDER_COLS)
            new = pd.DataFrame([{"Order ID": order_id, "TimeStamp": ts, "Custumer Name": name.strip(),
                                 "Phone Number": phone, "PIN Code": pin, "Full Adress": addr.strip(),
                                 "Order Items & Total": items_txt, "Status": "Pending"}])
            write_sheet("orders", pd.concat([odf, new], ignore_index=True))
            msg = (f"New order {order_id} - {SHOP_NAME}\nName: {name.strip()}\nPhone: {phone}\n"
                   f"PIN: {pin}\nAddress: {addr.strip()}\nItems: {items_txt}")
            wa = f"https://wa.me/{WHATSAPP_NUMBER}?text=" + urllib.parse.quote(msg)
            st.session_state.last_order = {"id": order_id, "wa": wa}
            st.session_state.cart = {}
            st.rerun()
    footer()


def profile_page():
    st.markdown("<div class='hdr'><div class='nm'>Profile</div></div>", unsafe_allow_html=True)
    st.markdown("**My orders**")
    phone = st.text_input("Enter your phone number", max_chars=10, key="prof_phone")
    if phone and phone.isdigit() and len(phone) == 10:
        odf = read_sheet("orders", ORDER_COLS)
        mine = odf[odf["Phone Number"].astype(str).str.replace(r"\.0$", "", regex=True) == phone]
        if mine.empty:
            st.info("No orders found for this number.")
        for _, o in mine.iloc[::-1].iterrows():
            status = o["Status"] if pd.notna(o["Status"]) else "Pending"
            st.markdown(f"""
            <div class='sumbox'><div class='r'><span><b>{html.escape(str(o['Order ID']))}</b></span>
            <span class='ostat'>{html.escape(str(status))}</span></div>
            <div class='r'><span>{html.escape(str(o['Order Items & Total']))}</span></div>
            <div class='r'><span>{html.escape(str(o['TimeStamp']))}</span></div></div>""",
                        unsafe_allow_html=True)
    st.markdown("**Need help?**")
    st.link_button("Chat on WhatsApp", f"https://wa.me/{WHATSAPP_NUMBER}", type="primary")
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
if st.query_params.get("page") == ADMIN_PAGE_KEY:
    admin_page()
else:
    tab = st.session_state.tab
    if tab == "Home":
        home_page()
        footer()
    elif tab == "Cart":
        cart_page()
    else:
        profile_page()
    bottom_nav()

import io
import time
import os
import re
import html as html_module
import random
import base64
import urllib.parse
from datetime import datetime, timezone, timedelta
import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image

# --- CONFIGURATION & CONSTANTS ---
WHATSAPP_NUMBER = "918089523293"  # Updated WhatsApp business number with country code
CONTACT_EMAIL = "boomboy985@gmail.com"  # Change to your support email

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.now(timezone.utc).astimezone(IST)

def ist_timestamp_str():
    return now_ist().strftime("%Y-%m-%d %H:%M:%S")

def esc(value):
    return html_module.escape(str(value if value is not None else ""), quote=True)

# Logo detection
LOGO_FILENAME = None
for filename in ["store-logo.png", "logo.png", "cadet.cart.logo.png"]:
    if os.path.exists(filename):
        LOGO_FILENAME = filename
        break

st.set_page_config(page_title="Express Store", page_icon="🛍️", layout="wide")

# --- GLOBAL STYLING ---
st.markdown("""
<style>
.stApp { background-color: #0d1117 !important; color: #c9d1d9 !important; }
.main-header {
    background: linear-gradient(135deg, #1f2937 0%, #111827 50%, #0f172a 100%);
    padding: 20px; border-radius: 16px; color: white; margin-bottom: 20px; border: 1px solid #374151;
}
.main-header h1 { color: #38bdf8 !important; font-size: 1.5rem !important; margin-bottom: 5px; }
.summary-card {
    background-color: #161b22 !important; padding: 20px; border-radius: 16px; border: 1px solid #30363d; margin-bottom: 15px;
}
.stButton > button {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important; color: white !important; font-weight: 700 !important;
    border-radius: 10px !important; border: none !important; min-height: 44px; width: 100%;
}
.contact-footer {
    margin-top: 40px; padding: 18px; background-color: #161b22; border-top: 1px solid #30363d; border-radius: 12px; text-align: center; color: #94a3b8;
}
</style>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS CONNECTION ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Could not connect to Google Sheets: {e}")
    st.stop()

ORDER_COLUMNS = ["Order ID", "Timestamp", "Customer Name", "Phone Number", "PIN Code", "Full Address", "Ordered Items & Total", "Status"]
PRODUCT_COLUMNS = ["Product ID", "Title", "Price", "Description", "Image 1", "Active"]

def get_orders_df():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        if df.empty or "Order ID" not in df.columns:
            return pd.DataFrame(columns=ORDER_COLUMNS)
        for col in ORDER_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        st.error(f"Error reading orders: {e}")
        return pd.DataFrame(columns=ORDER_COLUMNS)

def get_products_df():
    try:
        df = conn.read(worksheet="Products", ttl=0)
        if df.empty or "Product ID" not in df.columns:
            return pd.DataFrame(columns=PRODUCT_COLUMNS)
        for col in PRODUCT_COLUMNS:
            if col not in df.columns:
                df[col] = "YES" if col == "Active" else ""
        return df
    except Exception as e:
        return pd.DataFrame(columns=PRODUCT_COLUMNS)

def save_products_df(df):
    try:
        conn.update(worksheet="Products", data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Failed to save products: {e}")
        return False

def get_next_order_id():
    today_prefix = f"ORD{now_ist().strftime('%y%m%d')}"
    df = get_orders_df()
    if df.empty:
        return f"{today_prefix}001"
    today_orders = df[df["Order ID"].astype(str).str.startswith(today_prefix)]
    return f"{today_prefix}{(len(today_orders) + 1):03d}"

def get_next_product_id():
    df = get_products_df()
    existing_nums = set()
    if not df.empty:
        for pid in df["Product ID"].astype(str):
            m = re.match(r'^P(\d+)$', pid.strip())
            if m:
                existing_nums.add(int(m.group(1)))
    n = 1
    while n in existing_nums:
        n += 1
    return f"P{n:03d}"

def append_order(order_id, name, phone, pin, address, items_summary):
    df = get_orders_df()
    new_row = pd.DataFrame([{
        "Order ID": str(order_id),
        "Timestamp": ist_timestamp_str(),
        "Customer Name": name.upper().strip(),
        "Phone Number": str(phone).strip(),
        "PIN Code": str(pin).strip(),
        "Full Address": address.upper().replace("\n", ", ").strip(),
        "Ordered Items & Total": items_summary,
        "Status": "NEW"
    }])
    updated_df = pd.concat([df, new_row], ignore_index=True)
    conn.update(worksheet="Sheet1", data=updated_df)
    st.cache_data.clear()

# GitHub Image Upload Helpers
def github_upload_configured():
    return "github" in st.secrets and "token" in st.secrets["github"] and "repo" in st.secrets["github"]

def upload_image_to_github(file_bytes, filename):
    if not github_upload_configured():
        return False, "GitHub not configured."
    token = st.secrets["github"]["token"]
    repo = st.secrets["github"]["repo"]
    branch = st.secrets["github"].get("branch", "main")
    api_url = f"https://api.github.com/repos/{repo}/contents/{filename}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    try:
        existing_sha = None
        get_resp = requests.get(api_url, headers=headers, params={"ref": branch}, timeout=15)
        if get_resp.status_code == 200:
            existing_sha = get_resp.json().get("sha")
        payload = {"message": f"Upload product image: {filename}", "content": base64.b64encode(file_bytes).decode(), "branch": branch}
        if existing_sha:
            payload["sha"] = existing_sha
        put_resp = requests.put(api_url, headers=headers, json=payload, timeout=20)
        if put_resp.status_code in (200, 201):
            return True, "Success"
        return False, put_resp.text
    except Exception as e:
        return False, str(e)

def safe_image_filename(title, pid):
    base = re.sub(r'[^a-z0-9]+', '-', str(title).lower()).strip('-') or "product"
    return f"{base[:30]}-{pid.lower()}.jpg"

def resolve_image_path(filename):
    filename = str(filename or "").strip()
    if not filename: return None
    if os.path.exists(filename): return filename
    for folder in [".", "images", "product_images", "products"]:
        path = f"{folder}/{filename}"
        if os.path.exists(path): return path
    return None

# --- ROUTING & VIEW CONTROL ---
query_params = st.query_params
current_page = query_params.get("page", "shop")

if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

# --- ADMIN DASHBOARD ---
if current_page == "admin":
    if not st.session_state.admin_auth:
        st.markdown("<div class='summary-card'><h2>Admin Login</h2></div>", unsafe_allow_html=True)
        with st.form("admin_login"):
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if pw == "admin123":  # Change your default password here
                    st.session_state.admin_auth = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        if st.button("Back to Store"):
            st.query_params["page"] = "shop"
            st.rerun()
        st.stop()

    st.markdown("""
        <div class='main-header'>
            <h1>🛠️ Store Admin Dashboard</h1>
            <p>View customer orders & manage your product catalog easily.</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("Logout / Return to Store"):
        st.session_state.admin_auth = False
        st.query_params["page"] = "shop"
        st.rerun()

    tab_orders, tab_products = st.tabs(["📦 View Orders (Who Ordered & What)", "🛍️ Manage Products (Add / Edit / Delete)"])

    # TAB 1: VIEW ORDERS
    with tab_orders:
        st.subheader("Customer Orders")
        orders_df = get_orders_df()
        if orders_df.empty:
            st.info("No orders received yet.")
        else:
            st.dataframe(orders_df, use_container_width=True, hide_index=True)
            csv_bytes = orders_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Orders CSV", data=csv_bytes, file_name="orders_export.csv", mime="text/csv")

    # TAB 2: MANAGE PRODUCTS
    with tab_products:
        st.subheader("Add New Product")
        github_ready = github_upload_configured()
        
        with st.form("add_prod", clear_on_submit=True):
            p_title = st.text_input("Product Title *")
            p_price = st.text_input("Price (₹) *")
            p_desc = st.text_area("Description")
            p_image_file = st.file_uploader("Product Image *", type=["jpg", "jpeg", "png", "webp"])
            
            if st.form_submit_button("Add Product"):
                if not p_title or not p_price or not p_image_file:
                    st.error("Title, Price, and Image are required.")
                else:
                    new_pid = get_next_product_id()
                    img_bytes = p_image_file.getvalue()
                    img_name = safe_image_filename(p_title, new_pid)
                    
                    if github_ready:
                        ok, msg = upload_image_to_github(img_bytes, img_name)
                        if not ok:
                            st.error(f"Image upload failed: {msg}")
                            st.stop()
                    else:
                        with open(img_name, "wb") as f:
                            f.write(img_bytes)

                    products_df = get_products_df()
                    new_row = pd.DataFrame([{
                        "Product ID": new_pid,
                        "Title": p_title.strip(),
                        "Price": p_price.strip(),
                        "Description": p_desc.strip(),
                        "Image 1": img_name,
                        "Active": "YES"
                    }])
                    updated_prod = pd.concat([products_df, new_row], ignore_index=True)
                    if save_products_df(updated_prod):
                        st.success(f"Product '{p_title}' added successfully!")
                        time.sleep(1)
                        st.rerun()

        st.markdown("---")
        st.subheader("Existing Catalog")
        prod_df = get_products_df()
        if prod_df.empty:
            st.info("No products in catalog.")
        else:
            for _, row in prod_df.iterrows():
                pid = str(row["Product ID"])
                with st.expander(f"{row['Title']} - ₹{row['Price']} ({pid})"):
                    img_path = resolve_image_path(row["Image 1"])
                    if img_path:
                        st.image(img_path, width=120)
                    if st.button("Delete Product", key=f"del_{pid}"):
                        updated_prod = prod_df[prod_df["Product ID"] != pid]
                        save_products_df(updated_prod)
                        st.success("Product deleted.")
                        st.rerun()

# --- CUSTOMER SHOP & CART STOREFRONT ---
else:
    if "cart" not in st.session_state:
        st.session_state.cart = {}

    col_title, col_admin_link = st.columns([4, 1])
    with col_title:
        st.markdown("""
            <div class='main-header'>
                <h1>🛍️ Express Store</h1>
                <p>Browse products, add to cart, and place your order instantly via WhatsApp!</p>
            </div>
        """, unsafe_allow_html=True)
    with col_admin_link:
        if st.button("Admin Login"):
            st.query_params["page"] = "admin"
            st.rerun()

    products_df = get_products_df()
    active_products = products_df[products_df["Active"].astype(str).str.upper() != "NO"]

    if active_products.empty:
        st.info("No products available right now. Please check back soon.")
    else:
        st.subheader("Available Products")
        for _, prod in active_products.iterrows():
            pid = str(prod["Product ID"])
            p_title = str(prod["Title"])
            p_price = str(prod["Price"])
            p_desc = str(prod.get("Description", ""))
            
            with st.container(border=True):
                img_path = resolve_image_path(prod.get("Image 1", ""))
                if img_path:
                    st.image(img_path, width=200)
                st.markdown(f"### {esc(p_title)}")
                if p_desc:
                    st.caption(esc(p_desc))
                st.markdown(f"**Price: ₹{esc(p_price)}**")
                
                qty = st.number_input("Quantity", min_value=1, max_value=10, value=1, key=f"qty_{pid}")
                if st.button("Add to Cart", key=f"add_{pid}"):
                    st.session_state.cart[pid] = {"title": p_title, "price": p_price, "qty": qty}
                    st.toast(f"Added {qty} x {p_title} to cart!")

    st.markdown("---")
    st.subheader("🛒 Your Shopping Cart")
    
    if not st.session_state.get("cart"):
        st.caption("Your cart is empty.")
    else:
        cart_total = 0.0
        for pid, item in list(st.session_state.cart.items()):
            line_total = float(item["price"]) * int(item["qty"])
            cart_total += line_total
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(f"• {item['qty']} x {esc(item['title'])} — ₹{line_total:,.0f}")
            with c2:
                if st.button("Remove", key=f"rm_{pid}"):
                    st.session_state.cart.pop(pid, None)
                    st.rerun()
                    
        st.markdown(f"### Total Amount: ₹{cart_total:,.0f}")
        st.markdown("---")
        st.subheader("📦 Checkout & Place Order")
        
        with st.form("checkout_form"):
            co_name = st.text_input("Full Name *")
            co_phone = st.text_input("Phone Number (10 digits) *")
            co_address = st.text_area("Delivery Address *")
            co_pin = st.text_input("PIN Code (6 digits) *")
            submitted = st.form_submit_button("Place Order & Open WhatsApp")
            
            if submitted:
                if not co_name.strip() or not co_phone.strip() or not co_address.strip() or not co_pin.strip():
                    st.error("Please fill in all required customer details.")
                elif len(co_phone.strip()) != 10 or not co_phone.strip().isdigit():
                    st.error("Please enter a valid 10-digit phone number.")
                else:
                    order_id = get_next_order_id()
                    item_lines = [f"{item['qty']} x {item['title']} (₹{item['price']} each)" for item in st.session_state.cart.values()]
                    items_summary = "; ".join(item_lines) + f" | Total: ₹{cart_total:.0f}"
                    
                    append_order(order_id, co_name, co_phone, co_pin, co_address, items_summary)
                    
                    wa_text = f"Hello! I'd like to place an order:\n*Order ID:* {order_id}\n*Name:* {co_name.upper()}\n*Phone:* {co_phone}\n*Address:* {co_address.upper()} - {co_pin}\n\n*Items:*\n" + "\n".join([f"- {line}" for line in item_lines]) + f"\n*Total Amount:* ₹{cart_total:.0f}"
                    wa_url = f"https://api.whatsapp.com/send?phone={WHATSAPP_NUMBER}&text={urllib.parse.quote(wa_text)}"
                    
                    st.session_state.cart = {}
                    st.balloons()
                    st.success(f"Order saved! Order ID: **{order_id}**")
                    components.html(f'<script>window.location.href = "{wa_url}";</script>', height=0)
                    st.link_button("Click here if WhatsApp didn't open automatically", wa_url)

    st.markdown(f"""
        <div class="contact-footer">
            Need help? Contact Support<br/>
            Email: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> | WhatsApp: <a href="https://api.whatsapp.com/send?phone={WHATSAPP_NUMBER}" target="_blank">+{WHATSAPP_NUMBER}</a>
        </div>
    """, unsafe_allow_html=True)

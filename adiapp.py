import streamlit as st
import pandas as pd
from datetime import datetime
import json
import base64
import urllib.parse
import requests
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================
WHATSAPP_NUMBER = "918089523293"
ADMIN_SECRET = "adithyan1234"

st.set_page_config(
    page_title="Cartel Shop",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# UI Styling matching the modern e-commerce mobile app reference
UI_CSS = """
<style>
    /* Light theme app container background */
    .stApp {
        background-color: #f4f6f9;
        color: #1f2937;
    }
    
    /* Mobile Shell Frame for Desktop View */
    @media (min-width: 768px) {
        .main .block-container {
            max-width: 440px;
            margin: auto;
            padding-top: 1.5rem;
            padding-bottom: 6rem;
            background-color: #ffffff;
            border-radius: 30px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
            border: 1px solid #e5e7eb;
        }
    }
    
    /* Bottom Navigation Bar Styles */
    .nav-container {
        position: fixed;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 440px;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-top: 1px solid #e5e7eb;
        display: flex;
        justify-content: space-around;
        padding: 12px 0;
        z-index: 99999;
    }
    
    .nav-item {
        color: #9ca3af;
        text-align: center;
        text-decoration: none;
        font-size: 11px;
        font-weight: 600;
        transition: color 0.3s ease;
    }
    
    .nav-item:hover, .nav-item.active {
        color: #ff5722;
    }
    
    /* Product Card Styling */
    .product-card {
        background: #ffffff;
        border-radius: 20px;
        padding: 16px;
        border: 1px solid #f0f2f5;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
        margin-bottom: 16px;
        text-align: center;
    }
    
    /* Admin Banner */
    .admin-banner {
        background: linear-gradient(135deg, #ff5722, #ff7043);
        padding: 20px;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
</style>
"""
st.markdown(UI_CSS, unsafe_allow_html=True)

# ==========================================
# 2. SESSION STATE INITIALIZATION
# ==========================================
if "cart" not in st.session_state:
    st.session_state.cart = []
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# ==========================================
# 3. DATABASE & GITHUB HELPER FUNCTIONS
# ==========================================
@st.cache_resource
def get_db_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def load_products():
    try:
        conn = get_db_connection()
        df = conn.read(worksheet="products", ttl=5)
        if df is not None and not df.empty:
            if 'Active' in df.columns:
                df = df[df['Active'].astype(str).str.lower() == 'true']
            return df
    except Exception as e:
        st.warning(f"Could not load live inventory from Google Sheets: {e}")
    
    return pd.DataFrame([
        {"Product ID": 1, "Title": "Cartel Signature Tee", "Price": 499, "Description": "Premium cotton streetwear t-shirt.", "Image 1": ""},
        {"Product ID": 2, "Title": "Tactical Utility Pouch", "Price": 699, "Description": "Durable multi-purpose gear pouch.", "Image 1": ""},
        {"Product ID": 3, "Title": "Custom Engraved Dog Tag", "Price": 299, "Description": "Stainless steel personalized ID tag.", "Image 1": ""}
    ])

def save_order_to_sheet(order_data):
    try:
        conn = get_db_connection()
        df_orders = conn.read(worksheet="orders", ttl=0)
        new_row = pd.DataFrame([order_data])
        updated_df = pd.concat([df_orders, new_row], ignore_index=True)
        conn.update(worksheet="orders", data=updated_df)
        return True
    except Exception as e:
        st.error(f"Failed to save order to Google Sheets: {e}")
        return False

def add_product_to_sheet(prod_data):
    try:
        conn = get_db_connection()
        df_prods = conn.read(worksheet="products", ttl=0)
        new_row = pd.DataFrame([prod_data])
        updated_df = pd.concat([df_prods, new_row], ignore_index=True)
        conn.update(worksheet="products", data=updated_df)
        return True
    except Exception as e:
        st.error(f"Failed to add product to Google Sheets: {e}")
        return False

def upload_image_to_github(file_bytes, filename):
    try:
        github_cfg = st.secrets.get("github", {})
        GITHUB_TOKEN = github_cfg.get("token")
        REPO = github_cfg.get("repo")
        BRANCH = github_cfg.get("branch", "main")
        
        if not GITHUB_TOKEN or not REPO:
            st.error("GitHub credentials missing in secrets.")
            return None
            
        url = f"https://api.github.com/repos/{REPO}/contents/images/{filename}"
        encoded_content = base64.b64encode(file_bytes).decode("utf-8")
        
        payload = {
            "message": f"Upload product asset {filename} via Cartel Shop Admin",
            "content": encoded_content,
            "branch": BRANCH
        }
        
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        
        response = requests.put(url, json=payload, headers=headers)
        if response.status_code in [200, 201]:
            return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/images/{filename}"
        else:
            st.error(f"GitHub Upload Error: {response.json().get('message')}")
            return None
    except Exception as e:
        st.error(f"Error connecting to GitHub: {e}")
        return None

# ==========================================
# 4. NAVIGATION SHELL & ROUTING
# ==========================================
def render_nav_shell():
    nav_html = """
    <div class="nav-container">
        <a href="?tab=Home" class="nav-item">🏠<br>Home</a>
        <a href="?tab=Cart" class="nav-item">🛒<br>Cart</a>
        <a href="?tab=Profile" class="nav-item">👤<br>Profile</a>
        <a href="?tab=Admin" class="nav-item">⚙️<br>Admin</a>
    </div>
    """
    st.markdown(nav_html, unsafe_allow_html=True)

query_params = st.query_params
current_tab = query_params.get("tab", "Home")

# ==========================================
# 5. PAGE VIEWS
# ==========================================

if current_tab == "Home":
    # Top header bar matching reference design
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### 🛒 Cartel Shop")
        st.caption("Find your favorite items instantly")
    with col2:
        st.markdown("🔔")

    # Promo Banner Section
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e1b4b, #312e81); padding: 20px; border-radius: 20px; color: white; margin-bottom: 20px;">
        <h4 style="margin: 0; color: #ffffff;">Special Discount</h4>
        <h2 style="margin: 5px 0; color: #f97316;">50% OFF</h2>
        <p style="margin: 0; font-size: 12px; color: #cbd5e1;">On all seasonal collection items!</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Popular Products")
    
    df_products = load_products()
    
    # Display products in a clean 2-column grid layout matching the design reference
    for i in range(0, len(df_products), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(df_products):
                row = df_products.iloc[i + j]
                with cols[j]:
                    with st.container():
                        st.markdown('<div class="product-card">', unsafe_allow_html=True)
                        img_url = row.get("Image 1", "")
                        if pd.notna(img_url) and str(img_url).startswith("http"):
                            st.image(img_url, use_column_width=True)
                        else:
                            st.markdown("📦")
                        
                        title = row.get('Title', 'Product')
                        price = row.get('Price', 0)
                        
                        st.markdown(f"**{title}**")
                        st.markdown(f"<span style='color: #ff5722; font-weight: bold;'>₹{price}</span>", unsafe_allow_html=True)
                        
                        if st.button("Add", key=f"grid_add_{i+j}"):
                            item = {
                                "id": row.get('Product ID', i+j),
                                "name": title,
                                "price": float(price)
                            }
                            st.session_state.cart.append(item)
                            st.success(f"Added {title}!")
                        st.markdown('</div>', unsafe_allow_html=True)

elif current_tab == "Cart":
    st.markdown("## 🛒 My Cart")
    
    if not st.session_state.cart:
        st.info("Your cart is currently empty.")
    else:
        total = 0
        for i, item in enumerate(st.session_state.cart):
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{item['name']}** - ₹{item['price']}")
            if col2.button("❌", key=f"rem_{i}"):
                st.session_state.cart.pop(i)
                st.rerun()
            total += item['price']
            
        st.divider()
        st.markdown(f"### Total Amount: ₹{total}")
        
        with st.form("checkout_form"):
            st.markdown("### Delivery Details")
            c_name = st.text_input("Customer Name")
            c_phone = st.text_input("Phone Number")
            c_pin = st.text_input("PIN Code")
            c_address = st.text_area("Full Address")
            
            checkout_submitted = st.form_submit_button("Proceed to Checkout via WhatsApp", type="primary")
            if checkout_submitted:
                if not c_name or not c_phone or not c_address:
                    st.error("Please fill in your name, phone number, and address.")
                else:
                    items_str = ", ".join([f"{i['name']} (₹{i['price']})" for i in st.session_state.cart])
                    order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    order_record = {
                        "Order ID": order_id,
                        "TimeStamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Custumer Name": c_name,
                        "Phone Number": c_phone,
                        "PIN Code": c_pin,
                        "Full Adress": c_address,
                        "Order Items & Total": f"{items_str} | Total: ₹{total}",
                        "Status": "Pending"
                    }
                    
                    save_order_to_sheet(order_record)
                    
                    order_summary = f"Hello Cartel Shop, new order {order_id}:\n\nName: {c_name}\nPhone: {c_phone}\nAddress: {c_address}\n\nItems:\n{items_str}\nTotal: ₹{total}"
                    encoded_message = urllib.parse.quote(order_summary)
                    whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={encoded_message}"
                    
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={whatsapp_url}">', unsafe_allow_html=True)
                    st.success("Order logged and redirecting to WhatsApp...")

elif current_tab == "Profile":
    st.markdown("## 👤 User Profile")
    st.write("Manage your shipping addresses and account details.")
    
    with st.form("profile_form"):
        st.text_input("Full Name")
        st.text_input("Phone Number")
        st.text_area("Shipping Address")
        submitted = st.form_submit_button("Save Profile")
        if submitted:
            st.success("Profile details saved successfully!")

elif current_tab == "Admin":
    query_secret = query_params.get("secret", "")
    
    if query_secret == ADMIN_SECRET or st.session_state.get("admin_authenticated"):
        st.session_state.admin_authenticated = True
        
        st.markdown("""
        <div class="admin-banner">
            <h2>⚙️ Cartel Shop - Admin Dashboard</h2>
            <p>Manage customer orders and upload new products.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # --- SECTION 1: OLD ORDERS ---
        st.markdown("### 📦 Customer Orders")
        try:
            conn = get_db_connection()
            df_orders = conn.read(worksheet="orders", ttl=0)
            if df_orders is not None and not df_orders.empty:
                st.dataframe(df_orders, use_container_width=True)
            else:
                st.info("No orders found in the spreadsheet yet.")
        except Exception as e:
            st.warning(f"Could not load orders: {e}")
            
        st.divider()
        
        # --- SECTION 2: MANAGE & ADD PRODUCTS ---
        st.markdown("### ➕ Add New Product")
        with st.form("add_product_form"):
            p_id = st.text_input("Product ID (e.g. 104)")
            p_title = st.text_input("Product Title")
            p_price = st.number_input("Price (₹)", min_value=0.0, step=10.0)
            p_desc = st.text_area("Description")
            
            uploaded_file = st.file_uploader("Product Image", type=["jpg", "png", "jpeg"])
            
            prod_submitted = st.form_submit_button("Upload & Save Product")
            if prod_submitted:
                if not p_title or not p_id:
                    st.error("Please provide a Product ID and Title.")
                else:
                    image_url = ""
                    if uploaded_file:
                        bytes_data = uploaded_file.getvalue()
                        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
                        image_url = upload_image_to_github(bytes_data, filename)
                    
                    new_prod_record = {
                        "Products": p_title,
                        "Product ID": p_id,
                        "Title": p_title,
                        "Price": p_price,
                        "Description": p_desc,
                        "Image 1": image_url if image_url else "",
                        "Image 2": "",
                        "Image 3": "",
                        "Active": "TRUE"
                    }
                    
                    if add_product_to_sheet(new_prod_record):
                        st.success(f"Product '{p_title}' added successfully!")
                        st.rerun()
                        
        st.divider()
        if st.button("Lock / Logout Admin"):
            st.session_state.admin_authenticated = False
            st.query_params.clear()
            st.rerun()
            
    else:
        st.markdown("""
        <div class="admin-banner">
            <h2>Admin Portal</h2>
            <p>Enter the secure password to proceed.</p>
        </div>
        """, unsafe_allow_html=True)
        
        entered_secret = st.text_input("Admin Secret Password", type="password", key="admin_secret_input")
        if st.button("Access Dashboard"):
            if entered_secret == ADMIN_SECRET:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Invalid secret password.")

# Render persistent bottom navigation bar
render_nav_shell()

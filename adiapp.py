import streamlit as st
import pandas as pd
from datetime import datetime
import json
import base64
import urllib.parse
import requests
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. PAGE CONFIGURATION & MOBILE WIDTH
# ==========================================
st.set_page_config(
    page_title="Cartel Store",
    page_icon="shop",
    layout="centered",
    initial_sidebar_state="collapsed"
)

MOBILE_WIDTH_CSS = """
<style>
    .stApp {
        background-color: #0f1117;
        color: #f0f2f6;
    }
    
    @media (min-width: 768px) {
        .main .block-container {
            max-width: 480px;
            margin: auto;
            padding-top: 2rem;
            padding-bottom: 6rem;
            background-color: #161b22;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            border: 1px solid #30363d;
        }
    }
    
    .nav-container {
        position: fixed;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 480px;
        background: rgba(22, 27, 34, 0.95);
        backdrop-filter: blur(10px);
        border-top: 1px solid #30363d;
        display: flex;
        justify-content: space-around;
        padding: 12px 0;
        z-index: 99999;
    }
    
    .nav-item {
        color: #8b949e;
        text-align: center;
        text-decoration: none;
        font-size: 12px;
        font-weight: 500;
        transition: color 0.3s ease;
    }
    
    .nav-item:hover, .nav-item.active {
        color: #58a6ff;
    }
    
    .admin-banner {
        background: linear-gradient(135deg, #1f6feb, #58a6ff);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
</style>
"""
st.markdown(MOBILE_WIDTH_CSS, unsafe_allow_html=True)

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
        df = conn.read(worksheet="Products", ttl=5)
        if df is not None and not df.empty:
            return df
    except Exception as e:
        st.warning(f"Could not load live inventory from Google Sheets: {e}")
    
    # Fallback default products if sheet is empty/unconfigured
    return pd.DataFrame([
        {"id": 1, "name": "NCC Cadet Lanyard", "price": 150, "desc": "Standard regulation lanyard.", "image": ""},
        {"id": 2, "name": "Custom Name Badge", "price": 250, "desc": "Engraved acrylic identification badge.", "image": ""},
        {"id": 3, "name": "Beret Cap & Badge", "price": 350, "desc": "Woolen beret with metallic cap badge.", "image": ""}
    ])

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
            "message": f"Upload product asset {filename} via Cadet Cartel Admin",
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
        <a href="?tab=Shop" class="nav-item">🛍️<br>Shop</a>
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
    st.markdown("## 🛡️ Cadet Cartel")
    st.markdown("Your premier destination for high-quality uniform accessories, custom badges, and specialized tactical gear.")
    
    st.info("💡 Use the bottom navigation bar to explore the shop, review your cart, or manage your account.")
    
    st.markdown("""
    <div style="background: #21262d; padding: 20px; border-radius: 12px; border: 1px solid #30363d; margin-top: 15px;">
        <h3>Featured Collection</h3>
        <p>Custom NCC accessories and engraved identification cards built to rigorous specifications.</p>
    </div>
    """, unsafe_allow_html=True)

elif current_tab == "Shop":
    st.markdown("## 🛍️ Product Catalog")
    df_products = load_products()
    
    for idx, row in df_products.iterrows():
        with st.container():
            if "image" in row and pd.notna(row["image"]) and str(row["image"]).startswith("http"):
                st.image(row["image"], use_column_width=True)
            
            st.markdown(f"### {row.get('name', 'Product')}")
            st.write(row.get('desc', ''))
            st.write(f"**Price:** ₹{row.get('price', 0)}")
            
            if st.button(f"Add to Cart", key=f"add_{idx}"):
                item = {
                    "id": row.get('id', idx),
                    "name": row.get('name'),
                    "price": float(row.get('price', 0))
                }
                st.session_state.cart.append(item)
                st.success(f"Added {row.get('name')} to cart!")
            st.divider()

elif current_tab == "Cart":
    st.markdown("## 🛒 Your Shopping Cart")
    
    if not st.session_state.cart:
        st.info("Your cart is currently empty.")
    else:
        total = 0
        for i, item in enumerate(st.session_state.cart):
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{item['name']}** - ₹{item['price']}")
            if col2.button("Remove", key=f"rem_{i}"):
                st.session_state.cart.pop(i)
                st.rerun()
            total += item['price']
            
        st.divider()
        st.markdown(f"### Total Amount: ₹{total}")
        
        if st.button("Proceed to Checkout via WhatsApp", type="primary"):
            order_summary = "Hello Cadet Cartel, I would like to place an order:\n\n"
            for item in st.session_state.cart:
                order_summary += f"- {item['name']} (₹{item['price']})\n"
            order_summary += f"\nTotal: ₹{total}"
            
            encoded_message = urllib.parse.quote(order_summary)
            whatsapp_url = f"https://wa.me/?text={encoded_message}"
            st.markdown(f'<meta http-equiv="refresh" content="0;url={whatsapp_url}">', unsafe_allow_html=True)
            st.success("Redirecting to WhatsApp...")

elif current_tab == "Profile":
    st.markdown("## 👤 User Profile")
    st.write("Manage your shipping addresses and preferences.")
    
    with st.form("profile_form"):
        st.text_input("Full Name")
        st.text_input("Phone Number")
        st.text_area("Shipping Address")
        submitted = st.form_submit_button("Save Profile")
        if submitted:
            st.success("Profile details saved successfully!")

elif current_tab == "Admin":
    st.markdown(MOBILE_WIDTH_CSS, unsafe_allow_html=True)
    
    ADMIN_SECRET = "adithyan1234"
    query_secret = query_params.get("secret", "")
    
    if query_secret == ADMIN_SECRET or st.session_state.get("admin_authenticated"):
        st.session_state.admin_authenticated = True
        
        st.markdown("""
        <div class="admin-banner">
            <h2>⚙️ Admin Control Panel</h2>
            <p>Welcome back, Administrator.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Store Overview")
        col1, col2 = st.columns(2)
        col1.metric("Catalog Status", "Connected")
        col2.metric("GitHub Storage", "Active")
        
        st.markdown("### Upload New Product Image")
        uploaded_file = st.file_uploader("Choose an image", type=["jpg", "png", "jpeg"])
        if uploaded_file and st.button("Upload to GitHub Repository"):
            bytes_data = uploaded_file.getvalue()
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
            public_url = upload_image_to_github(bytes_data, filename)
            if public_url:
                st.success("Image uploaded successfully!")
                st.code(public_url)
                
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

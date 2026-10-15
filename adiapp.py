import streamlit as st
import pandas as pd
from datetime import datetime
import json
import base64
import urllib.parse

# ==========================================
# 1. PAGE CONFIGURATION & MOBILE WIDTH
# ==========================================
st.set_page_config(
    page_title="Cadet Cartel Store",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Apply mobile-width container wrapper and custom dark theme styling
MOBILE_WIDTH_CSS = """
<style>
    /* Main App Background & Font */
    .stApp {
        background-color: #0f1117;
        color: #f0f2f6;
    }
    
    /* Mobile Shell Wrapper */
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
    
    /* Bottom Navigation Bar Styles */
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
    
    /* Admin Banner */
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
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Home"

# ==========================================
# 3. NAVIGATION SHELL & ANIMATED BOTTOM BAR
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

# Parse query params for routing
query_params = st.query_params
current_tab = query_params.get("tab", "Home")

# ==========================================
# 4. VIEW ROUTERS
# ==========================================

if current_tab == "Home":
    st.markdown("## 🛡️ Cadet Cartel")
    st.markdown("Your one-stop destination for high-quality uniform accessories, custom badges, and tactical gear.")
    
    st.info("💡 Use the bottom navigation bar to browse products, check your cart, or access your profile.")
    
    # Featured Banner
    st.markdown("""
    <div style="background: #21262d; padding: 20px; border-radius: 12px; border: 1px solid #30363d; margin-top: 15px;">
        <h3>Featured Collection</h3>
        <p>Custom NCC accessories and engraved identification cards built to precise specifications.</p>
    </div>
    """, unsafe_allow_html=True)

elif current_tab == "Shop":
    st.markdown("## 🛍️ Product Catalog")
    
    # Sample Products Layout
    products = [
        {"id": 1, "name": "NCC Cadet Lanyard", "price": 150, "desc": "Standard regulation lanyard."},
        {"id": 2, "name": "Custom Name Badge", "price": 250, "desc": "Engraved acrylic identification badge."},
        {"id": 3, "name": "Beret Cap & Badge", "price": 350, "desc": "Woolen beret with metallic cap badge."}
    ]
    
    for p in products:
        with st.container():
            st.markdown(f"### {p['name']}")
            st.write(p['desc'])
            st.write(f"**Price:** ₹{p['price']}")
            if st.button(f"Add to Cart", key=f"add_{p['id']}"):
                st.session_state.cart.append(p)
                st.success(f"Added {p['name']} to cart!")
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
            
        st.divider(
        )
        st.markdown(f"### Total Amount: ₹{total}")
        
        if st.button("Proceed to Checkout via WhatsApp", type="primary"):
            # Format WhatsApp order text
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
    st.write("Manage your shipping addresses, view past orders, and configure preferences.")
    
    with st.form("profile_form"):
        st.text_input("Full Name")
        st.text_input("Phone Number")
        st.text_area("Shipping Address")
        submitted = st.form_submit_button("Save Profile")
        if submitted:
            st.success("Profile updated successfully!")

elif current_tab == "Admin":
    st.markdown(MOBILE_WIDTH_CSS, unsafe_allow_html=True)
    
    # Retrieve steamedy secret from Streamlit secrets, defaulting if missing
    STEAMEDY_ADMIN_SECRET = st.secrets.get("steamedy", {}).get("secret", "steamedy123")
    
    query_secret = query_params.get("secret", "")
    
    if query_secret == STEAMEDY_ADMIN_SECRET or st.session_state.get("admin_authenticated"):
        st.session_state.admin_authenticated = True
        
        st.markdown("""
        <div class="admin-banner">
            <h2>⚙️ Admin Control Panel</h2>
            <p>Welcome back, Administrator.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Store Statistics")
        col1, col2 = st.columns(2)
        col1.metric("Total Orders", "142")
        col2.metric("Revenue", "₹38,450")
        
        st.markdown("### Quick Actions")
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
        
        entered_secret = st.text_input("Admin Secret Password", type="password", key="steamedy_secret_input")
        if st.button("Access Dashboard"):
            if entered_secret == STEAMEDY_ADMIN_SECRET:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Invalid secret password.")

# Render persistent bottom navigation bar across pages
render_nav_shell()

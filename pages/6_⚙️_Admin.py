"""
login.py — Main login landing page
Place this in the root folder alongside app.py
"""

import streamlit as st

st.set_page_config(page_title="Grant Tracker Login", page_icon="🎯", layout="centered")

# Hide sidebar on login page
st.markdown("""
<style>
[data-testid="stSidebar"] {display: none;}
</style>
""", unsafe_allow_html=True)

# If already logged in, redirect to main app
if st.session_state.get("authenticated"):
    st.switch_page("app.py")

# Login UI
st.markdown("""
<div style='text-align: center; padding: 40px 0 20px 0;'>
    <h1>🎯 Grant Tracker</h1>
    <p style='color: gray;'>Sign in to access your grant management dashboard</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

    if submitted:
        if not username or not password:
            st.error("Please enter both username and password.")
        else:
            try:
                from db import get_db
                import hashlib
                db = get_db()
                if db is None:
                    st.error("Database connection failed. Check your secrets.toml")
                else:
                    password_hash = hashlib.sha256(password.encode()).hexdigest()
                    user = db["users"].find_one({
                        "username": username.lower().strip(),
                        "password_hash": password_hash
                    })
                    if user:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = user["username"]
                        st.session_state["role"] = user.get("role", "viewer")
                        st.switch_page("app.py")
                    else:
                        st.error("Incorrect username or password.")
            except Exception as e:
                st.error(f"Login error: {e}")

    st.markdown("")
    st.caption("Contact your administrator for access.")
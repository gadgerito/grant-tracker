"""
auth.py — Username + password login for the Grant Tracker app.
Passwords are hashed with bcrypt and stored in MongoDB.
"""

import streamlit as st
import hashlib
import os


def hash_password(password: str) -> str:
    """Simple SHA-256 hash (no bcrypt dependency needed)."""
    return hashlib.sha256(password.encode()).hexdigest()


def check_credentials(username: str, password: str, db) -> bool:
    """Check username/password against MongoDB users collection."""
    user = db["users"].find_one({"username": username.lower().strip()})
    if not user:
        return False
    return user["password_hash"] == hash_password(password)


def create_user(username: str, password: str, role: str, db):
    """Create a new user in MongoDB."""
    db["users"].insert_one({
        "username": username.lower().strip(),
        "password_hash": hash_password(password),
        "role": role,  # "admin" or "viewer"
    })


def login_screen():
    """Render the login UI. Returns True if logged in."""
    if st.session_state.get("authenticated"):
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🎯 Grant Tracker")
        st.markdown("### Sign in")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Sign in", type="primary", use_container_width=True):
            from db import get_db
            db = get_db()
            if db is None:
                st.error("Could not connect to database. Check your MONGODB_URI.")
                return False
            if check_credentials(username, password, db):
                user = db["users"].find_one({"username": username.lower().strip()})
                st.session_state["authenticated"] = True
                st.session_state["username"] = username.lower().strip()
                st.session_state["role"] = user.get("role", "viewer")
                st.rerun()
            else:
                st.error("Incorrect username or password.")
        st.caption("Contact your admin to get access.")
    return False


def logout():
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.rerun()


def require_login():
    """Call at the top of every page. Stops rendering if not logged in."""
    if not st.session_state.get("authenticated"):
        login_screen()
        st.stop()

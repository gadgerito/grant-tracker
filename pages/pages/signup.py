"""
pages/signup.py — Staff self-signup page
"""

import streamlit as st
import hashlib
import os

st.title("🎯 Grant Tracker — Create Account")
st.caption("Create your account to access the grant dashboard.")

# Don't show if already logged in
if st.session_state.get("authenticated"):
    st.success(f"You're already signed in as {st.session_state.get('username')}!")
    st.stop()

def get_db():
    try:
        from pymongo import MongoClient
        uri = os.environ.get("MONGODB_URI", "") or st.secrets.get("MONGODB_URI", "")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        return client["grant_tracker"]
    except Exception as e:
        st.error(f"DB error: {e}")
        return None

with st.form("signup_form"):
    st.subheader("Create your account")
    new_username = st.text_input("Choose a username *")
    new_password = st.text_input("Choose a password *", type="password")
    confirm_password = st.text_input("Confirm password *", type="password")
    
    # Optional invite code to prevent random signups
    invite_code = st.text_input("Invite code *", placeholder="Ask your admin for this code")
    
    submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)
    
    if submitted:
        # Validate
        if not new_username or not new_password or not confirm_password:
            st.error("All fields are required.")
        elif new_password != confirm_password:
            st.error("Passwords don't match.")
        elif len(new_password) < 6:
            st.error("Password must be at least 6 characters.")
        elif invite_code != st.secrets.get("INVITE_CODE", "grantteam2024"):
            st.error("Invalid invite code. Ask your administrator.")
        else:
            db = get_db()
            if db is None:
                st.stop()
            
            # Check if username already exists
            existing = db["users"].find_one({"username": new_username.lower().strip()})
            if existing:
                st.error(f"Username '{new_username}' is already taken.")
            else:
                db["users"].insert_one({
                    "username": new_username.lower().strip(),
                    "password_hash": hashlib.sha256(new_password.encode()).hexdigest(),
                    "role": "viewer",  # staff always get viewer role
                })
                st.success(f"✅ Account created! Go to the main page to sign in.")
                st.balloons()

st.markdown("---")
st.caption("Already have an account? Go to the main app page to sign in.")

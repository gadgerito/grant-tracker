import streamlit as st
import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username: str, password: str, db) -> bool:
    user = db["users"].find_one({"username": username.lower().strip()})
    if not user:
        return False
    return user["password_hash"] == hash_password(password)

def logout():
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.rerun()

def require_login():
    if not st.session_state.get("authenticated"):
        st.stop()
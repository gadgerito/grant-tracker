import os, hashlib
from pymongo import MongoClient

uri = os.environ.get("MONGODB_URI", "")
if not uri:
    try:
        import streamlit as st
        uri = st.secrets["MONGODB_URI"]
    except:
        pass

if not uri:
    print("ERROR: No MONGODB_URI found")
    exit(1)

client = MongoClient(uri)
db = client["grant_tracker"]

username = input("Enter username: ").strip().lower()
password = input("Enter password: ").strip()
role = input("Role (admin/viewer) [admin]: ").strip() or "admin"

db["users"].insert_one({
    "username": username,
    "password_hash": hashlib.sha256(password.encode()).hexdigest(),
    "role": role,
})
print(f"✅ User '{username}' created!")

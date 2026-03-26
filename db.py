"""
db.py — MongoDB Atlas connection and helper functions.
"""

import os
import pandas as pd

try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False


def get_db():
    import streamlit as st
    
    if not MONGO_AVAILABLE:
        st.error("pymongo not installed. Check requirements.txt")
        return None

    uri = os.environ.get("MONGODB_URI", "")
    if not uri:
        try:
            uri = st.secrets["MONGODB_URI"]
        except Exception as e:
            st.error(f"Could not read MONGODB_URI from secrets: {e}")
            return None

    if not uri:
        st.error("MONGODB_URI is empty. Add it to Streamlit secrets.")
        return None

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        return client["grant_tracker"]
    except Exception as e:
        st.error(f"MongoDB connection failed: {e}")
        return None


def load_deliverables(db) -> pd.DataFrame:
    docs = list(db["deliverables"].find({}, {"_id": 0}))
    if not docs:
        return pd.DataFrame(columns=[
            "id", "deliverable", "description", "assignee",
            "due_date", "status", "budget_allocated", "budget_spent",
            "milestone", "notes"
        ])
    return pd.DataFrame(docs)


def save_deliverable(db, record: dict):
    db["deliverables"].replace_one({"id": record["id"]}, record, upsert=True)


def delete_deliverable(db, deliverable_id: int):
    db["deliverables"].delete_one({"id": deliverable_id})


def next_deliverable_id(db) -> int:
    last = db["deliverables"].find_one(sort=[("id", -1)])
    return (last["id"] + 1) if last else 1


def bulk_insert_deliverables(db, records: list):
    if records:
        db["deliverables"].insert_many(records)


def load_team(db) -> pd.DataFrame:
    docs = list(db["team"].find({}, {"_id": 0}))
    if not docs:
        return pd.DataFrame(columns=["name", "role", "email"])
    return pd.DataFrame(docs)


def save_team_member(db, member: dict):
    db["team"].replace_one({"name": member["name"]}, member, upsert=True)


def load_notes(db) -> pd.DataFrame:
    docs = list(db["notes"].find({}, {"_id": 0}))
    if not docs:
        return pd.DataFrame(columns=["id", "type", "title", "content", "action_items", "date", "project_tag"])
    return pd.DataFrame(docs)


def save_note(db, note: dict):
    db["notes"].replace_one({"id": note["id"]}, note, upsert=True)


def next_note_id(db) -> int:
    last = db["notes"].find_one(sort=[("id", -1)])
    return (last["id"] + 1) if last else 1


def list_users(db) -> pd.DataFrame:
    docs = list(db["users"].find({}, {"_id": 0, "password_hash": 0}))
    if not docs:
        return pd.DataFrame(columns=["username", "role"])
    return pd.DataFrame(docs)
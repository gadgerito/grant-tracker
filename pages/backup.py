"""
pages/backup.py — Backup & Export all data
"""

import streamlit as st
import pandas as pd
import json
import os
import zipfile
from io import BytesIO
from datetime import date, datetime

if not st.session_state.get("authenticated"):
    st.warning("🔒 Please sign in from the main page first.")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("⛔ Admin access only.")
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

def load_from_db(db, collection):
    try:
        docs = list(db[collection].find({}, {"_id": 0}))
        return pd.DataFrame(docs) if docs else pd.DataFrame()
    except:
        return pd.DataFrame()

def load_from_csv(filename):
    DATA_DIR = "data"
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except:
            pass
    return pd.DataFrame()

st.title("💾 Backup & Export")
st.caption("Download all your data in one click. Do this weekly to make sure nothing is ever lost.")

db = get_db()

# ── Load all data ─────────────────────────────────────────────────────────────
if db is not None:
    deliverables_df = load_from_db(db, "deliverables")
    team_df = load_from_db(db, "team")
    notes_df = load_from_db(db, "notes")
    users_df = load_from_db(db, "users")
    # Remove password hashes from users export
    if not users_df.empty and "password_hash" in users_df.columns:
        users_df = users_df.drop(columns=["password_hash"])
else:
    deliverables_df = load_from_csv("deliverables.csv")
    team_df = load_from_csv("team.csv")
    notes_df = load_from_csv("notebook.csv")
    users_df = pd.DataFrame()

projects_df = load_from_csv("projects.csv")

# ── Status overview ───────────────────────────────────────────────────────────
st.subheader("📊 Data Overview")
col1, col2, col3, col4 = st.columns(4)
col1.metric("📋 Deliverables", len(deliverables_df))
col2.metric("📓 Notes", len(notes_df))
col3.metric("👥 Team Members", len(team_df))
col4.metric("📁 Projects", len(projects_df))

st.markdown(f"**Last backup check:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
st.markdown("---")

# ── ONE CLICK FULL BACKUP ─────────────────────────────────────────────────────
st.subheader("⬇️ Full Backup — Download Everything")
st.caption("Downloads a ZIP file with all your data as CSVs.")

if st.button("📦 Download Full Backup (ZIP)", type="primary", use_container_width=True):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if not deliverables_df.empty:
            zf.writestr("deliverables.csv", deliverables_df.to_csv(index=False))
        if not notes_df.empty:
            zf.writestr("notebook_notes.csv", notes_df.to_csv(index=False))
        if not team_df.empty:
            zf.writestr("team.csv", team_df.to_csv(index=False))
        if not projects_df.empty:
            zf.writestr("projects.csv", projects_df.to_csv(index=False))
        if not users_df.empty:
            zf.writestr("users.csv", users_df.to_csv(index=False))

        # Add a readme
        readme = f"""Grant Tracker Backup
====================
Date: {date.today()}
Time: {datetime.now().strftime('%I:%M %p')}

Files included:
- deliverables.csv ({len(deliverables_df)} records)
- notebook_notes.csv ({len(notes_df)} records)
- team.csv ({len(team_df)} records)
- projects.csv ({len(projects_df)} records)
- users.csv ({len(users_df)} records)

To restore: contact your administrator.
"""
        zf.writestr("README.txt", readme)

    zip_buffer.seek(0)
    st.download_button(
        "⬇️ Click here to save your backup ZIP",
        data=zip_buffer,
        file_name=f"grant_tracker_backup_{date.today()}.zip",
        mime="application/zip",
        use_container_width=True
    )
    st.success("✅ Backup ready! Save this ZIP to Google Drive or iCloud.")

st.markdown("---")

# ── INDIVIDUAL EXPORTS ────────────────────────────────────────────────────────
st.subheader("📄 Export Individual Files")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**📋 Deliverables**")
    if not deliverables_df.empty:
        st.dataframe(deliverables_df[["deliverable","status","due_date","assignee"]].head(5),
            use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export Deliverables CSV",
            data=deliverables_df.to_csv(index=False).encode("utf-8"),
            file_name=f"deliverables_{date.today()}.csv", mime="text/csv")
    else:
        st.info("No deliverables yet.")

    st.markdown("**👥 Team**")
    if not team_df.empty:
        st.dataframe(team_df.head(5), use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export Team CSV",
            data=team_df.to_csv(index=False).encode("utf-8"),
            file_name=f"team_{date.today()}.csv", mime="text/csv")
    else:
        st.info("No team members yet.")

with col2:
    st.markdown("**📓 Notebook Notes**")
    if not notes_df.empty:
        show_cols = [c for c in ["title","date","project_tag","status_tag"] if c in notes_df.columns]
        st.dataframe(notes_df[show_cols].head(5), use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export Notes CSV",
            data=notes_df.to_csv(index=False).encode("utf-8"),
            file_name=f"notes_{date.today()}.csv", mime="text/csv")
    else:
        st.info("No notes yet.")

    st.markdown("**📁 Projects**")
    if not projects_df.empty:
        st.dataframe(projects_df.head(5), use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export Projects CSV",
            data=projects_df.to_csv(index=False).encode("utf-8"),
            file_name=f"projects_{date.today()}.csv", mime="text/csv")
    else:
        st.info("No projects yet.")

st.markdown("---")

# ── RESTORE FROM CSV ──────────────────────────────────────────────────────────
st.subheader("♻️ Restore from CSV")
st.caption("⚠️ This will ADD records from your CSV to the database. It will not delete existing data.")

if st.session_state.get("role") == "admin":
    restore_type = st.selectbox("What do you want to restore?",
        ["Deliverables", "Notes", "Team", "Projects"])

    uploaded = st.file_uploader(f"Upload {restore_type} CSV", type=["csv"])
    if uploaded:
        try:
            restore_df = pd.read_csv(uploaded)
            st.dataframe(restore_df.head(5), use_container_width=True, hide_index=True)
            st.markdown(f"**{len(restore_df)} records found**")

            if st.button(f"♻️ Restore {len(restore_df)} {restore_type} records", type="primary"):
                if db is not None:
                    collection_map = {
                        "Deliverables": "deliverables",
                        "Notes": "notes",
                        "Team": "team",
                        "Projects": "projects"
                    }
                    collection = collection_map[restore_type]
                    records = restore_df.to_dict("records")
                    db[collection].insert_many(records)
                    st.success(f"✅ {len(records)} {restore_type} records restored!")
                    st.rerun()
                else:
                    st.error("No database connection.")
        except Exception as e:
            st.error(f"Could not read file: {e}")

st.markdown("---")
st.markdown("### 💡 Backup Tips")
st.markdown("""
- 🗓️ **Do a full backup every Friday** before the weekend
- ☁️ **Save your ZIP to Google Drive or iCloud** so it's accessible anywhere  
- 📧 **Email yourself the backup** for extra safety
- 🔄 **MongoDB Atlas free tier** automatically backs up your data daily
""")

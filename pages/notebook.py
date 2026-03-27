"""
pages/notebook.py — AI Notebook with folders, timeline, and PM Coach
"""

import streamlit as st
import pandas as pd
import json
import os
import urllib.request
from datetime import date, datetime

if not st.session_state.get("authenticated"):
    st.warning("🔒 Please sign in from the main page first.")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("⛔ This page is for administrators only.")
    st.stop()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    try:
        ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
    except:
        pass

def call_claude(messages, system=""):
    if not ANTHROPIC_API_KEY:
        return "⚠️ No API key found."
    payload = {"model": "claude-sonnet-4-20250514", "max_tokens": 1024, "system": system, "messages": messages}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=data,
        headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))["content"][0]["text"]
    except Exception as e:
        return f"⚠️ API error: {e}"

PM_SYSTEM = """You are an expert project management coach specializing in multi-year foundation grants. Help the user become an exceptional grant project manager. Be direct, practical, and always end with 2-3 specific next actions."""

DATA_DIR = "data"
NOTES_FILE = os.path.join(DATA_DIR, "notebook.csv")
os.makedirs(DATA_DIR, exist_ok=True)

MEETING_TYPES = ["Team Sync", "PI Meeting", "Funder Meeting", "Stakeholder", "One-on-One", "Other"]
STATUSES = ["Action Needed", "FYI", "Archived"]

def load_notes():
    if os.path.exists(NOTES_FILE):
        try:
            df = pd.read_csv(NOTES_FILE)
            for col in ["id","type","title","content","action_items","date","project_tag","meeting_type","status_tag"]:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            pass
    return pd.DataFrame(columns=["id","type","title","content","action_items","date","project_tag","meeting_type","status_tag"])

def save_notes(df):
    df.to_csv(NOTES_FILE, index=False)

notes_df = load_notes()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.title("📓 Notebook & PM Coach")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💬 PM Coach",
    "📝 Meeting Notes",
    "🔁 Reflections",
    "📂 My Folders",
    "📅 Timeline",
])

# ═══════════════════════════════════════════════════════════════════════
# TAB 1 — PM COACH
# ═══════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("💬 Chat with Your PM Coach")
    cols = st.columns(3)
    starters = [
        "How do I build a 3-year grant timeline?",
        "My team keeps missing deadlines. What do I do?",
        "How do I talk to my PI about budget overruns?",
        "What's the best way to run a grant kick-off meeting?",
        "How do I track deliverables without micromanaging?",
        "We're 6 months in and already behind. Help.",
    ]
    for i, starter in enumerate(starters):
        if cols[i % 3].button(starter, key=f"starter_{i}", use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": starter})
            with st.spinner("Coach is thinking..."):
                reply = call_claude(st.session_state.chat_history, system=PM_SYSTEM)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun()
    st.markdown("---")
    for msg in st.session_state.chat_history:
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.write(msg["content"])
    user_input = st.chat_input("Ask your PM coach anything...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = call_claude(st.session_state.chat_history, system=PM_SYSTEM)
            st.write(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
    if st.session_state.chat_history:
        if st.button("🗑️ Clear chat"):
            st.session_state.chat_history = []
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# TAB 2 — MEETING NOTES
# ═══════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📝 Log Meeting Notes")
    with st.form("meeting_form"):
        title = st.text_input("Meeting Title *")
        col1, col2, col3 = st.columns(3)
        with col1:
            project_tag = st.text_input("Project / Grant", placeholder="e.g. NIH R01")
        with col2:
            meeting_type = st.selectbox("Meeting Type", MEETING_TYPES)
        with col3:
            status_tag = st.selectbox("Status", STATUSES)
        meeting_date = st.date_input("Meeting Date", value=date.today())
        content = st.text_area("Meeting Notes", height=200)
        action_items = st.text_area("Action Items", placeholder="- [ ] Jane: submit report by Friday")
        col1, col2 = st.columns(2)
        with col1:
            save_btn = st.form_submit_button("💾 Save Notes")
        with col2:
            ai_btn = st.form_submit_button("🤖 Save + Get AI Feedback")
        if save_btn or ai_btn:
            if not title:
                st.error("Meeting title is required.")
            else:
                new_id = int(notes_df["id"].max()) + 1 if not notes_df.empty else 1
                new_note = {
                    "id": new_id, "type": "meeting", "title": title,
                    "content": content, "action_items": action_items,
                    "date": str(meeting_date), "project_tag": project_tag,
                    "meeting_type": meeting_type, "status_tag": status_tag
                }
                notes_df = pd.concat([notes_df, pd.DataFrame([new_note])], ignore_index=True)
                save_notes(notes_df)
                st.success("✅ Meeting notes saved!")
                if ai_btn and (content or action_items):
                    with st.spinner("Coach is reviewing..."):
                        feedback = call_claude([{"role": "user", "content": f"Review these meeting notes from a grant PM perspective.\nMeeting: {title}\nNotes: {content}\nAction Items: {action_items}\nGive feedback on clarity, risks, and 2-3 next steps."}], system=PM_SYSTEM)
                    st.info(feedback)

# ═══════════════════════════════════════════════════════════════════════
# TAB 3 — REFLECTIONS
# ═══════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("🔁 Weekly / Daily Reflection")
    reflection_type = st.radio("Reflection type", ["Daily", "Weekly"], horizontal=True)
    prompts = ["What did I accomplish today toward grant goals?", "What blockers came up?", "What's the one most important thing to do tomorrow?"] if reflection_type == "Daily" else ["What progress was made this week?", "What slowed us down?", "Is the project on track?", "What would I do differently?", "Any budget or timeline concerns?"]
    with st.form("reflection_form"):
        st.markdown(f"**{reflection_type} Reflection — {date.today().strftime('%B %d, %Y')}**")
        project_tag_r = st.text_input("Project / Grant Tag")
        responses = {p: st.text_area(p, key=f"reflect_{i}", height=80) for i, p in enumerate(prompts)}
        col1, col2 = st.columns(2)
        with col1:
            save_r = st.form_submit_button("💾 Save Reflection")
        with col2:
            coach_r = st.form_submit_button("🤖 Save + Get Coaching")
        if save_r or coach_r:
            combined = "\n\n".join([f"**{q}**\n{a}" for q, a in responses.items() if a.strip()])
            if not combined:
                st.error("Please fill in at least one prompt.")
            else:
                new_id = int(notes_df["id"].max()) + 1 if not notes_df.empty else 1
                new_note = {
                    "id": new_id, "type": "reflection",
                    "title": f"{reflection_type} Reflection — {date.today()}",
                    "content": combined, "action_items": "",
                    "date": str(date.today()), "project_tag": project_tag_r,
                    "meeting_type": "", "status_tag": "FYI"
                }
                notes_df = pd.concat([notes_df, pd.DataFrame([new_note])], ignore_index=True)
                save_notes(notes_df)
                st.success("✅ Reflection saved!")
                if coach_r:
                    with st.spinner("Coach is reading your reflection..."):
                        coaching = call_claude([{"role": "user", "content": f"Here is my {reflection_type.lower()} reflection:\n{combined}\nGive me: 1) One thing I am doing well, 2) One risk to address, 3) Three prioritized actions. Be direct."}], system=PM_SYSTEM)
                    st.info(coaching)

# ═══════════════════════════════════════════════════════════════════════
# TAB 4 — FOLDERS
# ═══════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("📂 My Folders")

    if notes_df.empty:
        st.info("No notes yet!")
    else:
        # Folder navigation
        col1, col2, col3 = st.columns(3)
        with col1:
            projects = ["All Projects"] + sorted(notes_df["project_tag"].dropna().unique().tolist())
            folder_project = st.selectbox("📁 Project / Grant", projects)
        with col2:
            types = ["All Types"] + MEETING_TYPES + ["reflection", "freeform"]
            folder_type = st.selectbox("📁 Meeting Type", types)
        with col3:
            statuses = ["All Statuses"] + STATUSES
            folder_status = st.selectbox("📁 Status", statuses)

        # Filter
        filtered = notes_df.copy()
        if folder_project != "All Projects":
            filtered = filtered[filtered["project_tag"] == folder_project]
        if folder_type != "All Types":
            filtered = filtered[
                (filtered["meeting_type"] == folder_type) |
                (filtered["type"] == folder_type)
            ]
        if folder_status != "All Statuses":
            filtered = filtered[filtered["status_tag"] == folder_status]

        filtered = filtered.sort_values("date", ascending=False)
        st.markdown(f"**{len(filtered)} note(s) found**")

        for _, row in filtered.iterrows():
            icon = {"meeting": "📝", "reflection": "🔁", "freeform": "📄"}.get(str(row["type"]), "📄")
            status_icon = {"Action Needed": "🔴", "FYI": "🟡", "Archived": "⚫"}.get(str(row.get("status_tag", "")), "🟢")
            label = f"{icon} {status_icon} **{row['title']}** — {row['date']}"
            if row.get("project_tag"):
                label += f" | 📁 {row['project_tag']}"
            if row.get("meeting_type"):
                label += f" | {row['meeting_type']}"
            with st.expander(label):
                st.markdown(row["content"])
                if row.get("action_items"):
                    st.markdown(f"**Action Items:**\n{row['action_items']}")

                # Update status
                col_s, col_d = st.columns(2)
                with col_s:
                    new_status = st.selectbox("Update status", STATUSES,
                        index=STATUSES.index(row["status_tag"]) if row.get("status_tag") in STATUSES else 0,
                        key=f"status_{row['id']}")
                    if st.button("💾 Update", key=f"update_{row['id']}"):
                        notes_df.loc[notes_df["id"] == row["id"], "status_tag"] = new_status
                        save_notes(notes_df)
                        st.success("Updated!")
                        st.rerun()
                with col_d:
                    if st.button("🗑️ Delete", key=f"del_{row['id']}"):
                        notes_df = notes_df[notes_df["id"] != row["id"]]
                        save_notes(notes_df)
                        st.success("Deleted!")
                        st.rerun()

        st.markdown("---")
        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Export Folder (CSV)", data=csv,
            file_name=f"notes_{date.today()}.csv", mime="text/csv")

# ═══════════════════════════════════════════════════════════════════════
# TAB 5 — TIMELINE
# ═══════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("📅 Meeting Timeline")

    if notes_df.empty:
        st.info("No notes yet to show on timeline!")
    else:
        # Filter controls
        col1, col2 = st.columns(2)
        with col1:
            tl_projects = ["All Projects"] + sorted(notes_df["project_tag"].dropna().unique().tolist())
            tl_project = st.selectbox("Filter by Project", tl_projects, key="tl_project")
        with col2:
            tl_type = st.selectbox("Filter by Type", ["All Types"] + MEETING_TYPES + ["reflection"], key="tl_type")

        tl_df = notes_df.copy()
        if tl_project != "All Projects":
            tl_df = tl_df[tl_df["project_tag"] == tl_project]
        if tl_type != "All Types":
            tl_df = tl_df[(tl_df["meeting_type"] == tl_type) | (tl_df["type"] == tl_type)]

        tl_df = tl_df.sort_values("date", ascending=False)

        # ── Table view ────────────────────────────────────────────────
        st.markdown("### 📋 Table View")
        table_data = []
        for _, row in tl_df.iterrows():
            status_icon = {"Action Needed": "🔴", "FYI": "🟡", "Archived": "⚫"}.get(str(row.get("status_tag", "")), "🟢")
            table_data.append({
                "Date": row["date"],
                "Status": f"{status_icon} {row.get('status_tag', '')}",
                "Title": row["title"],
                "Project": row.get("project_tag", ""),
                "Type": row.get("meeting_type", row.get("type", "")),
            })
        if table_data:
            st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

        # ── Visual timeline ───────────────────────────────────────────
        st.markdown("### 🗓️ Visual Timeline")

        # Group by month
        tl_df["_month"] = pd.to_datetime(tl_df["date"], errors="coerce").dt.strftime("%B %Y")
        months = tl_df["_month"].dropna().unique().tolist()

        for month in months:
            month_notes = tl_df[tl_df["_month"] == month]
            st.markdown(f"#### 📅 {month}")
            for _, row in month_notes.iterrows():
                status_icon = {"Action Needed": "🔴", "FYI": "🟡", "Archived": "⚫"}.get(str(row.get("status_tag", "")), "🟢")
                icon = {"meeting": "📝", "reflection": "🔁", "freeform": "📄"}.get(str(row["type"]), "📝")
                with st.expander(f"{status_icon} {icon} **{row['title']}** — {row['date']} | {row.get('meeting_type', '')} | {row.get('project_tag', '')}"):
                    st.markdown(row["content"][:500] + ("..." if len(str(row["content"])) > 500 else ""))
                    if row.get("action_items"):
                        st.markdown(f"**Action Items:** {row['action_items']}")
            st.markdown("---")

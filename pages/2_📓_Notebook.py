"""
pages/notebook.py — Notebook with project folders, meeting transcripts, overviews, timeline, PM Coach
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
    payload = {"model": "claude-sonnet-4-20250514", "max_tokens": 1500, "system": system, "messages": messages}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=data,
        headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))["content"][0]["text"]
    except Exception as e:
        return f"⚠️ API error: {e}"

def extract_text_from_docx(file):
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        from io import BytesIO
        docx_bytes = BytesIO(file.read())
        with zipfile.ZipFile(docx_bytes) as z:
            with z.open("word/document.xml") as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                paragraphs = []
                for para in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                    texts = [node.text for node in para.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
                    if texts:
                        paragraphs.append("".join(texts))
        return "\n".join(paragraphs)
    except Exception as e:
        return f"ERROR: {e}"

PM_SYSTEM = """You are an expert project management coach specializing in multi-year foundation grants. Be direct, practical, always end with 2-3 specific next actions."""

MINUTES_SYSTEM = """You are an ADHD-friendly meeting summarizer for a grant project manager.
Extract only what matters using traffic lights:
🔴 = urgent/blocked/overdue, 🟡 = needs attention, 🟢 = on track/done
One sentence per point. No walls of text. Bold the most critical item in each section."""

PROJECT_OVERVIEW_SYSTEM = """You are a grant project manager assistant. Analyze meeting notes and provide a concise ADHD-friendly project overview using traffic lights. One sentence per point. No walls of text."""

DATA_DIR = "data"
NOTES_FILE = os.path.join(DATA_DIR, "notebook.csv")
PROJECTS_FILE = os.path.join(DATA_DIR, "projects.csv")
os.makedirs(DATA_DIR, exist_ok=True)

MEETING_TYPES = ["Team Sync", "PI Meeting", "Funder Meeting", "Stakeholder", "One-on-One", "Other"]
NOTE_STATUSES = ["Action Needed", "FYI", "Archived"]

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

def load_projects():
    if os.path.exists(PROJECTS_FILE):
        try:
            return pd.read_csv(PROJECTS_FILE)
        except:
            pass
    return pd.DataFrame(columns=["name","description","start_date","end_date","funder"])

def save_projects(df):
    df.to_csv(PROJECTS_FILE, index=False)

def get_next_id(df):
    return int(df["id"].max()) + 1 if not df.empty and "id" in df.columns else 1

def add_note(notes_df, title, content, action_items, project_tag, meeting_type, status_tag, note_type="meeting", note_date=None):
    new_note = {
        "id": get_next_id(notes_df), "type": note_type, "title": title,
        "content": content, "action_items": action_items,
        "date": str(note_date or date.today()), "project_tag": project_tag,
        "meeting_type": meeting_type, "status_tag": status_tag
    }
    return pd.concat([notes_df, pd.DataFrame([new_note])], ignore_index=True)

notes_df = load_notes()
projects_df = load_projects()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

all_project_names = sorted(set(
    list(projects_df["name"].tolist()) +
    list(notes_df["project_tag"].dropna().unique().tolist())
))

st.title("📓 Notebook & PM Coach")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📁 Project Folders",
    "🔍 Project Overview",
    "📋 Transcribe & File",
    "📝 Add Notes",
    "📅 Timeline",
    "🔁 Reflections",
    "💬 PM Coach",
])

# ═══════════════════════════════════════════════════════════════════════
# TAB 1 — PROJECT FOLDERS
# ═══════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("📁 Project Folders")
    col_left, col_right = st.columns([1, 3])

    with col_left:
        st.markdown("**Your Projects**")
        with st.expander("➕ Add Project"):
            with st.form("add_project"):
                p_name = st.text_input("Project Name *")
                p_funder = st.text_input("Funder")
                p_desc = st.text_input("Description")
                p_start = st.date_input("Start Date", value=date.today())
                p_end = st.date_input("End Date", value=date.today())
                if st.form_submit_button("Add"):
                    if p_name:
                        projects_df = pd.concat([projects_df, pd.DataFrame([{
                            "name": p_name, "description": p_desc,
                            "start_date": str(p_start), "end_date": str(p_end), "funder": p_funder
                        }])], ignore_index=True)
                        save_projects(projects_df)
                        st.success(f"✅ {p_name} added!")
                        st.rerun()

        if not all_project_names:
            st.info("No projects yet.")
        else:
            selected_project = st.radio("Select project", all_project_names, key="selected_project")

    with col_right:
        if "selected_project" in st.session_state and st.session_state.selected_project:
            project = st.session_state.selected_project
            st.markdown(f"### 📁 {project}")
            proj_info = projects_df[projects_df["name"] == project]
            if not proj_info.empty:
                row = proj_info.iloc[0]
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Funder", row.get("funder", "—"))
                col_b.metric("Start", str(row.get("start_date", "—")))
                col_c.metric("End", str(row.get("end_date", "—")))
                if row.get("description"):
                    st.caption(row["description"])
            st.markdown("---")

            project_notes = notes_df[notes_df["project_tag"] == project].sort_values("date", ascending=False)
            col1, col2 = st.columns(2)
            with col1:
                filter_type = st.multiselect("Meeting Type", MEETING_TYPES, default=MEETING_TYPES, key=f"ft_{project}")
            with col2:
                filter_status = st.multiselect("Status", NOTE_STATUSES, default=NOTE_STATUSES, key=f"fs_{project}")

            filtered = project_notes[
                (project_notes["meeting_type"].isin(filter_type)) &
                (project_notes["status_tag"].isin(filter_status))
            ] if not project_notes.empty else project_notes

            st.markdown(f"**{len(filtered)} note(s)**")
            if filtered.empty:
                st.info("No notes yet. Use **Transcribe & File** to add meeting summaries!")
            else:
                for _, row in filtered.iterrows():
                    status_icon = {"Action Needed": "🔴", "FYI": "🟡", "Archived": "⚫"}.get(str(row.get("status_tag", "")), "🟢")
                    icon = {"meeting": "📝", "reflection": "🔁"}.get(str(row["type"]), "📄")
                    with st.expander(f"{status_icon} {icon} **{row['title']}** — {row['date']} | {row.get('meeting_type', '')}"):
                        st.markdown(row["content"])
                        if row.get("action_items"):
                            st.markdown(f"**Action Items:**\n{row['action_items']}")
                        col_s, col_d = st.columns(2)
                        with col_s:
                            new_s = st.selectbox("Status", NOTE_STATUSES,
                                index=NOTE_STATUSES.index(row["status_tag"]) if row.get("status_tag") in NOTE_STATUSES else 0,
                                key=f"s_{row['id']}")
                            if st.button("💾 Update", key=f"u_{row['id']}"):
                                notes_df.loc[notes_df["id"] == row["id"], "status_tag"] = new_s
                                save_notes(notes_df)
                                st.rerun()
                        with col_d:
                            if st.button("🗑️ Delete", key=f"d_{row['id']}"):
                                notes_df = notes_df[notes_df["id"] != row["id"]]
                                save_notes(notes_df)
                                st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# TAB 2 — PROJECT OVERVIEW
# ═══════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🔍 Project Overview")
    st.caption("Claude reads all your meeting notes for a project and generates a traffic light summary.")

    if not all_project_names:
        st.info("No projects yet!")
    else:
        ov_project = st.selectbox("Select project", all_project_names, key="ov_project")
        project_notes_ov = notes_df[notes_df["project_tag"] == ov_project].sort_values("date")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Notes", len(project_notes_ov))
        col2.metric("Action Needed", len(project_notes_ov[project_notes_ov["status_tag"] == "Action Needed"]))
        col3.metric("Last Meeting", project_notes_ov["date"].max() if not project_notes_ov.empty else "None")

        if not project_notes_ov.empty:
            if st.button("🤖 Generate Project Overview", type="primary"):
                combined_notes = ""
                for _, row in project_notes_ov.iterrows():
                    combined_notes += f"\n\n--- {row['date']} | {row.get('meeting_type', '')} | {row['title']} ---\n{row['content']}"
                    if row.get("action_items"):
                        combined_notes += f"\nAction Items: {row['action_items']}"
                combined_notes = combined_notes[:8000]
                prompt = f"""All meeting notes for project: {ov_project}

{combined_notes}

Generate ADHD-friendly project overview:

## 🔴🟡🟢 PROJECT HEALTH
One sentence overall status with traffic light.

## ✅ COMPLETED
Bullet list of wins. One sentence each.

## 🔴 OPEN ACTION ITEMS
Format: 🔴/🟡 **[Owner]**: [Task]

## 🚧 RISKS & BLOCKERS
One sentence each with traffic light.

## 📈 KEY DECISIONS
Bullet list. One sentence each.

## ⏭️ NEXT STEPS
Top 3 next steps. Bold the most urgent.

No paragraphs. Scannable only."""

                with st.spinner("Claude is analyzing your meeting notes..."):
                    overview = call_claude([{"role": "user", "content": prompt}], system=PROJECT_OVERVIEW_SYSTEM)
                st.markdown("---")
                st.markdown(f"### 📊 {ov_project} — Overview")
                st.markdown(overview)
                st.session_state[f"overview_{ov_project}"] = overview

            if f"overview_{ov_project}" in st.session_state:
                st.download_button("⬇️ Download Overview",
                    data=st.session_state[f"overview_{ov_project}"].encode("utf-8"),
                    file_name=f"{ov_project}_overview_{date.today()}.txt", mime="text/plain")
        else:
            st.info("No notes for this project yet!")

# ═══════════════════════════════════════════════════════════════════════
# TAB 3 — TRANSCRIBE & FILE
# ═══════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📋 Transcribe Meeting & File to Folder")
    st.caption("Upload or paste your meeting transcript — Claude summarizes it and you file it straight into a project folder.")

    col1, col2, col3 = st.columns(3)
    with col1:
        meeting_title = st.text_input("Meeting Title *", placeholder="e.g. Q1 Team Sync")
    with col2:
        file_project = st.selectbox("File into Project *", [""] + all_project_names, key="file_project")
    with col3:
        file_meeting_type = st.selectbox("Meeting Type", MEETING_TYPES, key="file_mt")

    col4, col5 = st.columns(2)
    with col4:
        file_date = st.date_input("Meeting Date", value=date.today(), key="file_date")
    with col5:
        file_status = st.selectbox("Status", NOTE_STATUSES, key="file_status")

    input_method = st.radio("Input method", ["📋 Paste text", "📄 Upload file (.txt or .docx)"], horizontal=True)

    raw_text = ""
    if input_method == "📋 Paste text":
        raw_text = st.text_area("Paste transcript or meeting notes", height=200,
            placeholder="Paste raw notes, transcript, or bullet points...")
    else:
        uploaded = st.file_uploader("Upload transcript", type=["txt", "docx"])
        if uploaded:
            if uploaded.name.endswith(".txt"):
                raw_text = uploaded.read().decode("utf-8", errors="ignore")
                st.success(f"✅ {len(raw_text.split())} words loaded")
            elif uploaded.name.endswith(".docx"):
                raw_text = extract_text_from_docx(uploaded)
                if raw_text.startswith("ERROR"):
                    st.error(raw_text)
                    raw_text = ""
                else:
                    st.success(f"✅ {len(raw_text.split())} words loaded")
            if raw_text:
                with st.expander("Preview"):
                    st.text(raw_text[:500] + "...")

    if raw_text.strip():
        col_a, col_b = st.columns(2)
        with col_a:
            summarize_btn = st.button("🤖 Summarize with Claude", type="primary")
        with col_b:
            save_raw_btn = st.button("💾 Save Raw Notes (no summary)")

        if save_raw_btn:
            if not meeting_title:
                st.error("Please add a meeting title.")
            elif not file_project:
                st.error("Please select a project folder.")
            else:
                notes_df = add_note(notes_df, meeting_title, raw_text, "", file_project, file_meeting_type, file_status, note_date=file_date)
                save_notes(notes_df)
                st.success(f"✅ Raw notes saved to **{file_project}**!")
                st.rerun()

        if summarize_btn:
            text_to_send = raw_text[:8000] if len(raw_text) > 8000 else raw_text
            prompt = f"""Meeting: {meeting_title or 'Team Meeting'}

TRANSCRIPT/NOTES:
{text_to_send}

## 🔴🟡🟢 KEY DECISIONS
Traffic lights. One sentence each. Bold the most important.

## ✅ ACTION ITEMS
Format: 🔴/🟡/🟢 **[Owner]**: [Task] — Due: [date or ASAP]

## 🚧 BLOCKERS & RISKS
🔴 blockers, 🟡 risks. One sentence each.

## ❓ FOLLOW-UP QUESTIONS
Short bullet list.

## ⚡ THE ONE THING
Bold: the single most important thing before the next meeting.

No paragraphs. ADHD-friendly only."""

            with st.spinner("Claude is summarizing..."):
                summary = call_claude([{"role": "user", "content": prompt}], system=MINUTES_SYSTEM)

            st.markdown("---")
            st.markdown("### 📊 Summary")
            st.markdown(summary)
            st.session_state["transcript_summary"] = summary
            st.session_state["transcript_title"] = meeting_title
            st.session_state["transcript_project"] = file_project
            st.session_state["transcript_type"] = file_meeting_type
            st.session_state["transcript_status"] = file_status
            st.session_state["transcript_date"] = file_date

    if "transcript_summary" in st.session_state:
        st.markdown("---")
        st.markdown("### 📁 File this summary")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ File Summary to Folder", type="primary"):
                if not st.session_state.get("transcript_project"):
                    st.error("Please select a project folder first.")
                elif not st.session_state.get("transcript_title"):
                    st.error("Please add a meeting title first.")
                else:
                    notes_df = add_note(
                        notes_df,
                        st.session_state["transcript_title"],
                        st.session_state["transcript_summary"],
                        "", 
                        st.session_state["transcript_project"],
                        st.session_state["transcript_type"],
                        st.session_state["transcript_status"],
                        note_date=st.session_state["transcript_date"]
                    )
                    save_notes(notes_df)
                    st.success(f"✅ Filed to **{st.session_state['transcript_project']}**!")
                    del st.session_state["transcript_summary"]
                    st.rerun()
        with col2:
            st.download_button("⬇️ Download Summary",
                data=st.session_state["transcript_summary"].encode("utf-8"),
                file_name=f"summary_{date.today()}.txt", mime="text/plain")

# ═══════════════════════════════════════════════════════════════════════
# TAB 4 — ADD NOTES MANUALLY
# ═══════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("📝 Add Meeting Notes Manually")
    with st.form("meeting_form"):
        title = st.text_input("Meeting Title *")
        col1, col2, col3 = st.columns(3)
        with col1:
            project_tag = st.selectbox("Project / Grant", [""] + all_project_names)
        with col2:
            meeting_type = st.selectbox("Meeting Type", MEETING_TYPES)
        with col3:
            status_tag = st.selectbox("Status", NOTE_STATUSES)
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
                notes_df = add_note(notes_df, title, content, action_items, project_tag, meeting_type, status_tag, note_date=meeting_date)
                save_notes(notes_df)
                st.success(f"✅ Saved to **{project_tag or 'no folder'}**!")
                if ai_btn and (content or action_items):
                    with st.spinner("Coach is reviewing..."):
                        feedback = call_claude([{"role": "user", "content": f"Review these meeting notes.\nMeeting: {title}\nNotes: {content}\nAction Items: {action_items}\nGive feedback on clarity, risks, 2-3 next steps."}], system=PM_SYSTEM)
                    st.info(feedback)

# ═══════════════════════════════════════════════════════════════════════
# TAB 5 — TIMELINE
# ═══════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("📅 Timeline")
    if notes_df.empty:
        st.info("No notes yet!")
    else:
        col1, col2 = st.columns(2)
        with col1:
            tl_projects = ["All Projects"] + sorted(notes_df["project_tag"].dropna().unique().tolist())
            tl_project = st.selectbox("Filter by Project", tl_projects, key="tl_p")
        with col2:
            tl_type = st.selectbox("Filter by Type", ["All Types"] + MEETING_TYPES, key="tl_t")

        tl_df = notes_df.copy()
        if tl_project != "All Projects":
            tl_df = tl_df[tl_df["project_tag"] == tl_project]
        if tl_type != "All Types":
            tl_df = tl_df[tl_df["meeting_type"] == tl_type]
        tl_df = tl_df.sort_values("date", ascending=False)

        st.markdown("### 📋 Table View")
        table_data = []
        for _, row in tl_df.iterrows():
            status_icon = {"Action Needed": "🔴", "FYI": "🟡", "Archived": "⚫"}.get(str(row.get("status_tag", "")), "🟢")
            table_data.append({
                "Date": row["date"], "Status": f"{status_icon} {row.get('status_tag', '')}",
                "Title": row["title"], "Project": row.get("project_tag", ""),
                "Type": row.get("meeting_type", ""),
            })
        if table_data:
            st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

        st.markdown("### 🗓️ Visual Timeline")
        tl_df["_month"] = pd.to_datetime(tl_df["date"], errors="coerce").dt.strftime("%B %Y")
        for month in tl_df["_month"].dropna().unique():
            month_notes = tl_df[tl_df["_month"] == month]
            st.markdown(f"#### 📅 {month}")
            for _, row in month_notes.iterrows():
                status_icon = {"Action Needed": "🔴", "FYI": "🟡", "Archived": "⚫"}.get(str(row.get("status_tag", "")), "🟢")
                with st.expander(f"{status_icon} **{row['title']}** — {row['date']} | {row.get('meeting_type', '')} | {row.get('project_tag', '')}"):
                    st.markdown(str(row["content"])[:500] + ("..." if len(str(row["content"])) > 500 else ""))
            st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════
# TAB 6 — REFLECTIONS
# ═══════════════════════════════════════════════════════════════════════
with tab6:
    st.subheader("🔁 Weekly / Daily Reflection")
    reflection_type = st.radio("Type", ["Daily", "Weekly"], horizontal=True)
    prompts = ["What did I accomplish today?", "What blockers came up?", "Most important thing to do tomorrow?"] if reflection_type == "Daily" else ["Progress this week?", "What slowed us down?", "On track for next milestone?", "What would I do differently?", "Budget or timeline concerns?"]
    with st.form("reflection_form"):
        project_tag_r = st.selectbox("Project", [""] + all_project_names)
        responses = {p: st.text_area(p, key=f"r_{i}", height=80) for i, p in enumerate(prompts)}
        col1, col2 = st.columns(2)
        with col1:
            save_r = st.form_submit_button("💾 Save")
        with col2:
            coach_r = st.form_submit_button("🤖 Save + Coach")
        if save_r or coach_r:
            combined = "\n\n".join([f"**{q}**\n{a}" for q, a in responses.items() if a.strip()])
            if combined:
                notes_df = add_note(notes_df, f"{reflection_type} Reflection — {date.today()}",
                    combined, "", project_tag_r, "", "FYI", note_type="reflection")
                save_notes(notes_df)
                st.success("✅ Saved!")
                if coach_r:
                    with st.spinner("Coach is reading..."):
                        coaching = call_claude([{"role": "user", "content": f"My {reflection_type.lower()} reflection:\n{combined}\nGive: 1) One thing I'm doing well, 2) One risk, 3) Three next actions."}], system=PM_SYSTEM)
                    st.info(coaching)

# ═══════════════════════════════════════════════════════════════════════
# TAB 7 — PM COACH
# ═══════════════════════════════════════════════════════════════════════
with tab7:
    st.subheader("💬 PM Coach Chat")
    cols = st.columns(3)
    starters = ["How do I build a 3-year grant timeline?", "My team keeps missing deadlines.", "How to talk to my PI about budget overruns?", "Best way to run a grant kick-off?", "Track deliverables without micromanaging?", "6 months in and already behind. Help."]
    for i, s in enumerate(starters):
        if cols[i % 3].button(s, key=f"st_{i}", use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": s})
            with st.spinner("Thinking..."):
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
        if st.button("🗑️ Clear"):
            st.session_state.chat_history = []
            st.rerun()

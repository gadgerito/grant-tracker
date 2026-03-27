"""
pages/notebook.py — Notebook with project folders, overviews, timeline, PM Coach
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

PM_SYSTEM = """You are an expert project management coach specializing in multi-year foundation grants. Be direct, practical, always end with 2-3 specific next actions."""

PROJECT_OVERVIEW_SYSTEM = """You are a grant project manager assistant. Analyze meeting notes and provide a concise project overview using traffic lights:
🔴 = urgent/at risk, 🟡 = needs attention, 🟢 = on track
Keep everything scannable and ADHD-friendly. One sentence per point. No walls of text."""

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
    return pd.DataFrame(columns=["name", "description", "start_date", "end_date", "funder"])

def save_projects(df):
    df.to_csv(PROJECTS_FILE, index=False)

notes_df = load_notes()
projects_df = load_projects()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.title("📓 Notebook & PM Coach")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📁 Project Folders",
    "🔍 Project Overview",
    "📝 Add Meeting Notes",
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

        # Add new project
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
                            "start_date": str(p_start), "end_date": str(p_end),
                            "funder": p_funder
                        }])], ignore_index=True)
                        save_projects(projects_df)
                        st.success(f"✅ {p_name} added!")
                        st.rerun()

        # Project list
        all_projects = sorted(set(
            list(projects_df["name"].tolist()) +
            list(notes_df["project_tag"].dropna().unique().tolist())
        ))

        if not all_projects:
            st.info("No projects yet.")
        else:
            selected_project = st.radio("Select project", all_projects, key="selected_project")

    with col_right:
        if "selected_project" in st.session_state and st.session_state.selected_project:
            project = st.session_state.selected_project
            st.markdown(f"### 📁 {project}")

            # Project info
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

            # Filter notes for this project
            project_notes = notes_df[notes_df["project_tag"] == project].sort_values("date", ascending=False)

            # Sub-filters
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
                st.info("No notes in this folder yet. Add meeting notes and tag them with this project!")
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
    st.caption("Select a project and Claude will generate an ADHD-friendly overview from all your meeting notes.")

    all_projects_ov = sorted(set(
        list(projects_df["name"].tolist()) +
        list(notes_df["project_tag"].dropna().unique().tolist())
    ))

    if not all_projects_ov:
        st.info("No projects yet!")
    else:
        ov_project = st.selectbox("Select project", all_projects_ov, key="ov_project")
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

                prompt = f"""Here are all meeting notes for project: {ov_project}

{combined_notes}

Generate a concise ADHD-friendly project overview:

## 🔴🟡🟢 PROJECT HEALTH
One sentence on overall status with traffic light.

## ✅ COMPLETED SINCE LAST MEETING
Bullet list of wins. One sentence each.

## 🔴 OPEN ACTION ITEMS
List all unresolved action items. Format: 🔴/🟡 **[Owner]**: [Task]

## 🚧 ONGOING RISKS OR BLOCKERS
One sentence each with traffic light.

## 📈 KEY DECISIONS MADE
Bullet list. One sentence each.

## ⏭️ NEXT STEPS
Top 3 things that need to happen next. Bold the most urgent.

Keep everything scannable. No paragraphs."""

                with st.spinner("Claude is analyzing all your meeting notes..."):
                    overview = call_claude([{"role": "user", "content": prompt}], system=PROJECT_OVERVIEW_SYSTEM)

                st.markdown("---")
                st.markdown(f"### 📊 {ov_project} — Project Overview")
                st.markdown(overview)
                st.session_state[f"overview_{ov_project}"] = overview

            if f"overview_{ov_project}" in st.session_state:
                st.download_button(
                    "⬇️ Download Overview",
                    data=st.session_state[f"overview_{ov_project}"].encode("utf-8"),
                    file_name=f"{ov_project}_overview_{date.today()}.txt",
                    mime="text/plain"
                )
        else:
            st.info("No notes for this project yet. Add meeting notes and tag them with this project!")

# ═══════════════════════════════════════════════════════════════════════
# TAB 3 — ADD MEETING NOTES
# ═══════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📝 Add Meeting Notes")
    all_project_names = sorted(set(
        list(projects_df["name"].tolist()) +
        list(notes_df["project_tag"].dropna().unique().tolist())
    ))
    with st.form("meeting_form"):
        title = st.text_input("Meeting Title *")
        col1, col2, col3 = st.columns(3)
        with col1:
            project_tag = st.selectbox("Project / Grant", [""] + all_project_names) if all_project_names else st.text_input("Project / Grant")
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
                new_id = int(notes_df["id"].max()) + 1 if not notes_df.empty else 1
                new_note = {"id": new_id, "type": "meeting", "title": title,
                    "content": content, "action_items": action_items,
                    "date": str(meeting_date), "project_tag": project_tag,
                    "meeting_type": meeting_type, "status_tag": status_tag}
                notes_df = pd.concat([notes_df, pd.DataFrame([new_note])], ignore_index=True)
                save_notes(notes_df)
                st.success("✅ Saved!")
                if ai_btn and (content or action_items):
                    with st.spinner("Coach is reviewing..."):
                        feedback = call_claude([{"role": "user", "content": f"Review these meeting notes.\nMeeting: {title}\nNotes: {content}\nAction Items: {action_items}\nGive feedback on clarity, risks, and 2-3 next steps."}], system=PM_SYSTEM)
                    st.info(feedback)

# ═══════════════════════════════════════════════════════════════════════
# TAB 4 — TIMELINE
# ═══════════════════════════════════════════════════════════════════════
with tab4:
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
                "Date": row["date"],
                "Status": f"{status_icon} {row.get('status_tag', '')}",
                "Title": row["title"],
                "Project": row.get("project_tag", ""),
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
# TAB 5 — REFLECTIONS
# ═══════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("🔁 Weekly / Daily Reflection")
    reflection_type = st.radio("Type", ["Daily", "Weekly"], horizontal=True)
    prompts = ["What did I accomplish today?", "What blockers came up?", "Most important thing to do tomorrow?"] if reflection_type == "Daily" else ["Progress this week?", "What slowed us down?", "On track for next milestone?", "What would I do differently?", "Budget or timeline concerns?"]
    with st.form("reflection_form"):
        project_tag_r = st.selectbox("Project", [""] + sorted(set(list(projects_df["name"].tolist()) + list(notes_df["project_tag"].dropna().unique().tolist()))))
        responses = {p: st.text_area(p, key=f"r_{i}", height=80) for i, p in enumerate(prompts)}
        col1, col2 = st.columns(2)
        with col1:
            save_r = st.form_submit_button("💾 Save")
        with col2:
            coach_r = st.form_submit_button("🤖 Save + Coach")
        if save_r or coach_r:
            combined = "\n\n".join([f"**{q}**\n{a}" for q, a in responses.items() if a.strip()])
            if combined:
                new_id = int(notes_df["id"].max()) + 1 if not notes_df.empty else 1
                notes_df = pd.concat([notes_df, pd.DataFrame([{"id": new_id, "type": "reflection",
                    "title": f"{reflection_type} Reflection — {date.today()}",
                    "content": combined, "action_items": "", "date": str(date.today()),
                    "project_tag": project_tag_r, "meeting_type": "", "status_tag": "FYI"}])], ignore_index=True)
                save_notes(notes_df)
                st.success("✅ Saved!")
                if coach_r:
                    with st.spinner("Coach is reading..."):
                        coaching = call_claude([{"role": "user", "content": f"My {reflection_type.lower()} reflection:\n{combined}\nGive: 1) One thing I'm doing well, 2) One risk, 3) Three next actions."}], system=PM_SYSTEM)
                    st.info(coaching)

# ═══════════════════════════════════════════════════════════════════════
# TAB 6 — PM COACH
# ═══════════════════════════════════════════════════════════════════════
with tab6:
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

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
        return "⚠️ No API key found. Add ANTHROPIC_API_KEY to your secrets."
    payload = {"model": "claude-sonnet-4-20250514", "max_tokens": 1024, "system": system, "messages": messages}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=data,
        headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))["content"][0]["text"]
    except Exception as e:
        return f"⚠️ API error: {e}"

PM_SYSTEM = """You are an expert project management coach specializing in multi-year foundation grants. Help the user become an exceptional grant project manager with expertise in budgets, timelines, team coordination, and funder communication. Be direct, practical, and always end with 2-3 specific next actions."""

DATA_DIR = "data"
NOTES_FILE = os.path.join(DATA_DIR, "notebook.csv")
os.makedirs(DATA_DIR, exist_ok=True)

def load_notes():
    if os.path.exists(NOTES_FILE):
        try:
            return pd.read_csv(NOTES_FILE)
        except:
            pass
    return pd.DataFrame(columns=["id","type","title","content","action_items","date","project_tag"])

def save_notes(df):
    df.to_csv(NOTES_FILE, index=False)

notes_df = load_notes()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.title("📓 Notebook & PM Coach")
st.caption("Take notes, log meetings, reflect — and get AI coaching to level up your grant management.")

tab1, tab2, tab3, tab4 = st.tabs(["💬 PM Coach Chat", "📝 Meeting Notes", "🔁 Reflections", "📂 All Notes"])

with tab1:
    st.subheader("💬 Chat with Your PM Coach")
    cols = st.columns(3)
    starters = ["How do I build a 3-year grant timeline?", "My team keeps missing deadlines. What do I do?", "How do I talk to my PI about budget overruns?", "What's the best way to run a grant kick-off meeting?", "How do I track deliverables without micromanaging?", "We're 6 months in and already behind. Help."]
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

with tab2:
    st.subheader("📝 Log Meeting Notes")
    with st.form("meeting_form"):
        title = st.text_input("Meeting Title *")
        project_tag = st.text_input("Project / Grant Tag")
        meeting_date = st.date_input("Meeting Date", value=date.today())
        content = st.text_area("Meeting Notes", height=200)
        action_items = st.text_area("Action Items")
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
                notes_df = pd.concat([notes_df, pd.DataFrame([{"id": new_id, "type": "meeting", "title": title, "content": content, "action_items": action_items, "date": str(meeting_date), "project_tag": project_tag}])], ignore_index=True)
                save_notes(notes_df)
                st.success("✅ Meeting notes saved!")
                if ai_btn and (content or action_items):
                    with st.spinner("Coach is reviewing..."):
                        feedback = call_claude([{"role": "user", "content": f"Review these meeting notes from a grant PM perspective.\nMeeting: {title}\nNotes: {content}\nAction Items: {action_items}\nGive feedback on clarity, risks, and 2-3 next steps."}], system=PM_SYSTEM)
                    st.info(feedback)

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
                notes_df = pd.concat([notes_df, pd.DataFrame([{"id": new_id, "type": "reflection", "title": f"{reflection_type} Reflection — {date.today()}", "content": combined, "action_items": "", "date": str(date.today()), "project_tag": project_tag_r}])], ignore_index=True)
                save_notes(notes_df)
                st.success("✅ Reflection saved!")
                if coach_r:
                    with st.spinner("Coach is reading your reflection..."):
                        coaching = call_claude([{"role": "user", "content": f"Here is my {reflection_type.lower()} reflection:\n{combined}\nGive me: 1) One thing I am doing well, 2) One risk to address, 3) Three prioritized actions. Be direct."}], system=PM_SYSTEM)
                    st.info(coaching)

with tab4:
    st.subheader("📂 All Notes")
    if notes_df.empty:
        st.info("No notes yet — start with a meeting log or reflection!")
    else:
        filter_type = st.multiselect("Filter by Type", ["meeting", "reflection", "freeform"], default=["meeting", "reflection", "freeform"])
        filtered = notes_df[notes_df["type"].isin(filter_type)].sort_values("date", ascending=False)
        for _, row in filtered.iterrows():
            icon = {"meeting": "📝", "reflection": "🔁", "freeform": "📄"}.get(row["type"], "📄")
            with st.expander(f"{icon} **{row['title']}** — {row['date']}"):
                st.markdown(row["content"])
                if row["action_items"]:
                    st.markdown(f"**Action Items:** {row['action_items']}")
        st.download_button("⬇️ Export Notes (CSV)", data=filtered.to_csv(index=False).encode("utf-8"), file_name=f"notebook_{date.today()}.csv", mime="text/csv")
    st.markdown("---")
    st.subheader("✏️ Quick Note")
    with st.form("freeform_form"):
        ff_title = st.text_input("Title")
        ff_tag = st.text_input("Project Tag")
        ff_content = st.text_area("Note", height=150)
        if st.form_submit_button("💾 Save Note"):
            if ff_content:
                new_id = int(notes_df["id"].max()) + 1 if not notes_df.empty else 1
                notes_df = pd.concat([notes_df, pd.DataFrame([{"id": new_id, "type": "freeform", "title": ff_title or "Untitled", "content": ff_content, "action_items": "", "date": str(date.today()), "project_tag": ff_tag}])], ignore_index=True)
                save_notes(notes_df)
                st.success("✅ Note saved!")
                st.rerun()

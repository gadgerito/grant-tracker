"""
pages/adhd_dashboard.py — ADHD-Friendly Dashboard & Meeting Minutes Summarizer
"""

import streamlit as st
import pandas as pd
import json
import os
import urllib.request
from datetime import date, datetime, timedelta

if not st.session_state.get("authenticated"):
    st.warning("🔒 Please sign in from the main page first.")
    st.stop()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    try:
        ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
    except:
        pass

def call_claude(prompt, system=""):
    if not ANTHROPIC_API_KEY:
        return "⚠️ No API key found."
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1500,
        "system": system,
        "messages": [{"role": "user", "content": prompt}]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=data,
        headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
        method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))["content"][0]["text"]
    except Exception as e:
        return f"⚠️ Error: {e}"

def get_db():
    try:
        from pymongo import MongoClient
        uri = os.environ.get("MONGODB_URI", "") or st.secrets.get("MONGODB_URI", "")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        return client["grant_tracker"]
    except:
        return None

# ── Load deliverables ─────────────────────────────────────────────────────────
db = get_db()
today = date.today()
week_end = today + timedelta(days=7)

df = pd.DataFrame()
if db is not None:
    try:
        from db import load_deliverables
        df = load_deliverables(db)
    except:
        pass

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🧠 ADHD Dashboard")
st.caption(f"Today is **{today.strftime('%A, %B %d, %Y')}** — here's what matters right now.")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 1 — FOCUS ZONES
# ═══════════════════════════════════════════════════════════════════════
if not df.empty:
    # Parse dates
    def parse_date(d):
        try:
            return datetime.strptime(str(d), "%Y-%m-%d").date()
        except:
            return None

    df["_due"] = df["due_date"].apply(parse_date)
    df["_days"] = df["_due"].apply(lambda d: (d - today).days if d else None)

    incomplete = df[df["status"] != "Complete"].copy()

    # Overdue
    overdue = incomplete[incomplete["_days"].apply(lambda x: x is not None and x < 0)]
    # This week
    this_week = incomplete[incomplete["_days"].apply(lambda x: x is not None and 0 <= x <= 7)]
    # Quick wins = Not Started, no budget complexity
    quick_wins = incomplete[
        (incomplete["status"] == "Not Started") &
        (incomplete["_days"].apply(lambda x: x is not None and x > 7))
    ].head(3)

    # ── 🔴 OVERDUE ────────────────────────────────────────────────────
    if not overdue.empty:
        st.markdown("### 🔴 Overdue — Handle These First")
        for _, row in overdue.iterrows():
            days_late = abs(int(row["_days"]))
            st.error(f"**{row['deliverable']}** — {days_late} day{'s' if days_late != 1 else ''} overdue | 👤 {row['assignee']} | 🏁 {row['milestone']}")
        st.markdown("")

    # ── 🟡 THIS WEEK ──────────────────────────────────────────────────
    if not this_week.empty:
        st.markdown("### 🟡 Due This Week — Stay On Track")
        for _, row in this_week.iterrows():
            days_left = int(row["_days"])
            label = "TODAY" if days_left == 0 else f"{days_left} day{'s' if days_left != 1 else ''}"
            st.warning(f"**{row['deliverable']}** — {label} | 👤 {row['assignee']} | Status: {row['status']}")
        st.markdown("")

    # ── 🟢 TOP 3 PRIORITIES ───────────────────────────────────────────
    st.markdown("### 🎯 Your Top 3 Priorities Today")
    in_progress = incomplete[incomplete["status"] == "In Progress"].head(3)
    if not in_progress.empty:
        for i, (_, row) in enumerate(in_progress.iterrows(), 1):
            st.success(f"**{i}. {row['deliverable']}** | 👤 {row['assignee']} | Due: {row['due_date']}")
    else:
        st.success("✅ No in-progress items — pick something from this week's list to start!")

    st.markdown("")

    # ── 🟢 QUICK WINS ─────────────────────────────────────────────────
    if not quick_wins.empty:
        st.markdown("### ⚡ Quick Wins — Easy Tasks to Knock Out")
        for _, row in quick_wins.iterrows():
            st.success(f"**{row['deliverable']}** | Due: {row['due_date']} | 👤 {row['assignee']}")

    st.markdown("---")

    # ── PROGRESS BAR ──────────────────────────────────────────────────
    total = len(df)
    complete = (df["status"] == "Complete").sum()
    pct = complete / total if total > 0 else 0
    color = "🔴" if pct < 0.3 else "🟡" if pct < 0.7 else "🟢"
    st.markdown(f"### {color} Overall Progress: {complete}/{total} deliverables complete")
    st.progress(pct)

else:
    st.info("No deliverables yet — add some in the Grant Tracker to see your dashboard!")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 2 — MEETING MINUTES SUMMARIZER
# ═══════════════════════════════════════════════════════════════════════
st.markdown("## 📋 Meeting Minutes Summarizer")
st.caption("Paste your meeting notes — Claude will extract what actually matters in ADHD-friendly format.")

MINUTES_SYSTEM = """You are an ADHD-friendly meeting summarizer for a grant project manager. 
Extract only what matters and format using traffic lights:
🔴 = urgent/blocked/overdue
🟡 = needs attention soon  
🟢 = on track/completed/decided

Keep every point to ONE sentence maximum. No walls of text. Bold the most critical item in each section."""

with st.form("minutes_form"):
    meeting_title = st.text_input("Meeting name", placeholder="e.g. Weekly Team Sync — March 26")
    minutes_text = st.text_area(
        "Paste your meeting notes here",
        height=250,
        placeholder="Paste raw meeting notes, transcript, or bullet points..."
    )
    submitted = st.form_submit_button("🧠 Summarize with Claude", type="primary")

if submitted and minutes_text.strip():
    with st.spinner("Claude is reading your minutes..."):
        prompt = f"""Meeting: {meeting_title}

MINUTES:
{minutes_text}

Extract and format ONLY:

## 🔴🟡🟢 KEY DECISIONS
Use traffic lights. One sentence each. Bold the most important.

## ✅ ACTION ITEMS
Format each as: 🔴/🟡/🟢 **[Owner]**: [Task] — Due: [date or ASAP]

## 🚧 BLOCKERS & RISKS  
Use 🔴 for blockers, 🟡 for risks. One sentence each.

## ❓ FOLLOW-UP QUESTIONS
Bullet list only. Keep it short.

## ⚡ THE ONE THING
In bold: the single most important thing that must happen before the next meeting.

Keep everything scannable. No paragraphs. ADHD-friendly only."""

        summary = call_claude(prompt, system=MINUTES_SYSTEM)

    st.markdown("---")
    st.markdown("### 📊 Summary")
    st.markdown(summary)

    # Save to notebook
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save to Notebook", type="primary"):
            DATA_DIR = "data"
            NOTES_FILE = os.path.join(DATA_DIR, "notebook.csv")
            os.makedirs(DATA_DIR, exist_ok=True)
            try:
                notes_df = pd.read_csv(NOTES_FILE) if os.path.exists(NOTES_FILE) else pd.DataFrame(columns=["id","type","title","content","action_items","date","project_tag"])
                new_id = int(notes_df["id"].max()) + 1 if not notes_df.empty else 1
                notes_df = pd.concat([notes_df, pd.DataFrame([{
                    "id": new_id, "type": "meeting",
                    "title": meeting_title or f"Meeting — {today}",
                    "content": summary, "action_items": "",
                    "date": str(today), "project_tag": ""
                }])], ignore_index=True)
                notes_df.to_csv(NOTES_FILE, index=False)
                st.success("✅ Saved to Notebook!")
            except Exception as e:
                st.error(f"Could not save: {e}")
    with col2:
        st.download_button(
            "⬇️ Download Summary",
            data=summary.encode("utf-8"),
            file_name=f"minutes_{today}.txt",
            mime="text/plain"
        )

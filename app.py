import streamlit as st
st.set_page_config(page_title="Grant Deliverable Tracker", page_icon="🎯", layout="wide")

import pandas as pd
from datetime import date, datetime
from auth import require_login, logout
from db import (get_db, load_deliverables, save_deliverable, delete_deliverable,
                next_deliverable_id, load_team, save_team_member, bulk_insert_deliverables)
from utils import status_color, budget_summary

# ── Auth ──────────────────────────────────────────────────────────────────────
require_login()

# ── DB ────────────────────────────────────────────────────────────────────────
db = get_db()
if db is None:
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🎯 Grant Tracker")
st.sidebar.caption(f"👤 {st.session_state.get('username', '')} · {st.session_state.get('role', '')}")

page = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "📋 Deliverables", "👥 Team", "💰 Budget", "📤 Reports"],
)
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sign out"):
    logout()
st.sidebar.caption("Grant Deliverable Tracker v2.0")

# ── Load data ─────────────────────────────────────────────────────────────────
df = load_deliverables(db)
team_df = load_team(db)
STATUS_OPTIONS = ["Not Started", "In Progress", "Under Review", "Complete", "Blocked"]

# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.title("📊 Dashboard")
    if df.empty:
        st.info("No deliverables yet. Head to **Deliverables** to add some!")
    else:
        total = len(df)
        complete = (df["status"] == "Complete").sum()
        in_progress = (df["status"] == "In Progress").sum()
        blocked = (df["status"] == "Blocked").sum()
        today = date.today()
        overdue = 0
        for _, row in df.iterrows():
            try:
                d = datetime.strptime(str(row["due_date"]), "%Y-%m-%d").date()
                if d < today and row["status"] != "Complete":
                    overdue += 1
            except Exception:
                pass
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Deliverables", total)
        c2.metric("Complete", complete, f"{round(complete/total*100)}%")
        c3.metric("In Progress", in_progress)
        c4.metric("Blocked", blocked)
        c5.metric("⚠️ Overdue", overdue)
        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Status Breakdown")
            status_counts = df["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            st.bar_chart(status_counts.set_index("Status"))
        with col_b:
            st.subheader("Upcoming Deadlines (next 30 days)")
            upcoming = []
            for _, row in df.iterrows():
                try:
                    d = datetime.strptime(str(row["due_date"]), "%Y-%m-%d").date()
                    delta = (d - today).days
                    if 0 <= delta <= 30 and row["status"] != "Complete":
                        upcoming.append({"Deliverable": row["deliverable"], "Assignee": row["assignee"], "Due": str(row["due_date"]), "Days Left": delta})
                except Exception:
                    pass
            if upcoming:
                st.dataframe(pd.DataFrame(upcoming).sort_values("Days Left"), use_container_width=True, hide_index=True)
            else:
                st.success("No deadlines in the next 30 days! 🎉")
        st.markdown("---")
        st.subheader("💰 Budget Snapshot")
        bsum = budget_summary(df)
        b1, b2, b3 = st.columns(3)
        b1.metric("Total Allocated", f"${bsum['allocated']:,.2f}")
        b2.metric("Total Spent", f"${bsum['spent']:,.2f}")
        b3.metric("Remaining", f"${bsum['remaining']:,.2f}")
        if bsum["allocated"] > 0:
            pct = bsum["spent"] / bsum["allocated"]
            st.progress(min(pct, 1.0), text=f"{pct:.0%} of budget used")

# ═════════════════════════════════════════════════════════════════════════════
# DELIVERABLES
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📋 Deliverables":
    st.title("📋 Deliverables")
    tab1, tab2 = st.tabs(["View & Edit", "Add New"])
    with tab1:
        if df.empty:
            st.info("No deliverables added yet.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_status = st.multiselect("Filter by Status", STATUS_OPTIONS, default=STATUS_OPTIONS)
            with col2:
                assignees = ["All"] + sorted(df["assignee"].dropna().unique().tolist())
                filter_assignee = st.selectbox("Filter by Assignee", assignees)
            with col3:
                milestones = ["All"] + sorted(df["milestone"].dropna().unique().tolist())
                filter_milestone = st.selectbox("Filter by Milestone", milestones)
            filtered = df[df["status"].isin(filter_status)]
            if filter_assignee != "All":
                filtered = filtered[filtered["assignee"] == filter_assignee]
            if filter_milestone != "All":
                filtered = filtered[filtered["milestone"] == filter_milestone]
            st.markdown(f"**{len(filtered)} deliverable(s) shown**")
            for _, row in filtered.iterrows():
                color = status_color(row["status"])
                with st.expander(f"{color} **{row['deliverable']}** — {row['status']} | Due: {row['due_date']}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Assignee:** {row['assignee']}")
                        st.write(f"**Milestone:** {row['milestone']}")
                        st.write(f"**Description:** {row['description']}")
                    with c2:
                        st.write(f"**Budget Allocated:** ${float(row['budget_allocated']):,.2f}")
                        st.write(f"**Budget Spent:** ${float(row['budget_spent']):,.2f}")
                        st.write(f"**Notes:** {row['notes']}")
                    with st.form(key=f"edit_{row['id']}"):
                        new_status = st.selectbox("Update Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(row["status"]))
                        new_spent = st.number_input("Update Budget Spent ($)", value=float(row["budget_spent"]), min_value=0.0)
                        new_notes = st.text_area("Update Notes", value=str(row["notes"]))
                        submitted = st.form_submit_button("💾 Save Changes")
                        if submitted:
                            updated = row.to_dict()
                            updated["status"] = new_status
                            updated["budget_spent"] = new_spent
                            updated["notes"] = new_notes
                            save_deliverable(db, updated)
                            st.success("Saved!")
                            st.rerun()
    with tab2:
        st.subheader("Add a New Deliverable")
        team_names = team_df["name"].tolist() if not team_df.empty else []
        with st.form("add_deliverable"):
            name = st.text_input("Deliverable Name *")
            description = st.text_area("Description")
            col1, col2 = st.columns(2)
            with col1:
                assignee = st.selectbox("Assignee", [""] + team_names) if team_names else st.text_input("Assignee")
                due_date = st.date_input("Due Date", value=date.today())
                status = st.selectbox("Status", STATUS_OPTIONS)
            with col2:
                milestone = st.text_input("Milestone / Aim")
                budget_alloc = st.number_input("Budget Allocated ($)", min_value=0.0, value=0.0)
                budget_spent = st.number_input("Budget Spent ($)", min_value=0.0, value=0.0)
            notes = st.text_area("Notes")
            if st.form_submit_button("➕ Add Deliverable"):
                if not name:
                    st.error("Deliverable name is required.")
                else:
                    new_record = {
                        "id": next_deliverable_id(db),
                        "deliverable": name, "description": description,
                        "assignee": assignee, "due_date": str(due_date),
                        "status": status, "budget_allocated": budget_alloc,
                        "budget_spent": budget_spent, "milestone": milestone, "notes": notes,
                    }
                    save_deliverable(db, new_record)
                    st.success(f"✅ '{name}' added!")
                    st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# TEAM
# ═════════════════════════════════════════════════════════════════════════════
elif page == "👥 Team":
    st.title("👥 Team Members")
    tab1, tab2 = st.tabs(["Team Roster", "Add Member"])
    with tab1:
        if team_df.empty:
            st.info("No team members added yet.")
        else:
            st.dataframe(team_df, use_container_width=True, hide_index=True)
            if not df.empty:
                st.markdown("---")
                st.subheader("Deliverables by Team Member")
                for member in team_df["name"]:
                    member_delivs = df[df["assignee"] == member]
                    if not member_delivs.empty:
                        with st.expander(f"📌 {member} ({len(member_delivs)} deliverable(s))"):
                            st.dataframe(member_delivs[["deliverable", "status", "due_date", "milestone"]], use_container_width=True, hide_index=True)
    with tab2:
        with st.form("add_member"):
            m_name = st.text_input("Full Name *")
            m_role = st.text_input("Role / Title")
            m_email = st.text_input("Email")
            if st.form_submit_button("➕ Add Team Member"):
                if not m_name:
                    st.error("Name is required.")
                else:
                    save_team_member(db, {"name": m_name, "role": m_role, "email": m_email})
                    st.success(f"✅ {m_name} added!")
                    st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# BUDGET
# ═════════════════════════════════════════════════════════════════════════════
elif page == "💰 Budget":
    st.title("💰 Budget Tracking")
    if df.empty:
        st.info("No deliverables to show budget for.")
    else:
        bsum = budget_summary(df)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Allocated", f"${bsum['allocated']:,.2f}")
        c2.metric("Total Spent", f"${bsum['spent']:,.2f}")
        c3.metric("Remaining", f"${bsum['remaining']:,.2f}")
        if bsum["allocated"] > 0:
            pct = bsum["spent"] / bsum["allocated"]
            color = "🔴" if pct > 0.9 else "🟡" if pct > 0.7 else "🟢"
            st.progress(min(pct, 1.0), text=f"{color} {pct:.0%} of total budget used")
        st.markdown("---")
        milestone_budget = df.groupby("milestone")[["budget_allocated", "budget_spent"]].sum().reset_index()
        milestone_budget.columns = ["Milestone", "Allocated ($)", "Spent ($)"]
        milestone_budget["Remaining ($)"] = milestone_budget["Allocated ($)"] - milestone_budget["Spent ($)"]
        st.subheader("Budget by Milestone")
        st.dataframe(milestone_budget, use_container_width=True, hide_index=True)
        st.markdown("---")
        budget_detail = df[["deliverable", "assignee", "status", "budget_allocated", "budget_spent"]].copy()
        budget_detail["remaining"] = budget_detail["budget_allocated"] - budget_detail["budget_spent"]
        budget_detail.columns = ["Deliverable", "Assignee", "Status", "Allocated ($)", "Spent ($)", "Remaining ($)"]
        st.subheader("Budget by Deliverable")
        st.dataframe(budget_detail, use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════════════════════
# REPORTS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📤 Reports":
    st.title("📤 Reports & Exports")
    if df.empty:
        st.info("No data to export yet.")
    else:
        total = len(df)
        complete = (df["status"] == "Complete").sum()
        pct = round(complete / total * 100, 1) if total > 0 else 0
        bsum = budget_summary(df)
        st.markdown(f"""
**Report Generated:** {date.today().strftime("%B %d, %Y")}
### Overall Progress
- **{complete} of {total} deliverables complete ({pct}%)**
### Budget Summary
- Allocated: **${bsum['allocated']:,.2f}** | Spent: **${bsum['spent']:,.2f}** | Remaining: **${bsum['remaining']:,.2f}**
""")
        for s in STATUS_OPTIONS:
            count = (df["status"] == s).sum()
            st.markdown(f"- {status_color(s)} **{s}**: {count}")
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Deliverables (CSV)", data=csv, file_name=f"grant_deliverables_{date.today()}.csv", mime="text/csv")
        with col2:
            summary_df = df.groupby("status").size().reset_index(name="count")
            summary_csv = summary_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Summary (CSV)", data=summary_csv, file_name=f"grant_summary_{date.today()}.csv", mime="text/csv")
        st.dataframe(df, use_container_width=True, hide_index=True)

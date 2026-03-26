from datetime import date, datetime
from typing import Optional
import pandas as pd

STATUS_EMOJI = {
    "Not Started": "⚪",
    "In Progress": "🔵",
    "Under Review": "🟡",
    "Complete": "🟢",
    "Blocked": "🔴",
}

def status_color(status: str) -> str:
    return STATUS_EMOJI.get(status, "⚫")

def days_until(due_date_str: str) -> Optional[int]:
    try:
        due = datetime.strptime(str(due_date_str), "%Y-%m-%d").date()
        return (due - date.today()).days
    except Exception:
        return None

def budget_summary(df: pd.DataFrame) -> dict:
    allocated = pd.to_numeric(df["budget_allocated"], errors="coerce").fillna(0).sum()
    spent = pd.to_numeric(df["budget_spent"], errors="coerce").fillna(0).sum()
<<<<<<< HEAD
    return {"allocated": allocated, "spent": spent, "remaining": allocated - spent}
=======
    return {"allocated": allocated, "spent": spent, "remaining": allocated - spent}
>>>>>>> e376fcf4af7a6e7d36e7140a096a16bb4061896d

"""data_manager.py — handles all CSV read/write operations."""

import os
import pandas as pd

DATA_DIR = "data"
DELIVERABLES_FILE = os.path.join(DATA_DIR, "deliverables.csv")
TEAM_FILE = os.path.join(DATA_DIR, "team.csv")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_data(filepath: str, schema: dict) -> pd.DataFrame:
    """Load a CSV file; return an empty DataFrame matching schema if not found."""
    _ensure_data_dir()
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath)
            # Fill any missing columns so the app never crashes on schema changes
            for col, series in schema.items():
                if col not in df.columns:
                    df[col] = series.dtype.type(0) if series.dtype != object else ""
            return df
        except Exception as e:
            print(f"Warning: could not load {filepath}: {e}")
    return pd.DataFrame(schema)


def save_data(df: pd.DataFrame, filepath: str):
    """Persist a DataFrame to CSV."""
    _ensure_data_dir()
    df.to_csv(filepath, index=False)

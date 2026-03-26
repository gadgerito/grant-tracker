# 🎯 Grant Deliverable Tracker

A Streamlit app to track grant deliverables, team assignments, budgets, and generate progress reports — all backed by simple CSV files.

---

## 📁 Project Structure

```
grant_tracker/
├── app.py              # Main Streamlit application
├── data_manager.py     # CSV load/save logic
├── utils.py            # Helper functions (status colors, budget math)
├── requirements.txt    # Python dependencies
├── .gitignore
├── data/               # Auto-created at runtime
│   ├── deliverables.csv
│   └── team.csv
└── README.md
```

---

## 🚀 Setup & Run

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/grant-tracker.git
cd grant-tracker
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## 🗂 Features

| Page | What it does |
|------|-------------|
| **Dashboard** | KPI cards, status breakdown, upcoming deadlines, budget snapshot |
| **Deliverables** | Add, filter, and inline-edit all grant deliverables |
| **Team** | Manage team roster; see deliverables per person |
| **Budget** | Track allocated vs. spent by deliverable and milestone |
| **Reports** | Exportable progress summary and full CSV downloads |

---

## 💾 Data Storage

All data lives in the `data/` folder as CSV files — no database needed.

| File | Contents |
|------|----------|
| `data/deliverables.csv` | All deliverable records |
| `data/team.csv` | Team member roster |

> ⚠️ **Do not commit your `data/` folder** if it contains sensitive grant info. It is listed in `.gitignore` by default.

---

## 🔧 Customization Tips

- **Add new fields**: Update the schema dict in `data_manager.py` and add the field to the form in `app.py`.
- **Change statuses**: Edit `STATUS_OPTIONS` in `app.py` and `STATUS_EMOJI` in `utils.py`.
- **Deploy to Streamlit Cloud**: Push to GitHub, connect at [share.streamlit.io](https://share.streamlit.io), set main file to `app.py`.

---

## ☁️ Deploying to Streamlit Community Cloud

1. Push this repo to GitHub (keep `data/` in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Select your repo, branch `main`, main file `app.py`
4. Click **Deploy**

> Note: On Streamlit Cloud, the `data/` folder resets on each redeployment. For persistent storage, swap CSV files for Google Sheets or Supabase.

---

## 📝 License

MIT

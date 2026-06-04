# 🚀 Quick Start (2 Minutes)

## Prerequisites
- Python 3.8+ installed
- Terminal/Command Prompt

## Installation

### Option 1: Automated Setup (Recommended)

**Mac/Linux:**
```bash
./setup.sh
```

**Windows:**
```
setup.bat
```

### Option 2: Manual Setup

```bash
# Install backend dependencies
cd backend
pip install -r requirements.txt
python -c "import nltk; nltk.download('vader_lexicon')"
cd ..
```

## Running the Application

### Terminal 1 — Backend
```bash
cd backend
python main.py
```

Wait for: `"Bootstrap complete"` message

### Terminal 2 — Frontend
```bash
cd frontend
python -m http.server 3000
```

### Open Browser
```
http://localhost:3000
```

## First Run Notes

**⏱️ Timing:**
- First run: 15-30 seconds (downloading BERT model ~440MB)
- Subsequent runs: 5-10 seconds

**🔄 What's Happening:**
- Backend generates 500 sample posts
- Runs BERT sentiment analysis
- Fits topic model (NMF)
- Builds trend forecasts
- Scans for crisis signals

**📊 What You'll See:**
- Dashboard with sentiment metrics
- 90-day trend chart + 14-day forecast
- 8 auto-discovered topic clusters
- Crisis detection alerts
- Competitor intelligence
- Live text analyzer

## Troubleshooting

**Backend won't start?**
- Check Python version: `python --version` (need 3.8+)
- Try: `python3 main.py` instead of `python main.py`

**Model download slow?**
- First-time download of RoBERTa model (~440MB)
- Subsequent runs load from cache (fast)

**Frontend shows "demo data"?**
- Backend isn't running — start it first
- Or backend is still bootstrapping — wait 30 seconds
- Demo mode still works — shows synthetic data

**Port 3000 already in use?**
```bash
python -m http.server 8080  # Use different port
```

Then open: `http://localhost:8080`

## What to Explore

1. **Dashboard** — Overall sentiment, volume, crisis alerts
2. **Trends** — Time series + forecast + anomaly detection
3. **Topics** — Click topic chips to see keywords and examples
4. **Crisis Radar** — View detected crisis posts and severity
5. **Competitors** — Sentiment comparison and opportunities
6. **Live Analyzer** — Paste any text for real-time analysis

## Demo vs. Real Mode

**Demo Mode** (backend offline):
- Instant load with pre-generated data
- All features work except live analysis

**Real Mode** (backend running):
- NLP pipeline processes actual corpus
- Live text analysis via API
- Model performance metrics shown

## Need Help?

📖 **Full docs:** See `README.md`  
📝 **Case study:** See `docs/CASE_STUDY.md`  
🐛 **Issues:** Check Python version, pip dependencies

---

**Estimated time:** 2 minutes setup + 30 seconds first run = **2.5 minutes total**

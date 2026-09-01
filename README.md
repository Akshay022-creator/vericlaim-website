# VeriClaim — 7-Provider Real-Time News Cross-Verification Engine

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![FastAPI/HTTP](https://img.shields.io/badge/API-Zero--Dependency%20REST-emerald.svg)](https://localhost:8000)
[![Providers](https://img.shields.io/badge/News%20Wires-7%20Live%20APIs-indigo.svg)](https://localhost:8000)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**VeriClaim** is an evidence-based, explainable news cross-verification engine. It simultaneously cross-references breaking headlines, viral claims, and statistics against **7 live global news wire APIs** using concurrent multithreading, hybrid TF-IDF semantic vector similarity, and quantitative fact-conflict auditing to compute a deterministic **Corroboration Score (0–100)**.

---

## ⚡ 7 Live Global News Providers Active

1. **The Guardian Open Platform** — Quality investigative & world journalism
2. **NewsAPI.org** — Global news wire aggregator
3. **Currents API** — High-speed real-time news stream
4. **Mediastack API** — Worldwide media data feed
5. **GNews.io** — Fast breaking news search
6. **NewsData.io** — Regional and international news coverage
7. **WorldNewsAPI.com** — Multilingual worldwide news wire
8. **Local Verified Dataset** — Zero-dependency offline archive fallback

---

## 🚀 Key Features

- **Concurrent Multithreaded Ingestion (`ThreadPoolExecutor`)**: Queries all 7 global news providers simultaneously in parallel threads, delivering comprehensive cross-verification results in sub-second to ~1–2s latency.
- **Explainable Corroboration Scoring (0–100)**:
  - *Top Content Similarity* (up to 45 pts)
  - *Multi-Source Coverage Breadth* (up to 30 pts)
  - *Reporting Depth & Consistency* (up to 25 pts)
  - *Fact Consistency Modifier* (+10 bonus for verified facts, -35 penalty for numeric discrepancies)
- **Claim vs. Reality Fact-Auditing Matrix**: Audits exact currency amounts ($/€/£), percentages, quantities, and dates, pinpointing numeric distortions (e.g. claiming *$50 billion* when wires report *$5 billion*).
- **Modern Glassmorphic UI**:
  - Dark / Light mode toggle (persisted in `localStorage`).
  - Animated live breaking news ticker tape.
  - Floating glowing particle mesh background.
  - Animated SVG circular score meter with smooth count-up animation.
  - Interactive provider filtering chips.
  - Publisher similarity comparison bar chart.
  - Verification history drawer with 1-click restore.
  - One-click export suite (Copy Markdown, Download `.md`, Print / PDF).

---

## 🛠️ Quick Start Locally

### 1. Clone & Setup
```bash
git clone https://github.com/your-username/vericlaim-website.git
cd vericlaim-website
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys
Copy the example environment file and add your keys (or use the pre-configured active keys in `.env`):
```bash
cp .env.example .env
```

### 4. Launch the Web Server
```bash
python server.py
# or
python web/server.py
```
Open **`http://localhost:8000`** in your browser.

---

## 🌐 How to Push to GitHub

Follow these steps to initialize Git and push this repository to GitHub:

### Step 1: Initialize Git & Commit
Open your terminal in the `vericlaim-website` directory:
```bash
# Initialize git repository
git init

# Add all files (respecting .gitignore)
git add .

# Commit changes
git commit -m "Initial commit: VeriClaim 7-Provider News Verification Engine"
```

### Step 2: Create a New GitHub Repository
1. Go to [GitHub New Repository](https://github.com/new).
2. Name the repository (e.g., `vericlaim-website` or `vericlaim`).
3. Leave it **Public** or **Private**, and **do not** check "Initialize with README".
4. Click **Create repository**.

### Step 3: Link & Push
```bash
# Rename branch to main
git branch -M main

# Add your GitHub remote URL
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/vericlaim-website.git

# Push to GitHub
git push -u origin main
```

---

## 🚀 Where & How to Deploy (Free & Instant)

Here are the top 3 recommended platforms to host VeriClaim live on the web:

### Option 1: Render.com (Recommended — 100% Free Web Service)
1. Sign up at [Render.com](https://render.com).
2. Click **New +** ➔ **Web Service**.
3. Connect your GitHub repository `vericlaim-website`.
4. Configure settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py`
5. Under **Environment Variables**, add the API keys from your `.env` file (`NEWS_API_KEY`, `GUARDIAN_API_KEY`, `CURRENTS_API_KEY`, `MEDIASTACK_API_KEY`, etc.).
6. Click **Deploy Web Service**. You will receive a live URL like `https://vericlaim.onrender.com`!

### Option 2: Railway.app
1. Go to [Railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project** ➔ **Deploy from GitHub repo**.
3. Select `vericlaim-website`.
4. Under **Variables**, add your `.env` keys.
5. Railway automatically detects `Procfile` and launches the web app.

### Option 3: Hugging Face Spaces / PythonAnywhere
- **Hugging Face Spaces**: Create a new Space with SDK **Docker** or **Gradio/Streamlit**, upload files, and deploy with free GPU/CPU tiers.
- **PythonAnywhere**: Upload repository to a free PythonAnywhere Web App tab and run on WSGI/HTTP server.

---

## 📡 REST API Endpoints

- `GET /api/health` — Returns system status and active provider count.
- `GET /api/providers` — Returns telemetry and metadata for all 7 news providers.
- `GET /api/trending` — Returns curated benchmark claims.
- `POST /api/verify` — Cross-verifies a headline:
  ```json
  // Request
  {
    "headline": "Nvidia reports record revenue growth in AI data center chips"
  }
  
  // Response
  {
    "headline": "...",
    "score": 87,
    "category": "Strongly Corroborated",
    "explanation": "...",
    "distinct_sources": ["The Guardian", "GNews", "NewsData", "..."],
    "articles": [...],
    "fact_check": {
      "conflicts_found": false,
      "audit_matrix": [...]
    },
    "telemetry": {
      "query_time_ms": 780,
      "providers_responding": 6
    }
  }
  ```

---

## 📄 License
MIT License. Open source and free to customize.

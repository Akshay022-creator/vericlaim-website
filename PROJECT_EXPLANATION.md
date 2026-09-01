# 📖 VeriClaim — Simple Code & Project Guide

> **How to explain this project to anyone (Examiners, Interviewers, or Friends) in plain English without needing complex programming terms.**

---

## ⚡ The 30-Second Elevator Pitch

> *"VeriClaim is a real-time news verification web platform. When a user enters a headline, article URL, or speaks a claim, our system searches **7 global news wire services** (like The Guardian, NewsAPI, Currents, and Reuters sources) simultaneously. It extracts key names, dates, and amounts, checks if the story is confirmed across independent newsrooms, catches distorted numbers, and generates an instant **Truth Score (0 to 100)** with a full source breakdown."*

---

## 🧩 The 5 Python Modules (How the Code Works)

Our backend is split into **5 simple, focused Python files**. Here is what each one does:

```
User Claim ("Nvidia AI Revenue")
         │
         ▼
[1. keyword_extractor.py] ──► Extracts "Nvidia", "AI", "Revenue"
         │
         ▼
[2. news_fetcher.py]      ──► Queries 7 Global News APIs at once
         │
         ▼
[3. similarity_engine.py] ──► Compares claim vs news articles (Checks entities & roles)
         │
         ▼
[4. fact_checker.py]      ──► Checks if numbers/percentages match ($50B vs $5B)
         │
         ▼
[5. scorer.py]            ──► Calculates final 0–100 Truth Score & explanation
         │
         ▼
[server.py] ───────────────► Sends results back to the website
```

---

### 1. `modules/keyword_extractor.py` — *The Notepad*
- **What it does**: Like a journalist highlighting important words on a notepad.
- **How it works**:
  - Removes common filler words (*"the"*, *"is"*, *"a"*, *"in"*).
  - Pulls out **named people/companies** (*"Modi"*, *"Nvidia"*, *"Google"*).
  - Pulls out **numbers/currency** (*"$50 billion"*, *"25 bps"*).
  - Pulls out **dates** (*"2026"*, *"October"*).

---

### 2. `modules/news_fetcher.py` — *The News Searcher*
- **What it does**: Connects to 7 live global news wire services.
- **The 7 Providers**:
  1. The Guardian Open Platform
  2. NewsAPI.org
  3. Currents API
  4. Mediastack API
  5. GNews.io
  6. NewsData.io
  7. WorldNewsAPI.com
- **How it works**:
  - Uses Python's `ThreadPoolExecutor` to send requests to all 7 news services **at the exact same time** (in parallel).
  - Results come back in under **2 seconds**.

---

### 3. `modules/similarity_engine.py` — *The Story Matcher*
- **What it does**: Measures how closely the news reporting matches what the user claimed.
- **Smart Guards**:
  - **Entity Guard**: For `"Elon Musk buys Google"`, the article must mention *both* Elon Musk AND Google. (Articles only about SpaceX get a score of `0.0`).
  - **Role & Office Check**: For `"Modi is PM of Pakistan"`, it checks who the article says is Pakistan's PM (*Shehbaz Sharif*) and confirms Modi is India's PM, immediately flagging the contradiction (`0/100 False`).
  - **Debunk Detection**: If Reuters or BBC published a *"Fact-Check: False claim..."* article, it detects the debunk and marks the claim as False.

---

### 4. `modules/fact_checker.py` — *The Numbers Auditor*
- **What it does**: Checks whether numbers, prices, and percentages in the claim match the reported facts.
- **How it works**:
  - Compares currency to currency (*$50 billion* vs *$5 billion* -> flags -35 pt penalty for exaggerated claims).
  - Avoids comparing unrelated numbers (never compares interest rates against economist survey counts).

---

### 5. `modules/scorer.py` — *The Score Calculator*
- **What it does**: Combines the findings into an easy-to-understand **0 to 100 Truth Score**.
- **Simple 3-Part Formula**:
  1. **Story Match**: Up to **45 points** (how closely the news topic matches).
  2. **Multiple Sources**: Up to **35 points** (more independent news outlets covering it = higher score).
  3. **Consistency**: Up to **20 points** (how consistent the reporting is).
  4. **Fact Adjustment**: **+10 points** if numbers match, **-35 points** if numbers are distorted.
- **Verdict Tiers**:
  - **75 – 100**: 🟢 **Verified True**
  - **50 – 74**: 🟡 **Partially True**
  - **25 – 49**: 🟠 **Unverified**
  - **0 – 24**: 🔴 **False / Misleading**

---

### 6. `server.py` — *The Web Server*
- **What it does**: Runs the web server (`ThreadingHTTPServer`) that serves `index.html` and responds to search requests from the browser at `http://localhost:8000`.

---

## 🎤 Top 5 Questions You Might Be Asked & Simple Answers

### Q1: *"How does it know if a claim is fake?"*
> **Answer**: *"It searches 7 live global news agencies. If zero news outlets report it, or if articles about the topic explicitly call it a rumor/debunk, the claim receives a 0/100 False score."*

### Q2: *"How does it avoid false positives like 'Elon Musk buys Google'?"*
> **Answer**: *"We built a Subject-Object Entity Gate. If a claim mentions two distinct entities like 'Elon Musk' and 'Google', the news article must mention both. Articles that only talk about Elon Musk's SpaceX rockets without mentioning Google get a 0.0 match."*

### Q3: *"How does it handle tricky claims like 'Modi is PM of Pakistan'?"*
> **Answer**: *"We have a Role-Attribution Checker. It reads the news text and sees that Pakistan's Prime Minister is identified as Shehbaz Sharif, while Modi is identified as India's Prime Minister. It detects the contradiction and rates the claim 0/100 False."*

### Q4: *"Why do you query 7 different APIs?"*
> **Answer**: *"To avoid single-source bias. If only one outlet reports something, it gets moderate confidence. When 3 or 4 independent global newsrooms (Reuters, Guardian, BBC) all confirm it, the score reaches high confidence."*

### Q5: *"Is the server fast?"*
> **Answer**: *"Yes. We use Python multithreading (`ThreadPoolExecutor`) so all 7 news services are searched in parallel at the same time, returning complete verification in 1 to 2 seconds."*

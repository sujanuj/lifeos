#  LifeOS — Your Personal AI Operating System

> An AI-powered personal life management system that acts as your second brain — tracking goals, habits, mood, and delivering personalized daily briefings powered by GPT-4o.

**Live Demo:** [lifeos-sujan.onrender.com](https://lifeos-sujan.onrender.com)

![LifeOS Dashboard](https://img.shields.io/badge/Status-Live-brightgreen) ![Python](https://img.shields.io/badge/Python-3.10-blue) ![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey) ![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-orange)

---

##  Features

| Feature | Description |
|---|---|
|  **AI Morning Briefing** | Personalized daily briefing with priorities, mood insights, and motivation |
|  **ML Mood Analytics** | Pattern detection across days — finds your best/worst productivity days |
|  **Goal Tracker** | Set goals with progress bars, categories, deadlines |
|  **Habit Streaks** | Daily habit tracking with fire streaks |
|  **Mood Logger** | Daily mood + energy logging with trend charts |
|  **AI Life Coach** | GPT-powered coach that remembers your goals and mood history |
|  **Voice Input** | Speak to your AI coach using Web Speech API |
|  **Tech News Feed** | Personalized tech news relevant to your career |
|  **XP & Level System** | Gamified progression — earn XP for every action |
|  **Daily Email Briefing** | Automated morning briefing delivered to your inbox at 8 AM |
|  **PWA** | Installable on phone/desktop — works offline |
|  **JWT Auth** | Secure login with token-based authentication |

---

##  Tech Stack

**Backend**
- Python 3.10 + Flask
- SQLite via SQLAlchemy ORM
- OpenAI GPT-4o-mini
- Flask-JWT-Extended (auth)
- Flask-Mail + APScheduler (email automation)
- Python `statistics` module (ML pattern detection)

**Frontend**
- Vanilla HTML/CSS/JavaScript (zero framework)
- Chart.js (mood/energy trend charts)
- Web Speech API (voice input)
- PWA with Service Worker (offline + installable)

**Deployment**
- Render (backend + frontend)
- GitHub (auto-deploy on push)

---

##  Project Structure

```
lifeos/
└── backend/
    ├── app.py           # Flask backend — all routes, AI, email scheduler
    ├── index.html       # Full frontend (single file)
    ├── manifest.json    # PWA manifest
    ├── sw.js            # Service Worker (offline support)
    ├── requirements.txt
    ├── runtime.txt
    └── .env             # Environment variables (not committed)
```

---

##  Local Setup

### Prerequisites
- Python 3.10+
- OpenAI API key
- Gmail account with App Password

### Steps

```bash
# 1. Clone
git clone https://github.com/sujanuj/lifeos.git
cd lifeos/backend

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env
cat > .env << EOF
OPENAI_API_KEY=sk-your-key-here
JWT_SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///lifeos.db
MAIL_EMAIL=your@gmail.com
MAIL_PASSWORD=your-app-password
NEWS_API_KEY=your-newsapi-key
EOF

# 5. Run
python app.py
```

Open **http://localhost:5001**

---

##  Deployment (Render)

| Setting | Value |
|---|---|
| **Root Directory** | `backend` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |

**Environment Variables to add:**
- `OPENAI_API_KEY`
- `JWT_SECRET_KEY`
- `MAIL_EMAIL`
- `MAIL_PASSWORD`
- `NEWS_API_KEY` (optional)

---

##  API Endpoints

| Method | Route | Description |
|---|---|---|
| POST | `/register` | Register with email |
| POST | `/login` | Login |
| GET/PUT | `/profile` | Get/update profile |
| POST | `/mood` | Log mood (+10 XP) |
| GET | `/mood` | Get mood history |
| GET | `/mood/insights` | ML pattern analysis |
| GET/POST | `/goals` | Get/add goals |
| PUT/DELETE | `/goals/:id` | Update/delete goal |
| GET/POST | `/habits` | Get/add habits |
| POST | `/habits/:id/check` | Check habit (+15 XP) |
| GET | `/briefing` | AI morning briefing |
| POST | `/chat` | AI coach chat |
| GET | `/news` | Career-relevant news |
| GET | `/stats` | Dashboard stats |
| POST | `/send-test-email` | Send test briefing email |

---

##  XP System

| Action | XP Gained |
|---|---|
| Log mood | +10 XP |
| Add habit | +15 XP |
| Check habit daily | +15 XP |
| 7-day streak | +25 XP bonus |
| Add goal | +20 XP |
| Complete goal | +100 XP  |

Each level requires `level × 100 XP` to advance.

---

##  Roadmap

- [ ] GitHub integration (track coding streaks)
- [ ] Weather-based schedule adjustment
- [ ] Multi-user leaderboard
- [ ] Mobile push notifications
- [ ] LinkedIn network growth tracker
- [ ] Spotify mood-based playlist integration

---

##  Author

**Sujan Uppalli Jayadevappa**
M.S. Software Engineering @ Arizona State University
[LinkedIn](https://linkedin.com/in/sujan-uppalli-jayadevappa-504b721b9/) • [GitHub](https://github.com/sujanuj) • supalli@asu.edu

---

##  License

MIT — feel free to fork and build on this!
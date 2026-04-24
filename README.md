# LifeOS — Personal AI Operating System

A full-stack AI-powered life management application built as a personal project during my M.S. in Software Engineering at Arizona State University. The system integrates large language models, behavioral pattern analysis, and gamification to help users manage goals, habits, mood, and daily productivity through a unified dashboard.

**Live Application:** [https://lifeos-uysl.onrender.com](https://lifeos-uysl.onrender.com)  
**GitHub Repository:** [https://github.com/sujanuj/lifeos](https://github.com/sujanuj/lifeos)

---

## Motivation

During my graduate coursework in Statistical Machine Learning and Data Processing at Scale, I became interested in applying ML techniques to personal behavioral data. Most productivity tools offer isolated features — habit trackers, mood journals, or goal planners — but none synthesize behavioral patterns across these dimensions to generate personalized, context-aware guidance. LifeOS is my attempt to build that unified system.

---

## System Overview

LifeOS functions as a personal operating system for daily life. At its core, it collects structured behavioral data (mood scores, energy levels, goal progress, habit completions), analyzes patterns using statistical methods, and uses a GPT-4o-mini prompt pipeline to generate personalized morning briefings, coaching responses, and productivity recommendations that adapt to the user's behavioral history.

---

## Features

**AI-Powered Morning Briefing**  
Each morning, the system generates a fully personalized briefing by injecting the user's goal progress, habit streaks, 7-day mood averages, and stored memory fragments into a structured GPT-4o-mini prompt. The output includes prioritized tasks, mood insights, motivational content, and a daily challenge — all tailored to the individual user.

**Mood and Energy Tracking with ML Pattern Analysis**  
Users log daily mood and energy scores on a 1–10 scale. The backend computes day-of-week averages, overall trend direction, and Pearson correlation between mood and energy using Python's statistics module. After 3 or more days of data, the system surfaces insights such as best and worst productivity days and whether mood improvements correlate with energy levels.

**Goal Management with Progress Tracking**  
Users set goals with categories (career, health, learning, finance) and optional deadlines. Progress is tracked via a slider interface with debounced real-time updates to the backend. Goal completion awards 100 XP and feeds into the gamification layer.

**Habit Tracking with Streak Gamification**  
Daily habit check-ins maintain streak counters. The XP reward system provides +15 XP per daily check-in and a +25 XP bonus every 7 consecutive days, creating behavioral reinforcement loops grounded in habit formation principles.

**AI Life Coach with Persistent Memory**  
The coaching chat interface uses a context-injection approach: each API request assembles a dynamic system prompt from the user's active goals, recent mood scores, and stored conversation memories. Significant user statements are persisted to a Memory table and retrieved on subsequent sessions, giving the model conversational continuity without fine-tuning.

**Voice Input Interface**  
Integrated Web Speech API (webkitSpeechRecognition) allows users to speak queries directly to the AI coach. Interim transcription results stream into the input field in real-time, and the final transcript auto-submits on recognition completion.

**Automated Daily Email Briefing**  
APScheduler runs a background cron job at 8:00 AM daily. The job queries all users with email briefings enabled, generates personalized HTML email content via the same GPT pipeline, and dispatches via Flask-Mail over Gmail SMTP. The email includes goal summaries, habit streaks, and the full AI briefing formatted as a responsive HTML newsletter.

**Progressive Web App**  
A Web App Manifest and Service Worker enable installation on desktop and mobile devices. The service worker implements a cache-first strategy for static assets and network-first for API calls, providing basic offline functionality and a native app-like experience.

**XP and Level System**  
Every meaningful user interaction earns XP: logging mood (+10), adding habits (+15), checking habits daily (+15 or +25 on weekly milestones), adding goals (+20), completing goals (+100). The leveling formula uses level × 100 XP thresholds with automatic level-up detection and popup feedback.

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (SPA)                    │
│         Vanilla JS + Chart.js + Web Speech API       │
│              PWA: manifest.json + sw.js              │
└────────────────────┬────────────────────────────────┘
                     │ HTTP/REST (JWT Bearer Token)
┌────────────────────▼────────────────────────────────┐
│                Flask REST API (Python)               │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  Auth Layer │  │ AI Pipeline  │  │  Scheduler │ │
│  │ JWT Extended│  │ GPT-4o-mini  │  │ APScheduler│ │
│  └─────────────┘  └──────────────┘  └────────────┘ │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │           SQLAlchemy ORM + SQLite            │   │
│  │  User | MoodLog | Goal | Habit | Memory      │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
   OpenAI API               Gmail SMTP
   (GPT-4o-mini)            (Flask-Mail)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10, Flask 3.x |
| ORM | Flask-SQLAlchemy, SQLite |
| Authentication | Flask-JWT-Extended |
| AI | OpenAI Python SDK, GPT-4o-mini |
| Email Automation | Flask-Mail, APScheduler, Gmail SMTP |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Data Visualization | Chart.js |
| Voice Interface | Web Speech API |
| PWA | Web App Manifest, Service Worker Cache API |
| Deployment | Render, GitHub |

---

## Data Models

```python
User       # id, username, password, name, career_field, xp, level, email, email_briefing
MoodLog    # id, user_id, mood(1-10), energy(1-10), note, date, day_of_week
Goal       # id, user_id, title, category, progress(0-100), deadline, completed
Habit      # id, user_id, title, streak, last_checked, category
Memory     # id, user_id, content, memory_type, created_at
```

---

## API Reference

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/register` | Create account | No |
| POST | `/login` | Authenticate user | No |
| GET/PUT | `/profile` | Get or update profile | Yes |
| POST | `/mood` | Log daily mood (+10 XP) | Yes |
| GET | `/mood` | Retrieve mood history | Yes |
| GET | `/mood/insights` | ML pattern analysis | Yes |
| GET/POST | `/goals` | Get all / create goal | Yes |
| PUT/DELETE | `/goals/:id` | Update or delete goal | Yes |
| GET/POST | `/habits` | Get all / create habit | Yes |
| POST | `/habits/:id/check` | Daily check-in (+15/25 XP) | Yes |
| GET | `/briefing` | Generate AI morning briefing | Yes |
| POST | `/chat` | AI coach conversation | Yes |
| GET | `/news` | Career-relevant news feed | Yes |
| GET | `/stats` | Dashboard statistics | Yes |
| POST | `/send-test-email` | Trigger test briefing email | Yes |

---

## Local Development Setup

Prerequisites: Python 3.10+, pip, OpenAI API key, Gmail account with App Password enabled.

```bash
# Clone the repository
git clone https://github.com/sujanuj/lifeos.git
cd lifeos/backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
nano .env
```

Add the following to `.env`:

```
OPENAI_API_KEY=sk-your-openai-key
JWT_SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///lifeos.db
MAIL_EMAIL=your@gmail.com
MAIL_PASSWORD=your-16-char-app-password
NEWS_API_KEY=your-newsapi-key-optional
```

```bash
# Run the development server
python app.py
# Application available at http://localhost:5001
```

---

## Deployment

The application is deployed on Render as a Web Service connected to the GitHub repository with automatic deploys on push to main.

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |
| Python Version | 3.10 |

Required environment variables: `OPENAI_API_KEY`, `JWT_SECRET_KEY`, `MAIL_EMAIL`, `MAIL_PASSWORD`

The free tier on Render spins down after 15 minutes of inactivity. Setting up a free monitor on UptimeRobot to ping the service every 5 minutes keeps the instance alive continuously.

---

## Limitations and Future Work

The current implementation uses SQLite, which is appropriate for single-user personal deployment but would not scale to concurrent production workloads. A migration to PostgreSQL is straightforward given the SQLAlchemy abstraction.

Password storage currently uses plaintext and would require bcrypt hashing before any public multi-user release. The JWT implementation also lacks refresh token rotation.

Planned extensions include GitHub API integration to track coding streaks from commit history, a vector embedding memory system using ChromaDB to enable semantic retrieval of past conversations, weather API integration to adjust recommendations based on environmental conditions, and a LinkedIn network growth tracker.

---

## Project Structure

```
lifeos/
├── backend/
│   ├── app.py            # Flask application, all routes, models, AI logic
│   ├── index.html        # Single-page frontend
│   ├── manifest.json     # PWA manifest
│   ├── sw.js             # Service Worker
│   ├── requirements.txt  # Python dependencies
│   └── runtime.txt       # Python version
├── .gitignore
└── README.md
```

---

## Author

**Sujan Uppalli Jayadevappa**  
M.S. Software Engineering — Data Science Specialization  
Arizona State University, Tempe, AZ  
Expected Graduation: December 2026  

[LinkedIn](https://www.linkedin.com/in/sujan-uppalli-jayadevappa-504b721b9/) • [GitHub](https://github.com/sujanuj) • supalli@asu.edu

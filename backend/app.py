from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_mail import Mail, Message
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import os, json, requests, statistics, atexit

load_dotenv()

app = Flask(__name__)
CORS(app, origins="*")

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "lifeos-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///lifeos.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_EMAIL', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_EMAIL', '')

db = SQLAlchemy(app)
jwt = JWTManager(app)
mail = Mail(app)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# ============ MODELS ============

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    career_field = db.Column(db.String(100))
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    email = db.Column(db.String(100))
    email_briefing = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    mood = db.Column(db.Integer)
    energy = db.Column(db.Integer)
    note = db.Column(db.String(500))
    date = db.Column(db.String(20))
    day_of_week = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(200))
    category = db.Column(db.String(50))
    progress = db.Column(db.Integer, default=0)
    deadline = db.Column(db.String(20))
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(200))
    streak = db.Column(db.Integer, default=0)
    last_checked = db.Column(db.String(20))
    category = db.Column(db.String(50))

class Memory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text)
    memory_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ============ XP HELPER ============

def add_xp(user, amount, reason=""):
    user.xp = (user.xp or 0) + amount
    xp_needed = user.level * 100
    leveled_up = False
    while user.xp >= xp_needed:
        user.xp -= xp_needed
        user.level += 1
        xp_needed = user.level * 100
        leveled_up = True
    db.session.commit()
    return {"xp_gained": amount, "total_xp": user.xp, "level": user.level, "leveled_up": leveled_up}

# ============ EMAIL BRIEFING HELPER ============

def generate_briefing_for_user(user):
    goals = Goal.query.filter_by(user_id=user.id, completed=False).all()
    habits = Habit.query.filter_by(user_id=user.id).all()
    mood_logs = MoodLog.query.filter_by(user_id=user.id).order_by(MoodLog.created_at.desc()).limit(7).all()
    today = datetime.utcnow().strftime("%Y-%m-%d")

    avg_mood = round(sum(m.mood for m in mood_logs) / len(mood_logs), 1) if mood_logs else "unknown"
    goals_summary = "\n".join([f"- {g.title} ({g.category}): {g.progress}% done" for g in goals]) or "No active goals"
    habits_summary = "\n".join([f"- {h.title}: {h.streak} day streak" for h in habits]) or "No habits"

    prompt = f"""You are LifeOS for {user.name}. Today is {today}. Career: {user.career_field}. Level: {user.level}.
Avg mood: {avg_mood}/10. Goals: {goals_summary}. Habits: {habits_summary}.
Return STRICT JSON only:
{{"greeting":"...","mood_insight":"...","top_priorities":["...","...","..."],"motivation":"...","focus_tip":"...","daily_challenge":"..."}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
    )
    text = response.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
    return json.loads(text)

def send_daily_briefings():
    with app.app_context():
        users = User.query.filter_by(email_briefing=True).all()
        for user in users:
            if not user.email:
                continue
            try:
                briefing = generate_briefing_for_user(user)
                goals = Goal.query.filter_by(user_id=user.id, completed=False).all()
                habits = Habit.query.filter_by(user_id=user.id).all()
                today = datetime.utcnow().strftime("%A, %B %d, %Y")

                html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body{{font-family:'Segoe UI',sans-serif;background:#0a0a12;color:#e8e8f0;margin:0;padding:0}}
  .wrap{{max-width:600px;margin:0 auto;padding:32px 24px}}
  .header{{background:linear-gradient(135deg,#7c6cfc,#fc6c8f);border-radius:16px;padding:28px;margin-bottom:24px;text-align:center}}
  .header h1{{font-size:28px;margin:0 0 4px;color:white}}
  .header p{{margin:0;opacity:0.8;color:white;font-size:14px}}
  .card{{background:#13131f;border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:20px;margin-bottom:16px}}
  .card h3{{font-size:12px;text-transform:uppercase;letter-spacing:1.5px;color:#5a5a7a;margin:0 0 12px}}
  .greeting{{font-size:20px;font-weight:600;line-height:1.4;margin-bottom:8px}}
  .insight{{font-size:14px;color:#8888aa;line-height:1.6}}
  .priority{{display:flex;align-items:center;gap:10px;padding:10px;background:rgba(255,255,255,0.03);border-radius:8px;margin-bottom:8px;font-size:14px}}
  .num{{width:22px;height:22px;background:#7c6cfc;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:white;flex-shrink:0;text-align:center;line-height:22px}}
  .insight-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}}
  .insight-box{{background:rgba(255,255,255,0.03);border-radius:10px;padding:12px}}
  .insight-label{{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#5a5a7a;margin-bottom:6px}}
  .insight-text{{font-size:13px;line-height:1.5;color:#e8e8f0}}
  .goal-item{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:13px}}
  .badge{{padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600}}
  .footer{{text-align:center;font-size:12px;color:#5a5a7a;margin-top:24px}}
  .footer a{{color:#7c6cfc;text-decoration:none}}
  .level-badge{{display:inline-block;background:rgba(252,212,108,0.15);border:1px solid rgba(252,212,108,0.3);color:#fcd46c;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;margin-top:8px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>🧠 LifeOS Morning Briefing</h1>
    <p>{today}</p>
    <div class="level-badge">⚡ Level {user.level} • {user.xp} XP</div>
  </div>

  <div class="card">
    <div class="greeting">{briefing.get('greeting','Good morning!')}</div>
    <div class="insight">{briefing.get('mood_insight','')}</div>
  </div>

  <div class="card">
    <h3>🎯 Today's Top Priorities</h3>
    {''.join([f'<div class="priority"><div class="num">{i+1}</div>{p}</div>' for i,p in enumerate(briefing.get('top_priorities',[]))])}
  </div>

  <div class="card">
    <h3>💡 Daily Insights</h3>
    <div class="insight-grid">
      <div class="insight-box"><div class="insight-label">Motivation</div><div class="insight-text">{briefing.get('motivation','')}</div></div>
      <div class="insight-box"><div class="insight-label">Focus Tip</div><div class="insight-text">{briefing.get('focus_tip','')}</div></div>
      <div class="insight-box"><div class="insight-label">Challenge</div><div class="insight-text">{briefing.get('daily_challenge','')}</div></div>
    </div>
  </div>

  {'<div class="card"><h3>🎯 Active Goals</h3>' + ''.join([f'<div class="goal-item"><span>{g.title}</span><span class="badge" style="background:rgba(124,108,252,0.12);color:#7c6cfc">{g.progress}%</span></div>' for g in goals[:5]]) + '</div>' if goals else ''}

  {'<div class="card"><h3>⚡ Habit Streaks</h3>' + ''.join([f'<div class="goal-item"><span>{h.title}</span><span class="badge" style="background:rgba(252,212,108,0.12);color:#fcd46c">🔥 {h.streak}d</span></div>' for h in habits[:5]]) + '</div>' if habits else ''}

  <div class="footer">
    <p>Sent with ❤️ by <a href="#">LifeOS</a> — Your Personal AI Operating System</p>
    <p style="margin-top:6px">Open your <a href="#">LifeOS dashboard</a> to log today's mood</p>
  </div>
</div>
</body>
</html>"""

                msg = Message(
                    subject=f"☀️ LifeOS Morning Briefing — {today}",
                    recipients=[user.email],
                    html=html
                )
                mail.send(msg)
                print(f"✅ Briefing sent to {user.email}")
            except Exception as e:
                print(f"❌ Failed to send to {user.email}: {e}")

# Schedule daily briefing at 8 AM
scheduler = BackgroundScheduler()
scheduler.add_job(func=send_daily_briefings, trigger="cron", hour=8, minute=0)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# ============ AUTH ============

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "User already exists"}), 400
    user = User(
        username=data["username"], password=data["password"],
        name=data.get("name", ""), career_field=data.get("career_field", "Software Engineering"),
        email=data.get("email", ""), xp=0, level=1, email_briefing=True
    )
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "name": user.name})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data["username"]).first()
    if not user or user.password != data["password"]:
        return jsonify({"error": "Invalid credentials"}), 401
    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "name": user.name})

# ============ PROFILE ============

@app.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    xp_needed = user.level * 100
    return jsonify({
        "name": user.name, "level": user.level or 1,
        "xp": user.xp or 0, "xp_needed": xp_needed,
        "xp_percent": int(((user.xp or 0) / xp_needed) * 100),
        "career_field": user.career_field,
        "email": user.email or "",
        "email_briefing": user.email_briefing
    })

@app.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.json
    if "email" in data: user.email = data["email"]
    if "email_briefing" in data: user.email_briefing = data["email_briefing"]
    if "career_field" in data: user.career_field = data["career_field"]
    if "name" in data: user.name = data["name"]
    db.session.commit()
    return jsonify({"message": "Profile updated!"})

# ============ TEST EMAIL ============

@app.route("/send-test-email", methods=["POST"])
@jwt_required()
def send_test_email():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user.email:
        return jsonify({"error": "No email set in profile"}), 400
    try:
        send_daily_briefings()
        return jsonify({"message": f"Briefing sent to {user.email}!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ MOOD ============

@app.route("/mood", methods=["POST"])
@jwt_required()
def log_mood():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.json
    today = datetime.utcnow().strftime("%Y-%m-%d")
    day_of_week = datetime.utcnow().strftime("%A")
    existing = MoodLog.query.filter_by(user_id=user_id, date=today).first()
    if existing:
        existing.mood = data["mood"]; existing.energy = data["energy"]
        existing.note = data.get("note", ""); existing.day_of_week = day_of_week
        db.session.commit()
        return jsonify({"message": "Mood updated!"})
    log = MoodLog(user_id=user_id, mood=data["mood"], energy=data["energy"],
                  note=data.get("note", ""), date=today, day_of_week=day_of_week)
    db.session.add(log)
    xp_result = add_xp(user, 10, "mood_log")
    return jsonify({"message": "Mood logged!", **xp_result})

@app.route("/mood", methods=["GET"])
@jwt_required()
def get_moods():
    user_id = int(get_jwt_identity())
    logs = MoodLog.query.filter_by(user_id=user_id).order_by(MoodLog.created_at.desc()).limit(30).all()
    return jsonify([{"date": l.date, "mood": l.mood, "energy": l.energy,
                     "note": l.note, "day_of_week": l.day_of_week} for l in logs])

@app.route("/mood/insights", methods=["GET"])
@jwt_required()
def mood_insights():
    user_id = int(get_jwt_identity())
    logs = MoodLog.query.filter_by(user_id=user_id).all()
    if len(logs) < 3:
        return jsonify({"has_data": False, "message": "Log at least 3 days of mood to unlock insights"})
    day_moods, day_energy = {}, {}
    for log in logs:
        day = log.day_of_week or "Unknown"
        day_moods.setdefault(day, []).append(log.mood)
        day_energy.setdefault(day, []).append(log.energy)
    day_avg_mood = {d: round(statistics.mean(v), 1) for d, v in day_moods.items()}
    day_avg_energy = {d: round(statistics.mean(v), 1) for d, v in day_energy.items()}
    all_moods = [l.mood for l in logs]
    all_energy = [l.energy for l in logs]
    try:
        correlation = round(statistics.correlation(all_moods, all_energy), 2) if len(all_moods) > 1 else 0
    except: correlation = 0
    trend = "stable"
    if len(all_moods) >= 6:
        recent = statistics.mean(all_moods[:3]); older = statistics.mean(all_moods[3:6])
        if recent > older + 0.5: trend = "improving"
        elif recent < older - 0.5: trend = "declining"
    return jsonify({
        "has_data": True,
        "best_mood_day": max(day_avg_mood, key=day_avg_mood.get),
        "best_mood_score": day_avg_mood[max(day_avg_mood, key=day_avg_mood.get)],
        "best_energy_day": max(day_avg_energy, key=day_avg_energy.get),
        "best_energy_score": day_avg_energy[max(day_avg_energy, key=day_avg_energy.get)],
        "worst_mood_day": min(day_avg_mood, key=day_avg_mood.get),
        "worst_mood_score": day_avg_mood[min(day_avg_mood, key=day_avg_mood.get)],
        "overall_avg_mood": round(statistics.mean(all_moods), 1),
        "overall_avg_energy": round(statistics.mean(all_energy), 1),
        "mood_energy_correlation": correlation, "trend": trend,
        "day_avg_mood": day_avg_mood, "total_logs": len(logs)
    })

# ============ GOALS ============

@app.route("/goals", methods=["GET"])
@jwt_required()
def get_goals():
    user_id = int(get_jwt_identity())
    goals = Goal.query.filter_by(user_id=user_id).all()
    return jsonify([{"id": g.id, "title": g.title, "category": g.category,
                     "progress": g.progress, "deadline": g.deadline, "completed": g.completed} for g in goals])

@app.route("/goals", methods=["POST"])
@jwt_required()
def add_goal():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.json
    goal = Goal(user_id=user_id, title=data["title"],
                category=data.get("category", "career"), deadline=data.get("deadline", ""))
    db.session.add(goal)
    db.session.commit()
    return jsonify({"message": "Goal added!", **add_xp(user, 20, "goal_added")})

@app.route("/goals/<int:goal_id>", methods=["PUT"])
@jwt_required()
def update_goal(goal_id):
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if not goal: return jsonify({"error": "Not found"}), 404
    data = request.json
    was_completed = goal.completed
    goal.progress = data.get("progress", goal.progress)
    goal.completed = data.get("completed", goal.completed)
    if not was_completed and goal.completed:
        goal.progress = 100
        return jsonify({"message": "Goal completed!", **add_xp(user, 100, "goal_completed")})
    db.session.commit()
    return jsonify({"message": "Updated!"})

@app.route("/goals/<int:goal_id>", methods=["DELETE"])
@jwt_required()
def delete_goal(goal_id):
    user_id = int(get_jwt_identity())
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if not goal: return jsonify({"error": "Not found"}), 404
    db.session.delete(goal); db.session.commit()
    return jsonify({"message": "Deleted!"})

# ============ HABITS ============

@app.route("/habits", methods=["GET"])
@jwt_required()
def get_habits():
    user_id = int(get_jwt_identity())
    return jsonify([{"id": h.id, "title": h.title, "streak": h.streak,
                     "last_checked": h.last_checked, "category": h.category}
                    for h in Habit.query.filter_by(user_id=user_id).all()])

@app.route("/habits", methods=["POST"])
@jwt_required()
def add_habit():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.json
    habit = Habit(user_id=user_id, title=data["title"], category=data.get("category", "health"))
    db.session.add(habit); db.session.commit()
    return jsonify({"message": "Habit added!", **add_xp(user, 15, "habit_added")})

@app.route("/habits/<int:habit_id>/check", methods=["POST"])
@jwt_required()
def check_habit(habit_id):
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    habit = Habit.query.filter_by(id=habit_id, user_id=user_id).first()
    if not habit: return jsonify({"error": "Not found"}), 404
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if habit.last_checked != today:
        habit.streak += 1; habit.last_checked = today
        xp = 25 if habit.streak % 7 == 0 else 15
        return jsonify({"streak": habit.streak, **add_xp(user, xp, "habit_checked")})
    return jsonify({"streak": habit.streak})

@app.route("/habits/<int:habit_id>", methods=["DELETE"])
@jwt_required()
def delete_habit(habit_id):
    user_id = int(get_jwt_identity())
    habit = Habit.query.filter_by(id=habit_id, user_id=user_id).first()
    if not habit: return jsonify({"error": "Not found"}), 404
    db.session.delete(habit); db.session.commit()
    return jsonify({"message": "Deleted!"})

# ============ NEWS ============

@app.route("/news", methods=["GET"])
@jwt_required()
def get_news():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    career = (user.career_field or "technology").lower()
    query_map = {
        "software engineering": "software engineering AI",
        "data science": "data science machine learning",
        "machine learning": "machine learning AI",
        "frontend": "web development javascript react",
        "backend": "backend engineering cloud",
        "devops": "devops kubernetes cloud",
    }
    query = query_map.get(career, career + " technology")
    if NEWS_API_KEY and NEWS_API_KEY not in ["your-newsapi-key-here", ""]:
        try:
            resp = requests.get(f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&pageSize=4&language=en&apiKey={NEWS_API_KEY}", timeout=5)
            articles = resp.json().get("articles", [])
            news = [{"title": a["title"], "source": a["source"]["name"],
                     "url": a["url"], "published": a["publishedAt"][:10]}
                    for a in articles[:4] if a.get("title")]
            if news: return jsonify(news)
        except: pass
    return jsonify([
        {"title": "OpenAI releases o3 model with breakthrough reasoning", "source": "TechCrunch", "url": "https://techcrunch.com", "published": "2026-04-15"},
        {"title": "Google announces 50,000 new engineering hires in 2026", "source": "Bloomberg", "url": "https://bloomberg.com", "published": "2026-04-14"},
        {"title": "Meta open-sources Llama 4 with 1T parameter model", "source": "The Verge", "url": "https://theverge.com", "published": "2026-04-13"},
        {"title": "Rust overtakes Python as fastest-growing programming language", "source": "Stack Overflow", "url": "https://stackoverflow.com", "published": "2026-04-12"},
    ])

# ============ BRIEFING ============

@app.route("/briefing", methods=["GET"])
@jwt_required()
def get_briefing():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    try:
        return jsonify(generate_briefing_for_user(user))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ CHAT ============

@app.route("/chat", methods=["POST"])
@jwt_required()
def chat():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    message = request.json.get("message", "")
    goals = Goal.query.filter_by(user_id=user_id, completed=False).all()
    memories = Memory.query.filter_by(user_id=user_id).order_by(Memory.created_at.desc()).limit(10).all()
    mood_logs = MoodLog.query.filter_by(user_id=user_id).order_by(MoodLog.created_at.desc()).limit(5).all()
    context = f"""You are LifeOS AI coach for {user.name} (Level {user.level}) in {user.career_field}.
Goals: {[g.title for g in goals]}. Moods: {[m.mood for m in mood_logs]}. Memories: {[m.content for m in memories]}.
Be concise, warm, actionable. Max 3 sentences unless asked more."""
    try:
        response = client.chat.completions.create(model="gpt-4o-mini",
            messages=[{"role": "system", "content": context}, {"role": "user", "content": message}])
        reply = response.choices[0].message.content
        if any(w in message.lower() for w in ["feel", "struggling", "goal", "habit", "want to", "plan"]):
            db.session.add(Memory(user_id=user_id, content=f"User said: {message[:200]}", memory_type="conversation"))
            db.session.commit()
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ STATS ============

@app.route("/stats", methods=["GET"])
@jwt_required()
def get_stats():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    mood_logs = MoodLog.query.filter_by(user_id=user_id).order_by(MoodLog.created_at.desc()).limit(7).all()
    return jsonify({
        "total_goals": Goal.query.filter_by(user_id=user_id).count(),
        "completed_goals": Goal.query.filter_by(user_id=user_id, completed=True).count(),
        "total_habits": Habit.query.filter_by(user_id=user_id).count(),
        "best_streak": db.session.query(db.func.max(Habit.streak)).filter_by(user_id=user_id).scalar() or 0,
        "avg_mood": round(sum(m.mood for m in mood_logs) / len(mood_logs), 1) if mood_logs else 0,
        "level": user.level or 1, "xp": user.xp or 0, "xp_needed": (user.level or 1) * 100,
        "mood_logs": [{"date": m.date, "mood": m.mood, "energy": m.energy} for m in mood_logs]
    })

# ============ STATIC FILES ============

@app.route("/manifest.json")
def manifest():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "manifest.json")

@app.route("/sw.js")
def service_worker():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "sw.js",
                               mimetype="application/javascript")

@app.route("/")
def serve_ui():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
import os
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import gspread
from google.oauth2.service_account import Credentials

BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "results.json"
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

QUESTION_POOLS = {
    "Technology & Innovation": [
        {"id": "tech_1", "question": "Which protocol is commonly used to transfer data securely over the web?", "options": ["HTTP", "HTTPS", "FTP"], "answer": "HTTPS"},
        {"id": "tech_2", "question": "Which language is commonly used to style a web page?", "options": ["HTML", "CSS", "Python"], "answer": "CSS"},
        {"id": "tech_3", "question": "What is the name of the Python framework commonly used for lightweight web apps?", "options": ["Flask", "Django", "FastAPI"], "answer": "Flask"},
        {"id": "tech_4", "question": "Which storage solution is often used for spreadsheet-style data in the cloud?", "options": ["Google Sheets", "MongoDB", "SQLite"], "answer": "Google Sheets"},
        {"id": "tech_5", "question": "What does API stand for?", "options": ["Application Programming Interface", "Automated Program Integration", "Application Process Index"], "answer": "Application Programming Interface"},
        {"id": "tech_6", "question": "Which HTML element is usually used to create a clickable button?", "options": ["<button>", "<link>", "<input>"], "answer": "<button>"},
    ],
    "Marketing & Sales": [
        {"id": "marketing_1", "question": "What is the main goal of a sales funnel?", "options": ["To attract, nurture and convert leads", "To hire employees", "To create invoices"], "answer": "To attract, nurture and convert leads"},
        {"id": "marketing_2", "question": "Which metric measures how many website visitors become customers?", "options": ["Conversion rate", "Bounce rate", "CTR"], "answer": "Conversion rate"},
        {"id": "marketing_3", "question": "What is the purpose of a value proposition?", "options": ["To define why a customer should choose a product", "To describe office policies", "To write job descriptions"], "answer": "To define why a customer should choose a product"},
        {"id": "marketing_4", "question": "Which marketing channel is best known for short-form visual content?", "options": ["Instagram", "Excel", "Slack"], "answer": "Instagram"},
        {"id": "marketing_5", "question": "What does CRM stand for?", "options": ["Customer Relationship Management", "Client Review Method", "Customer Return Metric"], "answer": "Customer Relationship Management"},
        {"id": "marketing_6", "question": "Which metric shows how many people clicked on an ad versus how many saw it?", "options": ["CTR", "ROI", "CPC"], "answer": "CTR"},
    ],
    "Finance & Operations": [
        {"id": "finance_1", "question": "What does ROI stand for?", "options": ["Return on Investment", "Rate of Income", "Revenue over Inventory"], "answer": "Return on Investment"},
        {"id": "finance_2", "question": "What is a budget primarily used for?", "options": ["Planning and controlling spending", "Hiring staff", "Writing emails"], "answer": "Planning and controlling spending"},
        {"id": "finance_3", "question": "Which term describes the total money coming into a business?", "options": ["Revenue", "Expense", "Liability"], "answer": "Revenue"},
        {"id": "finance_4", "question": "What is the purpose of operational KPIs?", "options": ["To track performance and efficiency", "To design logos", "To pay suppliers"], "answer": "To track performance and efficiency"},
        {"id": "finance_5", "question": "Which process helps a business check if its cash inflows cover its outflows?", "options": ["Cash flow analysis", "Market research", "Branding"], "answer": "Cash flow analysis"},
        {"id": "finance_6", "question": "What is a fixed cost?", "options": ["A cost that stays fairly constant over time", "A one-time sale", "A customer refund"], "answer": "A cost that stays fairly constant over time"},
    ],
    "People & Culture": [
        {"id": "people_1", "question": "What is the goal of employee engagement?", "options": ["To improve motivation and commitment", "To reduce payroll", "To bypass training"], "answer": "To improve motivation and commitment"},
        {"id": "people_2", "question": "Which document usually outlines responsibilities and expectations for a job role?", "options": ["Job description", "Sales report", "Invoice"], "answer": "Job description"},
        {"id": "people_3", "question": "Why is onboarding important?", "options": ["It helps new employees get productive faster", "It decreases office rent", "It replaces marketing"], "answer": "It helps new employees get productive faster"},
        {"id": "people_4", "question": "What is a common purpose of team training?", "options": ["To improve skills and performance", "To create social media posts", "To reduce customer service"], "answer": "To improve skills and performance"},
        {"id": "people_5", "question": "Which concept is focused on creating a respectful and inclusive workplace?", "options": ["Company culture", "Inventory planning", "Market segmentation"], "answer": "Company culture"},
        {"id": "people_6", "question": "What does retention mean in HR?", "options": ["Keeping employees in the company", "Reducing product prices", "Sending new offers"], "answer": "Keeping employees in the company"},
    ],
    "Customer Experience": [
        {"id": "cx_1", "question": "What does NPS stand for?", "options": ["Net Promoter Score", "New Product Survey", "Network Performance Standard"], "answer": "Net Promoter Score"},
        {"id": "cx_2", "question": "What is the main purpose of customer feedback?", "options": ["To understand needs and improve service", "To increase taxes", "To reduce office time"], "answer": "To understand needs and improve service"},
        {"id": "cx_3", "question": "Which metric helps measure how quickly a company responds to customers?", "options": ["Response time", "Inventory count", "Operating margin"], "answer": "Response time"},
        {"id": "cx_4", "question": "What is a common goal of customer support?", "options": ["Resolve problems efficiently and politely", "Train employees for sales", "Increase manufacturing speed"], "answer": "Resolve problems efficiently and politely"},
        {"id": "cx_5", "question": "Which experience element is most directly tied to customer satisfaction?", "options": ["Service quality", "Office layout", "Accounting rules"], "answer": "Service quality"},
        {"id": "cx_6", "question": "What is the benefit of personalization in customer experience?", "options": ["It makes interactions more relevant and effective", "It shortens product lines", "It eliminates customer service"], "answer": "It makes interactions more relevant and effective"},
    ],
    "Strategy & Leadership": [
        {"id": "strategy_1", "question": "What is a business strategy?", "options": ["A plan to achieve long-term goals", "A list of employees", "A monthly budget"], "answer": "A plan to achieve long-term goals"},
        {"id": "strategy_2", "question": "Why do companies use KPIs?", "options": ["To measure progress toward goals", "To create product designs", "To assign office chairs"], "answer": "To measure progress toward goals"},
        {"id": "strategy_3", "question": "What does stakeholder management focus on?", "options": ["Balancing interests of people affected by the business", "Reducing product inventory", "Writing technical manuals"], "answer": "Balancing interests of people affected by the business"},
        {"id": "strategy_4", "question": "Which skill is most important for effective leadership?", "options": ["Decision-making", "Data entry", "Inventory counting"], "answer": "Decision-making"},
        {"id": "strategy_5", "question": "What is the purpose of a SWOT analysis?", "options": ["To evaluate strengths, weaknesses, opportunities and threats", "To calculate payroll", "To track customer orders"], "answer": "To evaluate strengths, weaknesses, opportunities and threats"},
        {"id": "strategy_6", "question": "What does prioritization help a team do?", "options": ["Focus on the most important work first", "Increase office noise", "Reduce meeting time only"], "answer": "Focus on the most important work first"},
    ],
}

QUESTION_COUNT_PER_CATEGORY = 3
CATEGORY_ORDER = list(QUESTION_POOLS.keys())

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "quiz-secret-key")


def build_category_quiz():
    selected_questions = []
    for category_name in CATEGORY_ORDER:
        pool = QUESTION_POOLS[category_name]
        picked = random.sample(pool, k=min(len(pool), QUESTION_COUNT_PER_CATEGORY))
        selected_questions.append({
            "category": category_name,
            "questions": picked,
        })
    return selected_questions


def get_quiz_session():
    participant = session.get("participant")
    quiz_state = session.get("quiz_state")
    if not participant or not isinstance(quiz_state, list):
        return None
    return participant, quiz_state


def get_sheet():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        raise FileNotFoundError("GOOGLE_APPLICATION_CREDENTIALS is not set")

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1


def ensure_headers(sheet):
    if not sheet.row_values(1):
        sheet.append_row(["name", "email", "phone", "score", "submitted_at"])
    elif sheet.row_values(1) != ["name", "email", "phone", "score", "submitted_at"]:
        sheet.insert_row(["name", "email", "phone", "score", "submitted_at"], 1)
        sheet.delete_row(2)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/quiz")
def quiz_start():
    name = request.args.get("name", "").strip()
    email = request.args.get("email", "").strip()
    phone = request.args.get("phone", "").strip()

    if not name or not email or not phone:
        return redirect(url_for("index"))

    session["participant"] = {"name": name, "email": email, "phone": phone}
    session["quiz_state"] = build_category_quiz()
    session["scores"] = {}
    return redirect(url_for("quiz_category_page", page_num=0))


@app.get("/quiz/page/<int:page_num>")
def quiz_category_page(page_num):
    data = get_quiz_session()
    if data is None:
        return redirect(url_for("index"))

    participant, quiz_state = data
    if page_num < 0 or page_num >= len(quiz_state):
        return redirect(url_for("quiz_results"))

    page = quiz_state[page_num]
    return render_template(
        "quiz.html",
        name=participant["name"],
        email=participant["email"],
        phone=participant["phone"],
        category=page["category"],
        page_num=page_num,
        total_pages=len(quiz_state),
        is_last_page=(page_num == len(quiz_state) - 1),
        questions=page["questions"],
    )


@app.post("/quiz/page")
def submit_quiz_page():
    data = get_quiz_session()
    if data is None:
        return redirect(url_for("index"))

    participant, quiz_state = data
    page_num = int(request.form.get("page_num", 0))
    if page_num < 0 or page_num >= len(quiz_state):
        return redirect(url_for("index"))

    page = quiz_state[page_num]
    score = 0
    for question in page["questions"]:
        selected_answer = request.form.get(f"q_{question['id']}")
        if selected_answer == question["answer"]:
            score += 1

    session_scores = session.get("scores", {})
    session_scores[str(page_num)] = {
        "category": page["category"],
        "score": score,
        "total_questions": len(page["questions"]),
    }
    session["scores"] = session_scores

    if page_num < len(quiz_state) - 1:
        return redirect(url_for("quiz_category_page", page_num=page_num + 1))

    return redirect(url_for("quiz_results"))


@app.get("/quiz/results")
def quiz_results():
    data = get_quiz_session()
    if data is None:
        return redirect(url_for("index"))

    participant, quiz_state = data
    category_scores = []
    total_score = 0
    total_questions = 0
    session_scores = session.get("scores", {})

    for index, page in enumerate(quiz_state):
        score_data = session_scores.get(str(index), {})
        score = score_data.get("score", 0)
        page_total = score_data.get("total_questions", len(page["questions"]))
        category_scores.append({
            "category": page["category"],
            "score": score,
            "total": page_total,
        })
        total_score += score
        total_questions += page_total

    return render_template(
        "results.html",
        name=participant["name"],
        email=participant["email"],
        phone=participant["phone"],
        category_scores=category_scores,
        total_score=total_score,
        total_questions=total_questions,
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/submit")
def submit_score():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    email = str(payload.get("email") or "").strip()
    phone = str(payload.get("phone") or "").strip()
    score = str(payload.get("score") or "").strip()

    if not name or not email or not phone or not score:
        return jsonify({"error": "Missing required fields: name, email, phone and score"}), 400

    results = []
    if RESULTS_FILE.exists():
        try:
            with RESULTS_FILE.open("r", encoding="utf-8") as file:
                existing_results = json.load(file)
            if isinstance(existing_results, list):
                results = existing_results
        except (json.JSONDecodeError, OSError):
            results = []

    results.append({"name": name, "score": score})

    with RESULTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)

    try:
        if not GOOGLE_SHEET_ID:
            raise ValueError("GOOGLE_SHEET_ID is not set")
        sheet = get_sheet()
        ensure_headers(sheet)
        submitted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
        sheet.append_row([name, email, phone, score, submitted_at])
    except Exception as exc:
        return jsonify({"error": f"Failed to save to Google Sheet: {exc}"}), 500

    return jsonify({
        "message": "Score saved successfully",
        "name": name,
        "score": score,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

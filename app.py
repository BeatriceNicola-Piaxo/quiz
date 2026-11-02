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
    "Hardware": [
        {"id": "hw_1", "question": "What does LED stand for?", "options": ["Light Emitting Diode", "Low Energy Device", "Light Electronic Driver"], "answer": "Light Emitting Diode"},
        {"id": "hw_2", "question": "What is the nominal voltage of a single Lithium-Ion cell used in many battery packs?", "options": ["1.5 V", "3.6-3.7 V", "12 V"], "answer": "3.6-3.7 V"},
        {"id": "hw_3", "question": "What is the primary purpose of a BMU (Battery Management Unit)?", "options": ["Increase motor power", "Play warning sounds", "Monitor and protect the battery system"], "answer": "Monitor and protect the battery system"},
        {"id": "hw_4", "question": "Why are two 120 Ω termination resistors typically used on a CAN bus?", "options": ["To increase current capacity", "To reduce power consumption", "To match cable impedance and reduce signal reflections"], "answer": "To match cable impedance and reduce signal reflections"},
        {"id": "hw_5", "question": "A battery pack consists of 8 Li-Ion cells connected in series. Each cell is at 3.7 V. What is the pack voltage?", "options": ["8.0 V", "14.8 V", "29.6 V"], "answer": "29.6 V"},
        {"id": "hw_6", "question": "What happens when batteries are connected in series?", "options": ["Capacity increases, voltage stays the same", "Voltage increases, capacity stays approximately the same", "Both voltage and capacity double"], "answer": "Voltage increases, capacity stays approximately the same"},
        {"id": "hw_7", "question": "What does a fuse primarily protect against?", "options": ["High temperature only", "Excessive current", "Low battery voltage"], "answer": "Excessive current"},
        {"id": "hw_8", "question": "Which sensor is most commonly used by a BMU to prevent battery overheating?", "options": ["Pressure sensor", "Humidity sensor", "Temperature sensor"], "answer": "Temperature sensor"},
        {"id": "hw_9", "question": "Why is cell balancing used in a battery pack?", "options": ["To make the battery heavier", "To ensure all cells maintain a similar state of charge", "To increase CAN bus speed"], "answer": "To ensure all cells maintain a similar state of charge"},
        {"id": "hw_10", "question": "A BMU detects that one cell voltage exceeds the maximum allowed limit. What should happen?", "options": ["Ignore it if only one cell is affected", "Increase charging current", "Take protective action such as stopping charging or disconnecting the battery"], "answer": "Take protective action such as stopping charging or disconnecting the battery"},
    ],
    "Software": [
        {"id": "sw_1", "question": 'What is the effect of the "break" statement when it is used inside a "for" loop?', "options": ["It immediately terminates the execution of the for loop and continues with the next statement after the loop.", "It exits the program completely.", "It skips the current iteration and continues the loop."], "answer": "It skips the current iteration and continues the loop."},
        {"id": "sw_2", "question": "Which operator is used to set bit 3 of a register?", "options": ["reg |= (1 << 3);", "reg &= (1 << 3);", "reg ^= (1 << 3);"], "answer": "reg |= (1 << 3);"},
        {"id": "sw_3", "question": "What is the result of the expression below?\n\nuint8_t x = 0x55;\nx ^= 0xFF;", "options": ["0x00", "0xAA", "0x55"], "answer": "0xAA"},
        {"id": "sw_4", "question": "Which statement about stack usage in embedded systems is true?", "options": ["Stack size is unlimited", "Stack overflow cannot occur in C", "Recursion may cause stack overflow"], "answer": "Recursion may cause stack overflow"},
        {"id": "sw_5", "question": "What is the primary purpose of a Watchdog Timer (WDT)?", "options": ["Measure execution time of Watchdog runnables", "Manage the timer used by the Watchdog SW driver", "Control the I/O pins of the MCU"], "answer": "Manage the timer used by the Watchdog SW driver"},
        {"id": "sw_6", "question": "What is the value of x after executing the code?\n\nuint8_t x = 0x0F;\nx <<= 2;", "options": ["0x11", "0x3C", "0xF0"], "answer": "0x3C"},
        {"id": "sw_7", "question": "Which operation clears bit 5 in a register?", "options": ["reg |= (1 << 5);", "reg ^= (1 << 5);", "reg &= ~(1 << 5);"], "answer": "reg &= ~(1 << 5);"},
        {"id": "sw_8", "question": 'What is the output?\n\nuint8_t a = 5;\nuint8_t b = 3;\n\nprintf("%d", a & b);', "options": ["1", "7", "8"], "answer": "1"},
        {"id": "sw_9", "question": "What does this code do?\n\nuint32_t timeout = 1000;\n\nwhile(timeout--)\n{\n}", "options": ["Infinite loop", "Busy wait delay loop", "Memory initialization"], "answer": "Busy wait delay loop"},
        {"id": "sw_10", "question": "Which is generally safer for embedded safety-critical systems?", "options": ["Dynamic memory allocation during runtime", "Static memory allocation determined at compile time", "Using recursion everywhere"], "answer": "Static memory allocation determined at compile time"},
        {"id": "sw_11", "question": 'What is wrong with the following code?\n\nchar *str;\n\nstrcpy(str, "Hello");', "options": ["Nothing - the code is correct", "str does not point to valid memory before copying into it.", "The code is not valid C syntax."], "answer": "str does not point to valid memory before copying into it."},
    ],
    "FuSa": [
        {"id": "fusa_1", "question": "What is the main purpose of Functional Safety?", "options": ["To ensure that a product never experiences a failure", "To prevent failures from leading to unacceptable risks", "To eliminate the need for product testing"], "answer": "To prevent failures from leading to unacceptable risks"},
        {"id": "fusa_2", "question": "Which sequence correctly describes how a technical problem can create a safety risk?", "options": ["Hazard → failure → correct behavior", "Failure → incorrect system behavior → hazard", "Incorrect behavior → evidence → failure"], "answer": "Failure → incorrect system behavior → hazard"},
        {"id": "fusa_3", "question": "In the BMS example, what should happen if the actual cell voltage becomes too high?", "options": ["The system should continue charging normally", "The system should detect the problem and limit or stop charging", "The system should only record the voltage after charging is complete"], "answer": "The system should detect the problem and limit or stop charging"},
        {"id": "fusa_4", "question": "Which activity is part of developing the safety concept?", "options": ["Defining Safety Goals, FSRs, TSRs, safe states and timing", "Selecting the product's color and external appearance", "Preparing the marketing strategy"], "answer": "Defining Safety Goals, FSRs, TSRs, safe states and timing"},
        {"id": "fusa_5", "question": "Which of the following belongs to safety analysis?", "options": ["FTA, FMEA, FMEDA and DFA", "Sales forecasting and customer segmentation", "Cost calculation and production scheduling"], "answer": "FTA, FMEA, FMEDA and DFA"},
        {"id": "fusa_6", "question": "What is the purpose of Verification and Validation, or V&V?", "options": ["To demonstrate through tests and fault injection that the safety reaction works correctly", "To replace safety requirements with test results", "To define the commercial price of the product"], "answer": "To demonstrate through tests and fault injection that the safety reaction works correctly"},
        {"id": "fusa_7", "question": "Who is primarily responsible for planning and coordinating Functional Safety activities?", "options": ["Functional Safety Manager, or FSM", "Marketing representative", "Vehicle driver"], "answer": "Functional Safety Manager, or FSM"},
        {"id": "fusa_8", "question": "What is the role of an independent reviewer?", "options": ["To implement all hardware safety mechanisms", "To independently verify the quality of the evidence and compliance", "To approve the project budget"], "answer": "To independently verify the quality of the evidence and compliance"},
        {"id": "fusa_9", "question": "What does a Safety Case provide?", "options": ["An argument supported by evidence that the product is sufficiently safe for its defined context", "A list of all product components and their purchase prices", "A guarantee that the product can never fail"], "answer": "An argument supported by evidence that the product is sufficiently safe for its defined context"},
        {"id": "fusa_10", "question": "During charging, the actual cell voltage reaches 4.35 V, but the measurement remains stuck at 3.60 V. Which is an appropriate safety reaction?", "options": ["Continue charging because the measured value is below the limit", "Limit or inhibit charging and disconnect if required by the applicable threshold and timing", "Ignore the problem until the next maintenance inspection"], "answer": "Limit or inhibit charging and disconnect if required by the applicable threshold and timing"},
    ],
    "Cyber Security": [
        {"id": "cyber_1", "question": "What is the main difference between encryption and hashing?", "options": ["Encryption is only used for passwords, while hashing is used for files.", "Encryption is reversible; hashing is designed to be one-way.", "Hashing is more secure than encryption."], "answer": "Encryption is reversible; hashing is designed to be one-way."},
        {"id": "cyber_2", "question": "In symmetric encryption, what is used to encrypt and decrypt the data?", "options": ["Two completely unrelated passwords.", "The same secret key.", "No key is needed."], "answer": "The same secret key."},
        {"id": "cyber_3", "question": "In asymmetric cryptography, which keys are normally used?", "options": ["Two public keys.", "A public key and a private key.", "One password and one username."], "answer": "A public key and a private key."},
        {"id": "cyber_4", "question": "Which statement best describes a cryptographic hash function such as SHA-256?", "options": ["It encrypts information that can later be decrypted.", "It creates a fixed-length digest from input data, which is hard to reverse.", "It stores passwords in plaintext."], "answer": "It creates a fixed-length digest from input data, which is hard to reverse."},
        {"id": "cyber_5", "question": "What can a digital signature primarily help verify?", "options": ["That file has been encrypted.", "That nobody is able to copy the file.", "The authenticity and integrity of a message or document."], "answer": "The authenticity and integrity of a message or document."},
    ],
    "System": [
        {"id": "sys_1", "question": "What does NPS stand for?", "options": ["Net Promoter Score", "New Product Survey", "Network Performance Standard"], "answer": "Net Promoter Score"},
        {"id": "sys_2", "question": "What is the main purpose of customer feedback?", "options": ["To understand needs and improve service", "To increase taxes", "To reduce office time"], "answer": "To understand needs and improve service"},
        {"id": "sys_3", "question": "Which metric helps measure how quickly a company responds to customers?", "options": ["Response time", "Inventory count", "Operating margin"], "answer": "Response time"},
        {"id": "sys_4", "question": "What is a common goal of customer support?", "options": ["Resolve problems efficiently and politely", "Train employees for sales", "Increase manufacturing speed"], "answer": "Resolve problems efficiently and politely"},
        {"id": "sys_5", "question": "Which experience element is most directly tied to customer satisfaction?", "options": ["Service quality", "Office layout", "Accounting rules"], "answer": "Service quality"},
        {"id": "sys_6", "question": "What is the benefit of personalization in customer experience?", "options": ["It makes interactions more relevant and effective", "It shortens product lines", "It removes paperwork"], "answer": "It makes interactions more relevant and effective"},
    ],
    "Quality": [
        {"id": "q_1", "question": 'What does "quality" mean for a product or service?', "options": ["To be the most expensive", "To fulfill the client's requirements and expectations", "To receive the highest number of likes"], "answer": "To fulfill the client's requirements and expectations"},
        {"id": "q_2", "question": "You find a problem in a product. What is the best approach?", "options": ["If the client didn't notice it, you ignore it", "You quickly fix it without looking for the root cause", "You investigate the issue, identify the root cause and correct it"], "answer": "You investigate the issue, identify the root cause and correct it"},
        {"id": "q_3", "question": "Who is responsible for quality in an organisation?", "options": ["Only the Quality department", "Managers only", "Everyone involved in developing the product or service"], "answer": "Everyone involved in developing the product or service"},
        {"id": "q_4", "question": "What is more efficient?", "options": ["To detect the defects at the end", "To prevent the appearance of defects", "To repair the product after delivery"], "answer": "To prevent the appearance of defects"},
        {"id": "q_5", "question": "Why it's important to find the cause of a problem?", "options": ["To idenitfy the responsible person", "To prevent it's reoccurence", "To fill in a report"], "answer": "To prevent it's reoccurence"},
        {"id": "q_6", "question": "A client reports a problem that appears very rearly. What should we do?", "options": ["Ignore it because it's rare", "Investigate the problem and the associated causes", "Tell the client it is not a quality issue"], "answer": "Investigate the problem and the associated causes"},
        {"id": "q_7", "question": "Which of the following is an example of continuous improvement?", "options": ["Repeating the same method regardless of the results", "Analyse the results and improve the process", "Only changing the product after a complaint"], "answer": "Analyse the results and improve the process"},
        {"id": "q_8", "question": "Why clear requirements are important to have before developing a product?", "options": ["They reduce the risk of misunderstandings and errors", "They completely replace testing", "They are only useful for the sales team"], "answer": "They reduce the risk of misunderstandings and errors"},
        {"id": "q_9", "question": "A product passes all the defined tests. Does this automatically mean it is qualitative?", "options": ["Yes, always", "Not necessarily. Tests must cover all requirements and quality criteria", "No, quality is only reported by the customer"], "answer": "Not necessarily. Tests must cover all requirements and quality criteria"},
        {"id": "q_10", "question": "Which statement best describes quality culture?", "options": ["Quality will find all problems", "If it works, there's no need for quality checks", "Each of us contributes to quality and prevention"], "answer": "Each of us contributes to quality and prevention"},
    ],
}

QUESTION_COUNT_PER_CATEGORY = 3
CATEGORY_ORDER = list(QUESTION_POOLS.keys())
CATEGORY_RESULT_HEADERS = ["name", "email", "phone", "score"] + CATEGORY_ORDER + ["answers", "submitted_at"]

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


def get_category_summary(session_scores, quiz_state):
    category_scores = {}
    for index, page in enumerate(quiz_state):
        score_data = session_scores.get(str(index), {})
        score = score_data.get("score", 0)
        page_total = score_data.get("total_questions", len(page["questions"]))
        category_scores[page["category"]] = f"{score}/{page_total}"
    return category_scores


def normalize_category_scores(category_scores):
    normalized = {}
    for category in CATEGORY_ORDER:
        value = category_scores.get(category) if isinstance(category_scores, dict) else None
        if value is None:
            normalized[category] = "0/0"
        else:
            normalized[category] = str(value)
    return normalized


def normalize_question_answers(question_answers):
    normalized = {}
    if not isinstance(question_answers, dict):
        return normalized
    for key, value in question_answers.items():
        normalized[str(key)] = str(value)
    return normalized


def get_sheet():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        raise FileNotFoundError("GOOGLE_APPLICATION_CREDENTIALS is not set")

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1


def ensure_headers(sheet):
    current_headers = sheet.row_values(1)

    if not current_headers:
        sheet.append_row(CATEGORY_RESULT_HEADERS)
        return

    if current_headers == CATEGORY_RESULT_HEADERS:
        return

    legacy_headers = ["name", "email", "phone", "score", "submitted_at"]
    legacy_json_headers = ["name", "email", "phone", "score", "category_scores", "submitted_at"]

    if current_headers == legacy_headers or current_headers == legacy_json_headers:
        sheet.clear()
        sheet.update("A1", [CATEGORY_RESULT_HEADERS])
        return

    if current_headers[:4] == ["name", "email", "phone", "score"]:
        sheet.clear()
        sheet.update("A1", [CATEGORY_RESULT_HEADERS])
        return

    sheet.clear()
    sheet.update("A1", [CATEGORY_RESULT_HEADERS])


def save_quiz_result(name, email, phone, score, category_scores=None, question_answers=None):
    if not name or not email or not phone or not score:
        raise ValueError("Missing required fields: name, email, phone and score")

    submitted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    results = []
    if RESULTS_FILE.exists():
        try:
            with RESULTS_FILE.open("r", encoding="utf-8") as file:
                existing_results = json.load(file)
            if isinstance(existing_results, list):
                results = existing_results
        except (json.JSONDecodeError, OSError):
            results = []

    normalized_category_scores = normalize_category_scores(category_scores or {})
    normalized_question_answers = normalize_question_answers(question_answers)
    result_entry = {
        "name": name,
        "email": email,
        "phone": phone,
        "score": score,
        "category_scores": normalized_category_scores,
        "question_answers": normalized_question_answers,
        "submitted_at": submitted_at,
    }
    results.append(result_entry)

    with RESULTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)

    if not GOOGLE_SHEET_ID:
        raise ValueError("GOOGLE_SHEET_ID is not set")

    sheet = get_sheet()
    ensure_headers(sheet)
    row = [name, email, phone, score]
    row.extend(normalized_category_scores.get(category, "0/0") for category in CATEGORY_ORDER)
    row.append(json.dumps(normalized_question_answers, ensure_ascii=False))
    row.append(submitted_at)
    sheet.append_row(row)


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
    session["answers"] = {}
    session["result_saved"] = False
    session["save_error"] = None
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
    page_answers = {}
    for question in page["questions"]:
        selected_answer = request.form.get(f"q_{question['id']}")
        page_answers[question["id"]] = selected_answer
        if selected_answer == question["answer"]:
            score += 1

    session_answers = session.get("answers", {})
    session_answers.update(page_answers)
    session["answers"] = session_answers

    session_scores = session.get("scores", {})
    session_scores[str(page_num)] = {
        "category": page["category"],
        "score": score,
        "total_questions": len(page["questions"]),
    }
    session["scores"] = session_scores

    if page_num < len(quiz_state) - 1:
        return redirect(url_for("quiz_category_page", page_num=page_num + 1))

    total_score = 0
    total_questions = 0
    for index, category_page in enumerate(quiz_state):
        score_data = session_scores.get(str(index), {})
        total_score += score_data.get("score", 0)
        total_questions += score_data.get("total_questions", len(category_page["questions"]))

    final_score = f"{total_score} / {total_questions}"
    category_scores = get_category_summary(session_scores, quiz_state)
    try:
        save_quiz_result(participant["name"], participant["email"], participant["phone"], final_score, category_scores, session.get("answers", {}))
        session["result_saved"] = True
        session["save_error"] = None
    except Exception as exc:
        session["result_saved"] = False
        session["save_error"] = str(exc)

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
    question_answers = session.get("answers", {})

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

    if not session.get("result_saved"):
        final_score = f"{total_score} / {total_questions}"
        try:
            save_quiz_result(participant["name"], participant["email"], participant["phone"], final_score, get_category_summary(session_scores, quiz_state), question_answers)
            session["result_saved"] = True
            session["save_error"] = None
        except Exception as exc:
            session["result_saved"] = False
            session["save_error"] = str(exc)

    return render_template(
        "results.html",
        name=participant["name"],
        email=participant["email"],
        phone=participant["phone"],
        category_scores=category_scores,
        total_score=total_score,
        total_questions=total_questions,
        save_error=session.get("save_error"),
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
    category_scores = payload.get("category_scores") or payload.get("categories") or {}
    question_answers = payload.get("question_answers") or payload.get("answers") or {}

    try:
        save_quiz_result(name, email, phone, score, category_scores, question_answers)
    except Exception as exc:
        return jsonify({"error": f"Failed to save to Google Sheet: {exc}"}), 500

    return jsonify({
        "message": "Score saved successfully",
        "name": name,
        "score": score,
        "category_scores": normalize_category_scores(category_scores),
        "question_answers": normalize_question_answers(question_answers),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

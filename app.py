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
        {"id": "sys_1", "question": "What is the main purpose of system requirements?", "options": [
            "To describe the hardware and software implementation",
            "To define what the system must accomplish to satisfy stakeholder needs",
            "To define the production process"
        ],
        "answer": "To define what the system must accomplish to satisfy stakeholder needs"
    },
    {
        "id": "se_2",
        "question": "Which of the following is a well-formulated system requirement?",
        "options": [
            "The battery must have high performance.",
            "The battery shall provide a minimum of 300 A for 5 seconds at -18°C.",
            "The battery must be robust."
        ],
        "answer": "The battery shall provide a minimum of 300 A for 5 seconds at -18°C."
    },
    {
        "id": "se_3",
        "question": "What does requirements traceability represent?",
        "options": [
            "Connecting requirements with the associated design and tests.",
            "Numbering requirements in a document.",
            "Storing requirements in a database."
        ],
        "answer": "Connecting requirements with the associated design and tests."
    },
    {
        "id": "se_4",
        "question": "Which of the following is an external interface of a 12V battery?",
        "options": [
            "State of Charge estimation algorithm.",
            "CAN bus connection to the vehicle.",
            "Balancing function."
        ],
        "answer": "CAN bus connection to the vehicle."
    },
    {
        "id": "se_5",
        "question": "What does system architecture describe?",
        "options": [
            "The structure of system elements and the relationships between them.",
            "Only the battery electrical schematic.",
            "Only the list of components."
        ],
        "answer": "The structure of system elements and the relationships between them."
    },
    {
        "id": "se_6",
        "question": "What is the purpose of Verification?",
        "options": [
            "To demonstrate that the system was built according to requirements.",
            "To demonstrate that the user is satisfied.",
            "To demonstrate the product's profitability."
        ],
        "answer": "To demonstrate that the system was built according to requirements."
    },
    {
        "id": "se_7",
        "question": "What is the purpose of Validation?",
        "options": [
            "To demonstrate that all tests have been executed.",
            "To demonstrate that the product satisfies user needs and the operational purpose.",
            "To demonstrate compliance with the BOM."
        ],
        "answer": "To demonstrate that the product satisfies user needs and the operational purpose."
    },
    {
        "id": "se_8",
        "question": "What is a system function for a 12V battery?",
        "options": [
            "Monitoring and reporting the State of Charge to the vehicle.",
            "Cover fastening screw.",
            "Upper housing."
        ],
        "answer": "Monitoring and reporting the State of Charge to the vehicle."
    },
    {
        "id": "se_9",
        "question": "What activity is performed during requirements allocation?",
        "options": [
            "Requirements are assigned to elements of the system architecture.",
            "Requirements are deleted if they are not needed.",
            "Requirements are transformed into manufacturing procedures."
        ],
        "answer": "Requirements are assigned to elements of the system architecture."
    },
    {
        "id": "se_10",
        "question": "For the requirement 'Battery shall provide State of Charge information via CAN', what must exist?",
        "options": [
            "An associated test or verification method.",
            "A mechanical drawing.",
            "A financial report."
        ],
        "answer": "An associated test or verification method."
    },
    {
        "id": "se_11",
        "question": "The stakeholder requirement is: 'The vehicle must be able to start under any normal operating conditions.' How should it be handled at system level?",
        "options": [
            "Copy it identically into the system specification.",
            "Transform it into measurable requirements regarding voltage, SoC, and cranking capability at defined temperatures.",
            "Transfer it directly to the hardware team."
        ],
        "answer": "Transform it into measurable requirements regarding voltage, SoC, and cranking capability at defined temperatures."
    },
    {
        "id": "se_12",
        "question": "Which of the following is an example of a system constraint?",
        "options": [
            "The battery shall communicate via CAN 2.0B because this is the vehicle interface.",
            "The battery shall estimate SoC.",
            "The battery shall monitor temperature."
        ],
        "answer": "The battery shall communicate via CAN 2.0B because this is the vehicle interface."
    },
    {
        "id": "se_13",
        "question": "What is the primary purpose of Requirements Allocation?",
        "options": [
            "Reducing production costs.",
            "Assigning requirements to system architecture elements.",
            "Creating the test plan."
        ],
        "answer": "Assigning requirements to system architecture elements."
    },
    {
        "id": "se_14",
        "question": "Which of the following is a functional requirement?",
        "options": [
            "The battery weight shall be below 15 kg.",
            "The battery shall transmit the State of Charge value on the CAN bus at intervals not exceeding 1 second.",
            "The housing shall be black."
        ],
        "answer": "The battery shall transmit the State of Charge value on the CAN bus at intervals not exceeding 1 second."
    },
    {
        "id": "se_15",
        "question": "Which document typically describes system usage scenarios?",
        "options": [
            "Use Case Specification",
            "BOM",
            "PPAP"
        ],
        "answer": "Use Case Specification"
    },
    {
        "id": "se_16",
        "question": "Which of the following represents a mechanical interface?",
        "options": [
            "CAN Bus",
            "LIN Bus",
            "Battery terminals and mounting points in the vehicle"
        ],
        "answer": "Battery terminals and mounting points in the vehicle"
    },
    {
        "id": "se_17",
        "question": "What does validation ('Are we building the right system?') mean?",
        "options": [
            "Verifying implementation of requirements.",
            "Demonstrating that the product fulfills user needs and operational purpose.",
            "Reviewing source code."
        ],
        "answer": "Demonstrating that the product fulfills user needs and operational purpose."
    },
    {
        "id": "se_18",
        "question": "What problem occurs if a requirement is not traceable to a stakeholder requirement?",
        "options": [
            "No problem.",
            "Increased risk of implementing unjustified functionality ('gold plating').",
            "The battery cost decreases."
        ],
        "answer": "Increased risk of implementing unjustified functionality ('gold plating')."
    },
    {
        "id": "se_19",
        "question": "Which of the following represents a battery operational mode?",
        "options": [
            "Nominal, Sleep, Fault, Transport",
            "Hardware, Software, Mechanical",
            "Requirement, Design, Test"
        ],
        "answer": "Nominal, Sleep, Fault, Transport"
    },
    {
        "id": "se_20",
        "question": "For the requirement 'Battery shall prevent operation outside the allowable cell temperature range.' What is the best verification method?",
        "options": [
            "Inspection",
            "Demonstration",
            "Functional testing at temperatures outside the allowable limits"
        ],
        "answer": "Functional testing at temperatures outside the allowable limits"
    },
    {
        "id": "se_21",
        "question": "What represents a system function?",
        "options": [
            "NTC sensor",
            "Electrical terminal contact",
            "Monitoring and reporting SoC to the vehicle"
        ],
        "answer": "Monitoring and reporting SoC to the vehicle"
    },
    {
        "id": "se_22",
        "question": "What is an unambiguous requirement?",
        "options": [
            "The battery must have high performance.",
            "The battery must have good autonomy.",
            "The battery shall provide at least 6 Ah at 25°C and 100% SoC."
        ],
        "answer": "The battery shall provide at least 6 Ah at 25°C and 100% SoC."
    },
    {
        "id": "se_23",
        "question": "In the system architecture, which element is responsible for energy management?",
        "options": [
            "Vehicle ECU",
            "Battery Management System (BMS)",
            "Battery housing"
        ],
        "answer": "Battery Management System (BMS)"
    },
    {
        "id": "se_24",
        "question": "Which of the following indicates a poorly formulated requirement?",
        "options": [
            "Battery shall support communication via CAN 500 kbit/s.",
            "Battery shall provide SoC accuracy better than ±5%.",
            "Battery shall have sufficient current capability."
        ],
        "answer": "Battery shall have sufficient current capability."
    },
    {
        "id": "se_25",
        "question": "Which artifact is essential for demonstrating verification completeness?",
        "options": [
            "Requirement-to-Test Case Traceability Matrix",
            "BOM",
            "CAD Model"
        ],
        "answer": "Requirement-to-Test Case Traceability Matrix"
    },
    {
        "id": "se_26",
        "question": "A system requirement states: 'Battery shall withstand reverse polarity connection for 60 seconds.' This is:",
        "options": [
            "A functional requirement.",
            "An interface requirement.",
            "A robustness/protection requirement."
        ],
        "answer": "A robustness/protection requirement."
    },
    {
        "id": "se_27",
        "question": "What is the main purpose of System Requirements Definition?",
        "options": [
            "Implementing BMS software.",
            "Defining system requirements based on stakeholder requirements.",
            "Selecting the cell supplier."
        ],
        "answer": "Defining system requirements based on stakeholder requirements."
    },
    {
        "id": "se_28",
        "question": "Which of the following is a correctly formulated system requirement?",
        "options": [
            "The battery must be very reliable.",
            "The battery must use prismatic cells.",
            "The battery shall provide at least 300 A for 5 seconds at -18°C."
        ],
        "answer": "The battery shall provide at least 300 A for 5 seconds at -18°C."
    },
    {
        "id": "se_29",
        "question": "In the V-Cycle, verification of system requirements is performed through:",
        "options": [
            "Marketing reviews.",
            "Verification activities defined for each requirement.",
            "Supplier selection."
        ],
        "answer": "Verification activities defined for each requirement."
    },
    {
        "id": "se_30",
        "question": "What does system architecture represent for a 12V Li-Ion battery?",
        "options": [
            "The complete list of purchased components.",
            "The functional and physical structure of the elements that realize system functions.",
            "The production plan."
        ],
        "answer": "The functional and physical structure of the elements that realize system functions."
    },
    {
        "id": "se_31",
        "question": "Which of the following is a stakeholder for a 12V automotive battery?",
        "options": [
            "The vehicle OEM.",
            "Only the software developer.",
            "Only the cell supplier."
        ],
        "answer": "The vehicle OEM."
    },
    {
        "id": "se_32",
        "question": "What is the purpose of requirements traceability in the V-Cycle?",
        "options": [
            "Reducing the number of requirements.",
            "Linking higher-level requirements with architecture, implementation, and verification.",
            "Eliminating testing."
        ],
        "answer": "Linking higher-level requirements with architecture, implementation, and verification."
    },
    {
        "id": "se_33",
        "question": "A system requirement states: 'Battery shall support vehicle operation during engine cranking.' What information is missing to make the requirement fully verifiable?",
        "options": [
            "The person responsible for verification.",
            "Measurable values and test conditions.",
            "Supplier name."
        ],
        "answer": "Measurable values and test conditions."
    },
    {
        "id": "se_34",
        "question": "Which activity belongs to system validation?",
        "options": [
            "Verifying PCB connections.",
            "Testing whether the system satisfies vehicle and user needs.",
            "Source code analysis."
        ],
        "answer": "Testing whether the system satisfies vehicle and user needs."
    },
    {
        "id": "se_35",
        "question": "Which of the following represents an external interface of a 12V battery?",
        "options": [
            "SoC estimation.",
            "Balancing algorithm.",
            "CAN bus connection to the vehicle."
        ],
        "answer": "CAN bus connection to the vehicle."
    },
    {
        "id": "se_36",
        "question": "According to V-Cycle principles, for the requirement 'Battery shall provide State of Charge information via CAN' which artifact must exist?",
        "options": [
            "At least one associated verification test case.",
            "Only a mechanical drawing.",
            "Only a cost analysis."
        ],
        "answer": "At least one associated verification test case."
    }
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

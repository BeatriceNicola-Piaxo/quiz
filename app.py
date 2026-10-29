import os
import json
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template, request, jsonify
import gspread
from google.oauth2.service_account import Credentials

BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "results.json"

# Set this in your environment or leave default if you want to use a local file
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "YOUR_SHEET_ID_HERE")

# Google Sheets API scope
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

app = Flask(__name__)


def get_sheet():
    credentials_path = BASE_DIR / "credentials.json"

    if not credentials_path.exists():
        raise FileNotFoundError(
            "credentials.json not found. Put the downloaded Google service account JSON file in the project root."
        )

    creds = Credentials.from_service_account_file(
        str(credentials_path),
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1


def ensure_headers(sheet):
    if not sheet.row_values(1):
        sheet.append_row(["name", "score", "submitted_at"])
    elif sheet.row_values(1) != ["name", "score", "submitted_at"]:
        current = sheet.row_values(1)
        if current:
            # if the sheet already has something else, we still add the expected header to row 1
            sheet.insert_row(["name", "score", "submitted_at"], 1)
            sheet.delete_row(2)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/submit")
def submit_score():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    score = str(payload.get("score") or "").strip()

    if not name or not score:
        return jsonify({"error": "Missing required fields: name and score"}), 400

    # Save local JSON backup
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
        sheet = get_sheet()
        ensure_headers(sheet)
        submitted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
        sheet.append_row([name, score, submitted_at])
    except Exception as exc:
        return jsonify({
            "error": f"Failed to save to Google Sheet: {str(exc)}"
        }), 500

    return jsonify({
        "message": "Score saved successfully",
        "name": name,
        "score": score,
    })


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

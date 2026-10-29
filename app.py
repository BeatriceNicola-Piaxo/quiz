from flask import Flask, render_template, request, jsonify
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests
from openpyxl import Workbook, load_workbook

BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "results.json"

# Required environment variables:
# GRAPH_ACCESS_TOKEN=...
# ONE_DRIVE_FILE_PATH=/quiz_results.xlsx
# Example: ONE_DRIVE_FILE_PATH=/quiz_results.xlsx
GRAPH_ACCESS_TOKEN = os.environ.get("GRAPH_ACCESS_TOKEN")
ONE_DRIVE_FILE_PATH = os.environ.get("ONE_DRIVE_FILE_PATH", "/quiz_results.xlsx")

app = Flask(__name__)


def graph_headers():
    if not GRAPH_ACCESS_TOKEN:
        raise RuntimeError("GRAPH_ACCESS_TOKEN is not set")
    return {
        "Authorization": f"Bearer {GRAPH_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def get_one_drive_excel_bytes():
    url = "https://graph.microsoft.com/v1.0/me/drive/root" + f":{ONE_DRIVE_FILE_PATH}:/content"
    response = requests.get(url, headers=graph_headers(), timeout=30)
    if response.status_code == 404:
        raise FileNotFoundError(f"Excel file not found in OneDrive: {ONE_DRIVE_FILE_PATH}")
    response.raise_for_status()
    return response.content


def create_excel_if_missing():
    temp_name = "quiz_results.xlsx"
    temp_path = Path(tempfile.gettempdir()) / temp_name

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Quiz Results"
    sheet.append(["name", "score", "submitted_at"])
    workbook.save(temp_path)
    return temp_path


def upload_excel_bytes(file_path: Path):
    if not GRAPH_ACCESS_TOKEN:
        raise RuntimeError("GRAPH_ACCESS_TOKEN is not set")

    with file_path.open("rb") as f:
        content = f.read()

    url = "https://graph.microsoft.com/v1.0/me/drive/root" + f":{ONE_DRIVE_FILE_PATH}:/content"
    response = requests.put(
        url,
        headers={"Authorization": f"Bearer {GRAPH_ACCESS_TOKEN}"},
        data=content,
        timeout=60,
    )
    response.raise_for_status()


def ensure_excel_exists_in_onedrive():
    try:
        get_one_drive_excel_bytes()
        return
    except FileNotFoundError:
        temp_path = create_excel_if_missing()
        upload_excel_bytes(temp_path)


def append_result_to_onedrive_excel(name, score):
    ensure_excel_exists_in_onedrive()

    temp_file = Path(tempfile.gettempdir()) / "temp_quiz_results.xlsx"
    file_bytes = get_one_drive_excel_bytes()
    temp_file.write_bytes(file_bytes)

    workbook = load_workbook(temp_file)
    sheet = workbook.active

    if sheet.max_row == 0 or sheet["A1"].value is None:
        sheet.append(["name", "score", "submitted_at"])
    elif [sheet["A1"].value, sheet["B1"].value, sheet["C1"].value] != [
        "name",
        "score",
        "submitted_at",
    ]:
        sheet.insert_rows(1)
        sheet["A1"] = "name"
        sheet["B1"] = "score"
        sheet["C1"] = "submitted_at"

    submitted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    sheet.append([name, score, submitted_at])
    workbook.save(temp_file)

    upload_excel_bytes(temp_file)


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

    # Save a local JSON copy too (optional backup)
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

    append_result_to_onedrive_excel(name, score)

    return jsonify({
        "message": "Score saved successfully",
        "name": name,
        "score": score,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

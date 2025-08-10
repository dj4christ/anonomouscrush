import os
import re
import base64
import datetime
from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

# optional: from dotenv import load_dotenv
# load_dotenv()  # only for local testing; Render will use environment variables

app = Flask(__name__)
CORS(app)  # allow cross-origin requests; restrict origin in production if you want

# CONFIG - set these as environment variables on Render
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # DO NOT commit your token
REPO_OWNER = os.getenv("REPO_OWNER", "YOUR_GITHUB_USERNAME")
REPO_NAME = os.getenv("REPO_NAME", "YOUR_REPO")
BRANCH = os.getenv("BRANCH", "main")
SUBMISSIONS_DIR = os.getenv("SUBMISSIONS_DIR", "submissions")

# simple email validation
EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

def sanitize_email_filename(email: str) -> str:
    # make a safe filename based on email (replace non-alnum with _)
    safe = re.sub(r'[^A-Za-z0-9]+', '_', email)
    return safe.strip('_').lower() + ".txt"

@app.route("/submit", methods=["POST"])
def submit():
    if not GITHUB_TOKEN:
        return jsonify({"error": "Server not configured"}), 500

    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip()
    crush_name = (data.get("crush_name") or "").strip()

    if not email or not crush_name:
        return jsonify({"error": "Missing email or crush_name"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email format"}), 400

    filename = sanitize_email_filename(email)
    path = f"{SUBMISSIONS_DIR}/{filename}"

    # 1) Check if file exists
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return jsonify({"error": "Email already submitted"}), 409
    elif r.status_code not in (404, 200):
        # other errors (rate limit, auth)
        try:
            return jsonify({"error": "GitHub check failed", "details": r.json()}), 502
        except Exception:
            return jsonify({"error": "GitHub check failed", "status": r.status_code}), 502

    # 2) Prepare content
    timestamp = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    content_text = f"Crush Name: {crush_name}\nSubmitted By: {email}\nTimestamp (UTC): {timestamp}\n"
    b64content = base64.b64encode(content_text.encode()).decode()

    payload = {
        "message": f"Add crush submission for {email}",
        "content": b64content,
        "branch": BRANCH
    }

    put_r = requests.put(url, headers=headers, json=payload)
    if put_r.status_code in (200, 201):
        return jsonify({"success": True}), 201
    else:
        try:
            return jsonify({"error": "Failed to write to GitHub", "details": put_r.json()}), 502
        except Exception:
            return jsonify({"error": "Failed to write to GitHub", "status": put_r.status_code}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import base64
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

app = Flask(__name__)

CORS(app)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # Store safely on Render/Railway
GITHUB_REPO = "dj4christ/anonomouscrush"
GITHUB_BRANCH = "main"

EMAIL_API = os.environ.get("EMAIL_API")

def send_email(email, name, subject, message):
    if not EMAIL_API:
        raise ValueError("EMAIL_API not set")

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = EMAIL_API

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": email, "name": name}],
        sender={"email": "dj4christ09@gmail.com", "name": "AnonomousCrush"},
        subject=subject,
        html_content=f"<html><body><p>{message}</p></body></html>"
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
    except ApiException as e:
        print("Error sending email:", e)


def github_get_file(path):
    """Fetch a file from GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    return None

def github_write_file(path, content, message):
    """Write a file to GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    data = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": GITHUB_BRANCH
    }
    r = requests.put(url, headers=headers, json=data)
    return r.status_code in (200, 201)


@app.route("/submit", methods=["POST"])
def submit():
    user_name = request.form.get("name")
    print(user_name)
    crush_name = request.form.get("crush")
    email = request.form.get("email")

    if not all([user_name, crush_name, email]):
        return jsonify({"error": "Missing fields"}), 400

    filename = f"submissions/{email.replace('@','_at_')}.txt"

    existing_file = github_get_file(filename)
    if existing_file:
        return jsonify({"error": "You have already submitted"}), 400

    content = f"Name: {user_name}\nCrush: {crush_name}\nEmail: {email}"
    github_write_file(filename, content, f"Add crush for {email}")

    match_found = False
    match_email = None
    match_name = None

    submissions_dir = github_get_file("data")
    if submissions_dir and isinstance(submissions_dir, list):
        for f in submissions_dir:
            if f["type"] == "file":
                file_data = requests.get(f["download_url"]).text
                if f"Name: {crush_name}" in file_data and f"Crush: {user_name}" in file_data:
                    match_found = True
                    for line in file_data.splitlines():
                        if line.startswith("Email:"):
                            match_email = line.split("Email:")[1].strip()
                        if line.startswith("Name:"):
                            match_name = line.split("Name:")[1].strip()
                    break

    if match_found and match_email:
        send_email(email, user_name, "You have a match!", f"You matched with {crush_name}!")
        send_email(match_email, match_name, "You have a match!", f"You matched with {user_name}!")

    return jsonify({"message": "Submission saved", "match": match_found})


if __name__ == "__main__":
    app.run(debug=True)

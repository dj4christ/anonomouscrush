from github import Github
import base64, requests

GITHUB_TOKEN = ""
GITHUB_REPO = ""
GITHUB_BRANCH = ""

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
# main.py
import os
import json
import base64
import tempfile
import subprocess
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Student Build API")

# Secrets
SECRET = os.getenv("APP_SECRET", "sainathshelke06@gmail.com1234567890")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # GitHub personal access token


@app.get("/")
@app.head("/")
def home():
    return {"message": "Server is running!"}


@app.post("/task")
async def handle_task(request: Request):
    data = await request.json()

    # 1️⃣ Verify secret
    if data.get("secret") != SECRET:
        return JSONResponse(status_code=403, content={"error": "Invalid secret"})

    # 2️⃣ Extract task info
    email = data.get("email")
    task = data.get("task")
    brief = data.get("brief", "")
    round_ = data.get("round")
    nonce = data.get("nonce")
    checks = data.get("checks", [])
    attachments = data.get("attachments", [])
    evaluation_url = data.get("evaluation_url")

    print(f"Received task: {task} for {email}, round {round_}")

    # 3️⃣ Prepare temporary folder for app
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save attachments
        for attach in attachments:
            filename = attach["name"]
            filedata = base64.b64decode(attach["url"].split(",")[1])
            with open(os.path.join(tmpdir, filename), "wb") as f:
                f.write(filedata)

        # Generate minimal HTML app
        index_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{task} - Round {round_}</title>
        </head>
        <body>
            <h1>{brief}</h1>
            <p>Round {round_} completed successfully.</p>
        </body>
        </html>
        """
        with open(os.path.join(tmpdir, "index.html"), "w") as f:
            f.write(index_html)

        # README.md
        with open(os.path.join(tmpdir, "README.md"), "w") as f:
            f.write(f"# {task}\n\n{brief}\n\nRound {round_}")

        # MIT LICENSE
        with open(os.path.join(tmpdir, "LICENSE"), "w") as f:
            f.write("MIT License")

        # 4️⃣ Push to GitHub
        repo_name = f"{task.replace(' ', '-')}-round{round_}"
        repo_url = f"https://github.com/{email.split('@')[0]}/{repo_name}.git"

        try:
            # Create repo via GitHub API
            headers = {"Authorization": f"token {GITHUB_TOKEN}"}
            payload = {"name": repo_name, "private": False}
            r = requests.post("https://api.github.com/user/repos", headers=headers, json=payload)
            r.raise_for_status()

            # Initialize git, commit, push
            subprocess.run(["git", "init"], cwd=tmpdir, check=True)
            subprocess.run(["git", "add", "."], cwd=tmpdir, check=True)
            subprocess.run(["git", "commit", "-m", f"Round {round_}"], cwd=tmpdir, check=True)
            subprocess.run(["git", "branch", "-M", "main"], cwd=tmpdir, check=True)
            subprocess.run(["git", "remote", "add", "origin", repo_url], cwd=tmpdir, check=True)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=tmpdir, check=True)

            pages_url = f"https://{email.split('@')[0]}.github.io/{repo_name}/"
        except Exception as e:
            print("GitHub push failed:", e)
            pages_url = None

    # 5️⃣ Notify evaluation_url with retries
    def post_evaluation(payload, url, retries=5):
        for attempt in range(retries):
            try:
                resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload)
                if resp.status_code == 200:
                    return True
            except Exception as e:
                print("Evaluation POST attempt failed:", e)
            import time
            time.sleep(2 ** attempt)  # exponential backoff
        return False

    if evaluation_url:
        payload = {
            "email": email,
            "task": task,
            "round": round_,
            "nonce": nonce,
            "repo_url": repo_url,
            "commit_sha": "latest",
            "pages_url": pages_url,
        }
        post_evaluation(payload, evaluation_url)

    # 6️⃣ Respond to caller
    return {
        "status": "ok",
        "email": email,
        "task": task,
        "round": round_,
        "nonce": nonce
    }

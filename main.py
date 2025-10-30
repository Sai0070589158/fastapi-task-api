# main.py
import os
import json
import time
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from github import Github, GithubException
from groq import Groq  # ✅ Use Groq instead of OpenAI

# -------------------------
# Configuration
# -------------------------
app = FastAPI(title="Student Build API")

SECRET = os.getenv("APP_SECRET", "sainathshelke06@gmail.com1234567890")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USER = os.getenv("GITHUB_USER", "Sai0070589158")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq client (free, OpenAI-compatible)
client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.2-70b-text-preview"

MIT_LICENSE = """MIT License

Copyright (c) 2025 {user}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
"""

# -------------------------
# GitHub Helper Functions
# -------------------------
def enable_pages(repo_name: str):
    """Enable GitHub Pages for a repo and return its URL."""
    url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/pages"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    body = {"source": {"branch": "main"}}
    r = requests.post(url, headers=headers, json=body)

    if r.status_code in (201, 202, 409):
        print(f"✅ GitHub Pages enabled for {repo_name}")
        return f"https://{GITHUB_USER}.github.io/{repo_name}/"
    else:
        print("❌ GitHub Pages setup failed:", r.text)
        return None


def create_or_update_repo(task_name: str, repo_files: dict):
    """Create or update the GitHub repo with provided files."""
    g = Github(GITHUB_TOKEN)
    user = g.get_user()
    repo_url, pages_url, commit_sha = None, None, None

    try:
        try:
            repo = user.get_repo(task_name)
            print(f"Repo {task_name} exists — updating files.")
        except GithubException:
            repo = user.create_repo(
                name=task_name,
                private=False,
                description=f"Repo for task {task_name}",
                auto_init=True
            )
            print(f"Created new repo: {repo.html_url}")

        for filename, content in repo_files.items():
            try:
                existing = repo.get_contents(filename)
                commit = repo.update_file(
                    path=filename,
                    message=f"Update {filename}",
                    content=content,
                    sha=existing.sha
                )
            except GithubException:
                commit = repo.create_file(
                    path=filename,
                    message=f"Add {filename}",
                    content=content
                )
            commit_sha = commit["commit"].sha

        repo_url = repo.html_url
        pages_url = enable_pages(repo.name)
    except GithubException as e:
        print("GitHub error:", e)

    return repo_url, pages_url, commit_sha


def ping_evaluation_api(evaluation_url, payload):
    """Retry pinging the evaluation API with exponential backoff."""
    headers = {"Content-Type": "application/json"}
    for delay in [1, 2, 4, 8]:
        try:
            r = requests.post(evaluation_url, headers=headers, json=payload)
            if r.status_code == 200:
                print("✅ Evaluation API notified.")
                return True
            else:
                print("⚠️ Eval API failed:", r.status_code, r.text)
        except Exception as e:
            print("⚠️ Eval ping error:", e)
        time.sleep(delay)
    return False


# -------------------------
# LLM App Generator
# -------------------------
def generate_app_files(task, brief):
    """Use Groq Llama-3.1-70B to generate a small web app."""
    prompt = f"""
You are an expert full-stack web app generator.
Build a self-contained web app for this task.

Task: {task}
Brief: {brief}

Output must be a JSON object with filenames as keys and code as values.
Include at least index.html (required). Use simple HTML/CSS/JS.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    content = response.choices[0].message.content.strip()
    try:
        files = json.loads(content)
        print("✅ Parsed LLM JSON output successfully.")
    except Exception:
        files = {"index.html": content}
        print("⚠️ LLM returned non-JSON — wrapping in HTML.")

    return files


# -------------------------
# Routes
# -------------------------
@app.get("/")
def home():
    return {"message": "✅ Server is running and healthy."}


@app.head("/")
def head_home():
    """Used by Render and cron to keep service awake (no LLM calls)."""
    return Response(status_code=200)


@app.get("/keep-alive")
def keep_alive():
    """Ping this URL every 10-15 minutes via cron — it won’t trigger LLM."""
    print("⚙️ Keep-alive ping received.")
    return {"status": "alive"}


@app.post("/task")
async def handle_task(request: Request):
    """Main endpoint for handling round 1 or 2 app generation requests."""
    data = await request.json()
    if data.get("secret") != SECRET:
        return JSONResponse(status_code=403, content={"error": "Invalid secret"})

    email = data.get("email")
    task = data.get("task")
    brief = data.get("brief", "")
    round_ = data.get("round", 1)
    nonce = data.get("nonce")
    evaluation_url = data.get("evaluation_url")

    print(f"🚀 Handling round {round_} for task {task}")

    # LLM generation
    app_files = generate_app_files(task, brief)

    # Add license and readme
    app_files["README.md"] = f"# {task}\n\n**Brief:** {brief}\n\n**Round:** {round_}\n\nMIT License."
    app_files["LICENSE"] = MIT_LICENSE.format(user=GITHUB_USER)

    # Deploy to GitHub
    repo_url, pages_url, commit_sha = create_or_update_repo(task, app_files)

    result = {
        "status": "ok",
        "email": email,
        "task": task,
        "round": round_,
        "nonce": nonce,
        "repo_url": repo_url,
        "pages_url": pages_url,
        "commit_sha": commit_sha
    }

    # Notify evaluator
    if evaluation_url:
        ping_evaluation_api(evaluation_url, result)

    return result


import os
import json
import time
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from github import Github, GithubException
from openai import OpenAI  # Requires: pip install openai

app = FastAPI(title="Student Build API")

# -------------------------
# Environment Variables
# -------------------------
SECRET = os.getenv("APP_SECRET", "sainathshelke06@gmail.com1234567890")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USER = os.getenv("GITHUB_USER", "Sai0070589158")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Your OpenAI API key
MODEL = os.getenv("MODEL", "gpt-4o-mini")  # Or 'gpt-4o' if available

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
# GitHub Functions
# -------------------------
def enable_pages(repo_name: str):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/pages"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    r = requests.post(url, headers=headers, json={"source": {"branch": "main"}})

    if r.status_code in (201, 202, 409):
        return f"https://{GITHUB_USER}.github.io/{repo_name}/"
    else:
        print("⚠️ GitHub Pages setup failed:", r.json())
        return None


def create_or_update_repo(task_name: str, repo_files: dict):
    g = Github(GITHUB_TOKEN)
    user = g.get_user()
    repo_url, pages_url, commit_sha = None, None, None

    try:
        try:
            repo = user.get_repo(task_name)
            print(f"Repo {task_name} exists.")
        except GithubException:
            repo = user.create_repo(
                name=task_name,
                private=False,
                description=f"Repo for task {task_name}",
                auto_init=True,
            )
            print(f"✅ Created repo: {repo.html_url}")

        for filename, content in repo_files.items():
            try:
                existing = repo.get_contents(filename)
                commit = repo.update_file(
                    path=filename,
                    message=f"Update {filename}",
                    content=content,
                    sha=existing.sha,
                )
            except GithubException:
                commit = repo.create_file(
                    path=filename,
                    message=f"Add {filename}",
                    content=content,
                )
            commit_sha = commit["commit"].sha

        repo_url = repo.html_url
        pages_url = enable_pages(repo.name)

    except GithubException as e:
        print("❌ GitHub error:", e)

    return repo_url, pages_url, commit_sha


def ping_evaluation_api(evaluation_url, payload):
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
            print("❌ Eval ping error:", e)
        time.sleep(delay)
    return False


# -------------------------
# LLM Code Generator
# -------------------------
def generate_app_files(task: str, brief: str):
    """Uses GPT to generate HTML, CSS, and JS for a web app."""
    if not OPENAI_API_KEY:
        print("⚠️ No OpenAI API key provided, using fallback page.")
        return {
            "index.html": f"<html><body><h1>{brief}</h1><p>Task: {task}</p></body></html>",
        }

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
You are a web app generator. Build a small functional HTML/CSS/JS app based on this description:

Task: {task}
Brief: {brief}

Requirements:
- Use modern responsive HTML5.
- Include relevant CSS and minimal JavaScript if needed.
- No external dependencies or frameworks.
- The app must render a working UI, not just text.
Return only file contents in JSON format with filenames as keys.
Example:
{{
  "index.html": "...",
  "style.css": "...",
  "script.js": "..."
}}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    try:
        text = response.choices[0].message.content.strip()
        files = json.loads(text)
        return files
    except Exception as e:
        print("⚠️ LLM output parse error:", e)
        return {
            "index.html": f"<html><body><h1>{brief}</h1><p>Task: {task}</p></body></html>",
        }


# -------------------------
# Routes
# -------------------------
@app.get("/")
def home():
    return {"message": "Server running successfully"}


@app.head("/")
def head_home():
    return Response(status_code=200)


@app.post("/task")
async def handle_task(request: Request):
    data = await request.json()
    if data.get("secret") != SECRET:
        return JSONResponse(status_code=403, content={"error": "Invalid secret"})

    email = data.get("email")
    task = data.get("task")
    brief = data.get("brief", "")
    round_ = data.get("round", 1)
    nonce = data.get("nonce")
    evaluation_url = data.get("evaluation_url")

    print(f"🧩 Received task: {task} | Round: {round_}")

    # 🔹 Generate files via LLM
    app_files = generate_app_files(task, brief)

    # Add README and LICENSE
    app_files["README.md"] = f"# {task}\n\n**Brief:** {brief}\n\n**Round:** {round_}\n\nMIT License included."
    app_files["LICENSE"] = MIT_LICENSE.format(user=GITHUB_USER)

    repo_url, pages_url, commit_sha = create_or_update_repo(task, app_files)

    result = {
        "status": "ok",
        "email": email,
        "task": task,
        "round": round_,
        "nonce": nonce,
        "repo_url": repo_url,
        "pages_url": pages_url,
        "commit_sha": commit_sha,
    }

    if evaluation_url:
        ping_evaluation_api(evaluation_url, result)

    return result


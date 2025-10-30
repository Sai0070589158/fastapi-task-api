# main.py
import os
import json
import time
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from github import Github, GithubException

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

app = FastAPI(title="Student Build API")

# -------------------------
# Environment
# -------------------------
SECRET = os.getenv("APP_SECRET", "sainathshelke06@gmail.com1234567890")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USER = os.getenv("GITHUB_USER", "Sai0070589158")

# -------------------------
# GitHub Helpers
# -------------------------
def enable_pages(repo_name: str):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/pages"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    body = {"source": {"branch": "main"}}
    r = requests.post(url, headers=headers, json=body)
    if r.status_code in (201, 202):
        return f"https://{GITHUB_USER}.github.io/{repo_name}/"
    print("GitHub Pages setup failed:", r.text)
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
                auto_init=True
            )
            print(f"Created repo: {repo.html_url}")

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
    headers = {"Content-Type": "application/json"}
    for delay in [1, 2, 4, 8]:
        try:
            r = requests.post(evaluation_url, headers=headers, json=payload)
            if r.status_code == 200:
                print("✅ Evaluation API notified.")
                return True
            else:
                print("Evaluation API failed:", r.status_code, r.text)
        except Exception as e:
            print("Eval ping error:", e)
        time.sleep(delay)
    return False

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

    repo_name = f"{task}"
    print(f"Handling round {round_} for task {task}")

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>{task} - Round {round_}</title>
      <style>
        body {{ font-family: Arial; text-align:center; background:#fafafa; padding:40px; }}
        h1 {{ color:#333; }}
        p {{ color:#555; }}
      </style>
    </head>
    <body>
      <h1>{brief}</h1>
      <p>Task: <b>{task}</b> | Round: <b>{round_}</b></p>
    </body>
    </html>
    """

    repo_files = {
        "README.md": f"# {task}\n\n**Brief:** {brief}\n\n**Round:** {round_}\n\nThis project is licensed under the MIT License.",
        "index.html": html,
        "LICENSE": MIT_LICENSE.format(user=GITHUB_USER)
    }

    repo_url, pages_url, commit_sha = create_or_update_repo(repo_name, repo_files)

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

    if evaluation_url:
        ping_evaluation_api(evaluation_url, result)

    return result


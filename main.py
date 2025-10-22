# main.py
import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from github import Github, GithubException

app = FastAPI(title="Student Build API")

# -------------------------
# Environment Variables
# -------------------------
SECRET = os.getenv("APP_SECRET", "sainathshelke06@gmail.com1234567890")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Your GitHub Personal Access Token
GITHUB_USER = os.getenv("GITHUB_USER", "Sai0070589158")  # GitHub username

# -------------------------
# Helper: Enable GitHub Pages
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
    else:
        print("GitHub Pages setup failed:", r.json())
        return None

# -------------------------
# Helper: Create/Update Repo
# -------------------------
def create_or_update_repo(task_name: str, repo_files: dict):
    g = Github(GITHUB_TOKEN)
    user = g.get_user()
    repo_url, pages_url = None, None

    try:
        # Check if repo exists
        try:
            repo = user.get_repo(task_name)
            print(f"Repo {task_name} exists. Updating...")
        except GithubException:
            repo = user.create_repo(
                name=task_name,
                private=False,
                description=f"Repo for task {task_name}",
                auto_init=True  # ensure main branch exists
            )
            print(f"Created repo: {repo.html_url}")

        # Commit or update files (force commit)
        for filename, content in repo_files.items():
            try:
                existing_file = repo.get_contents(filename)
                repo.update_file(
                    path=filename,
                    message=f"Update {filename}",
                    content=content,
                    sha=existing_file.sha
                )
            except GithubException:
                repo.create_file(path=filename, message=f"Add {filename}", content=content)

        # Return repo URL
        repo_url = repo.html_url

        # Enable GitHub Pages
        pages_url = enable_pages(repo.name)
        if pages_url:
            print(f"GitHub Pages available at {pages_url}")

    except GithubException as e:
        print("GitHub push failed:", e)

    return repo_url, pages_url

# -------------------------
# Routes
# -------------------------
@app.get("/")
def home():
    return {"message": "Server is running!"}

@app.head("/")
def head_home():
    return Response(status_code=200)

@app.post("/task")
async def handle_task(request: Request):
    data = await request.json()

    # 1️⃣ Verify secret
    if data.get("secret") != SECRET:
        return JSONResponse(status_code=403, content={"error": "Invalid secret"})

    # 2️⃣ Extract task info
    email = data.get("email")
    task = data.get("task")
    brief = data.get("brief")
    round_ = data.get("round")
    nonce = data.get("nonce")

    print(f"Received task: {task} for {email}, round {round_}")

    # 3️⃣ Prepare minimal repo files
    repo_name = f"{task}-{round_}"
    repo_files = {
        "README.md": f"# Task: {task}\n\nBrief: {brief}\nRound: {round_}\n",
        "index.html": f"<html><body><h1>{brief}</h1></body></html>"
    }

    # 4️⃣ Create or update GitHub repo
    repo_url, pages_url = create_or_update_repo(repo_name, repo_files)

    # 5️⃣ Respond with JSON
    return {
        "status": "ok",
        "email": email,
        "task": task,
        "round": round_,
        "nonce": nonce,
        "repo_url": repo_url,
        "pages_url": pages_url
    }

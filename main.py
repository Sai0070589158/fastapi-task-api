# main.py
import os
import json
import shutil
import time
import uuid
import base64
import hashlib
import tempfile
from dotenv import load_dotenv
load_dotenv()
import subprocess
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional

import requests
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path

app = FastAPI(title="Student Build API")

# Config from env
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
EXPECTED_SECRET = os.environ.get("EXPECTED_SECRET")  # or load mapping
GIT_USER_NAME = os.environ.get("GIT_USER_NAME", "student-bot")
GIT_USER_EMAIL = os.environ.get("GIT_USER_EMAIL", "student@example.com")
GITHUB_API = "https://api.github.com"

if GITHUB_TOKEN is None:
    print("WARNING: GITHUB_TOKEN not set; repo creation will fail unless gh cli is used with auth.")


# ------------------------------
# Request / Response models
# ------------------------------
class Attachment(BaseModel):
    name: str
    url: str  # data:... or http(s)


class BuildRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: List[str]
    evaluation_url: str
    attachments: Optional[List[Attachment]] = []


class BuildResponse(BaseModel):
    status: str
    message: str


# ------------------------------
# Helpers
# ------------------------------
def verify_secret(provided: str) -> bool:
    # Simple equality check — replace with a database lookup if multiple secrets
    expected = EXPECTED_SECRET or ""
    return provided == expected


def save_attachments(attachments: List[Attachment], target_dir: Path) -> List[Path]:
    saved = []
    for a in attachments:
        data = a.url
        if data.startswith("data:"):
            # data URI
            header, b64 = data.split(",", 1)
            raw = base64.b64decode(b64)
            out = target_dir / a.name
            out.write_bytes(raw)
            saved.append(out)
        else:
            # remote URL - download
            r = requests.get(data, timeout=10)
            r.raise_for_status()
            out = target_dir / a.name
            out.write_bytes(r.content)
            saved.append(out)
    return saved


def slugify_repo_name(task_id: str, email: str) -> str:
    # generate unique public-looking name, keep short
    h = hashlib.sha1(f"{task_id}:{email}:{time.time()}".encode()).hexdigest()[:8]
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in task_id.lower())[:60]
    return f"{safe}-{h}"


def run(cmd, cwd=None, check=True, capture_output=False, env=None):
    if isinstance(cmd, str):
        cmd = cmd.split()
    res = subprocess.run(cmd, cwd=cwd, check=check, capture_output=capture_output, text=True, env=env)
    return res.stdout if capture_output else None


def create_local_repo(workdir: Path, repo_name: str, git_email: str = GIT_USER_EMAIL, git_name: str = GIT_USER_NAME):
    run(f"git init", cwd=str(workdir))
    run(f"git config user.email \"{git_email}\"", cwd=str(workdir))
    run(f"git config user.name \"{git_name}\"", cwd=str(workdir))


def commit_all_and_push(workdir: Path, owner: str, repo: str, remote_url: str, initial_branch="main"):
    run(f"git add --all", cwd=str(workdir))
    run(f"git commit -m \"Initial commit\"", cwd=str(workdir))
    run(f"git branch -M {initial_branch}", cwd=str(workdir))
    run(f"git remote add origin {remote_url}", cwd=str(workdir))
    run(f"git push -u origin {initial_branch}", cwd=str(workdir))


def ensure_no_secrets_in_history(workdir: Path):
    # Basic check: grep for "GITHUB_TOKEN" or "PRIVATE_KEY" in files
    for p in workdir.rglob("*"):
        if p.is_file():
            try:
                text = p.read_text(errors="ignore")
                if "GITHUB_TOKEN" in text or "PRIVATE_KEY" in text or "SECRET" in text:
                    raise RuntimeError(f"Possible secret found in file {p}")
            except Exception:
                pass


def create_mit_license(workdir: Path, author="Student"):
    mit = """MIT License

Copyright (c) {year} {author}

Permission is hereby granted, free of charge, to any person obtaining a copy...
""".format(year=time.strftime("%Y"), author=author)
    (workdir / "LICENSE").write_text(mit)


def create_readme(workdir: Path, brief: str, repo_url: str, pages_url: str, commit_sha: str):
    content = f"""# Student submission

**Brief:** {brief}

**Repo:** {repo_url}  
**Pages:** {pages_url}  
**Commit:** {commit_sha}

## Setup
Open the pages URL.

## Explanation
This project was generated to satisfy the brief.
"""
    (workdir / "README.md").write_text(content)


# ------------------------------
# LLM placeholder generator
# ------------------------------
def generate_app_with_llm(brief: str, attachments_dir: Path, out_dir: Path):
    """
    Replace this function with actual LLM-based generator.
    For now: produce a single-page app that:
    - Loads ?url=... or uses first attachment if present
    - Displays the image and a placeholder 'solved' text
    """
    index_html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width"/>
  <title>Task preview</title>
  <style>
    body {{ font-family: system-ui, sans-serif; padding: 2rem; }}
    img {{ max-width: 80%; height: auto; display:block; margin:1rem 0; }}
    #solved {{ font-weight: bold; color: green; }}
  </style>
</head>
<body>
  <h1>Generated app</h1>
  <div>
    <label>Image source: <code id="src"></code></label>
    <div><img id="img" alt="captcha sample"/></div>
    <div>Solved text: <span id="solved">—</span></div>
  </div>
  <script>
    async function load() {{
      const params = new URLSearchParams(location.search);
      let src = params.get('url');
      if (!src) {{
        // fallback to embedded attachment if present
        const attachments = {json.dumps([a.name for a in (attachments_dir.iterdir() if attachments_dir.exists() else [])])};
        if (attachments.length) src = attachments[0];
      }}
      document.getElementById('src').textContent = src || 'none';
      const img = document.getElementById('img');
      if (src && src.startsWith('data:')) {{
        img.src = src;
        document.getElementById('solved').textContent = 'SAMPLE-SOLUTION';
      }} else if (src) {{
        img.src = src;
        document.getElementById('solved').textContent = 'SAMPLE-SOLUTION';
      }} else {{
        document.getElementById('solved').textContent = 'no-source';
      }}
    }}
    load();
  </script>
</body>
</html>
"""
    (out_dir / "index.html").write_text(index_html)

    # if attachments_dir had files, copy them into out_dir
    if attachments_dir.exists():
        for f in attachments_dir.iterdir():
            if f.is_file():
                shutil.copy(f, out_dir / f.name)


# ------------------------------
# GitHub API helpers (create repo, enable pages)
# ------------------------------
def create_github_repo(repo_name: str, private: bool = False) -> Dict[str, Any]:
    """
    Creates a public repo under the authenticated user.
    Returns the repo JSON.
    """
    assert GITHUB_TOKEN, "GITHUB_TOKEN required for REST-based repo creation"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    payload = {"name": repo_name, "private": private, "auto_init": False}
    r = requests.post(f"{GITHUB_API}/user/repos", json=payload, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()


def enable_github_pages(owner: str, repo: str, branch: str = "main", path: str = "/"):
    """Use the Pages API to set source to branch/root."""
    assert GITHUB_TOKEN
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    body = {"source": {"branch": branch, "path": path}}
    # API endpoint: PUT /repos/{owner}/{repo}/pages
    r = requests.put(f"{GITHUB_API}/repos/{owner}/{repo}/pages", json=body, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()


def get_commit_sha(owner: str, repo: str, ref: str = "heads/main"):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    r = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/git/ref/{ref}", headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()["object"]["sha"]


# ------------------------------
# Evaluation POST with exponential backoff
# ------------------------------
def post_evaluation_with_backoff(payload: dict, url: str, max_attempts=6):
    attempt = 0
    wait = 1
    headers = {"Content-Type": "application/json"}
    while attempt < max_attempts:
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                return True, r.text
            else:
                attempt += 1
                time.sleep(wait)
                wait *= 2
        except Exception as e:
            attempt += 1
            time.sleep(wait)
            wait *= 2
    return False, "max attempts reached"


# ------------------------------
# Main endpoint
# ------------------------------
@app.post("/api-endpoint", response_model=BuildResponse)
async def receive_build(req: Request, background_tasks: BackgroundTasks):
    body = await req.json()
    try:
        build = BuildRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    # Verify secret
    if not verify_secret(build.secret):
        raise HTTPException(status_code=403, detail="Invalid secret")

    # Acknowledge quickly with 200
    resp = {"status": "accepted", "message": "Build started"}
    # Do the heavy lifting in background to allow quick 200 if desired.
    # BUT the spec requires POST to evaluation_url within 10 minutes.
    # We'll spawn background task but perform the push & evaluation post there.
    background_tasks.add_task(do_build_and_notify, build.dict())
    return resp


def do_build_and_notify(build: Dict[str, Any]):
    """
    Does the end-to-end process synchronously in this function:
    - Generates app
    - Creates repo & pushes
    - Enables Pages
    - Posts evaluation payload
    """
    br = BuildRequest(**build)
    tmp = Path(tempfile.mkdtemp(prefix="student-build-"))
    attachments_dir = tmp / "attachments"
    out_dir = tmp / "app"
    attachments_dir.mkdir(exist_ok=True)
    out_dir.mkdir(exist_ok=True)

    try:
        # Save attachments
        saved = save_attachments(br.attachments or [], attachments_dir)

        # Generate code with LLM (placeholder)
        generate_app_with_llm(br.brief, attachments_dir, out_dir)

        # Add license & readme
        create_mit_license(out_dir, author=br.email)
        # repo name
        repo_name = slugify_repo_name(br.task, br.email)
        # local git repo
        create_local_repo(out_dir, repo_name)

        # basic safety check for secrets in files
        try:
            ensure_no_secrets_in_history(out_dir)
        except Exception as e:
            # abort: do not push secrets
            print("Secret detected, aborting push:", e)
            return

        # create remote repo (REST)
        try:
            repo_json = create_github_repo(repo_name, private=False)
            remote_clone_url = repo_json.get("ssh_url") or repo_json.get("clone_url")
            owner = repo_json["owner"]["login"]
            repo_full = repo_json["full_name"]
        except Exception as e:
            print("Failed to create repo via REST, try gh CLI fallback:", e)
            # Fallback to `gh repo create` if gh CLI is present
            run(f"gh repo create {repo_name} --public --source={out_dir} --remote=origin --push", cwd=str(out_dir))
            # extract owner from git config
            # NOTE: adjust as needed for your environment
            remote = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=str(out_dir)).decode().strip()
            if remote.endswith(".git"):
                remote = remote[:-4]
            if remote.startswith("git@github.com:"):
                owner = remote.split(":")[1].split("/")[0]
                repo_full = remote.split(":")[1]
                remote_clone_url = remote
            else:
                owner = remote.split("/")[-2]
                repo_full = "/".join(remote.split("/")[-2:])
                remote_clone_url = remote

        # commit & push
        try:
            commit_all_and_push(out_dir, owner, repo_name, remote_clone_url, initial_branch="main")
        except Exception as e:
            print("Push failed:", e)
            # If SSH/HTTPS auth problems, surface and abort
            return

        # Enable GitHub Pages
        try:
            pages = enable_github_pages(owner, repo_name, branch="main", path="/")
            pages_url = f"https://{owner}.github.io/{repo_name}/"
        except Exception as e:
            print("Enabling pages failed (may need to wait for build):", e)
            pages_url = f"https://{owner}.github.io/{repo_name}/"

        # find commit sha
        try:
            commit_sha = get_commit_sha(owner, repo_name)
        except Exception:
            commit_sha = "unknown"

        # create README with links & commit info
        repo_url = f"https://github.com/{owner}/{repo_name}"
        create_readme(out_dir, br.brief, repo_url, pages_url, commit_sha)
        # push updated README
        try:
            run("git add README.md LICENSE", cwd=str(out_dir))
            run('git commit -m "Add README and LICENSE"', cwd=str(out_dir))
            run("git push", cwd=str(out_dir))
        except Exception:
            pass

        # Build evaluation payload and post with backoff
        eval_payload = {
            "email": br.email,
            "task": br.task,
            "round": br.round,
            "nonce": br.nonce,
            "repo_url": repo_url,
            "commit_sha": commit_sha,
            "pages_url": pages_url,
        }
        ok, result_text = post_evaluation_with_backoff(eval_payload, br.evaluation_url)
        if not ok:
            print("Evaluation POST failed after retries:", result_text)
        else:
            print("Evaluation POST succeeded.")
    finally:
        # cleanup tmp dir - keep for debugging if needed
        try:
            shutil.rmtree(tmp)
        except Exception:
            pass
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Server is running!"}
    return {"message": "Server is running!"}

app = FastAPI()

SECRET = os.getenv("APP_SECRET", "my-secret")  # you’ll set this in Render or locally

@app.get("/")
def home():
    return {"message": "Server is running!"}

@app.post("/task")
async def handle_task(request: Request):
    data = await request.json()

    # 1️⃣ Verify the secret
    if data.get("secret") != SECRET:
        return JSONResponse(status_code=403, content={"error": "Invalid secret"})

    # 2️⃣ Extract useful info
    email = data.get("email")
    task = data.get("task")
    brief = data.get("brief")
    round_ = data.get("round")
    nonce = data.get("nonce")

    # 3️⃣ Print/log the data for now
    print("Received task:", task, "for", email)

    # 4️⃣ Respond OK
    return {
        "status": "ok",
        "email": email,
        "task": task,
        "round": round_,
        "nonce": nonce
    }



# ------------------------------
# evaluation_url endpoint (for instructor server)
# ------------------------------
# The spec requires instructors to implement such an endpoint.
# We provide an example implementation below (not mounted by default).
#
# @app.post("/evaluation-receive")
# def evaluation_receive(payload: dict):
#     # validate that task exists in tasks table etc.
#     # insert into repos table then return 200
#     return {"ok": True}
#
# ------------------------------
# Run with: uvicorn main:app --host 0.0.0.0 --port 8000
# ------------------------------

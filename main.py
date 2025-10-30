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
model="llama-3.3-70b-versatile"

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
    """Use Groq Llama model to generate a high-quality web app."""
    prompt = f"""
You are an expert front-end developer and web designer.

Generate a **modern, visually stunning, responsive web app** in English.
Follow this request:

Task: {task}
Brief: {brief}

Design expectations:
- Use HTML5, CSS3 (Flexbox/Grid), and vanilla JS
- Include a gradient header (blue → purple), modern fonts, and hover animations
- Must be responsive and mobile-friendly
- Include a hero section, projects grid, about section, and footer
- Output a JSON object with 3 keys: "index.html", "styles.css", and "script.js"
- Each file should contain realistic, production-quality code
- Keep code indentation and line breaks intact
- Do not include any explanatory text outside JSON
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile", 
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    content = response.choices[0].message.content.strip()
       # 🧩 Fix: Extract only JSON content safely
    json_start = content.find("{")
    json_end = content.rfind("}") + 1
    if json_start != -1 and json_end != -1:
        try:
            content_json = content[json_start:json_end]
            files = json.loads(content_json)
        except json.JSONDecodeError:
            files = {"index.html": content}
    else:
        files = {"index.html": content}

    return files
# -------------------------
# Visual Enhancement Helper
# -------------------------
def enhance_visuals(app_files: dict) -> dict:
    """Enhance the generated HTML and CSS with premium modern visuals and interactivity."""
    html_code = app_files.get("index.html", "")
    css_code = app_files.get("styles.css", "")

    # ✅ Inject Google Fonts, Meta, and Base Styles
    if "<head>" in html_code:
        html_code = html_code.replace(
            "<head>",
            """<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
      html { scroll-behavior: smooth; }
      body {
        font-family: 'Poppins', sans-serif;
        transition: background 0.6s ease, color 0.6s ease;
        overflow-x: hidden;
      }
      ::selection {
        background: #8e44ad;
        color: white;
      }
    </style>
"""
        )

    # ✅ Add Modern Enhanced CSS
    css_code += """
/* --- Enhanced Modern Visuals --- */
:root {
  --primary: #8e44ad;
  --secondary: #007bff;
  --text: #333;
  --bg: #f9f9f9;
  --dark-bg: #121212;
  --dark-text: #f0f0f0;
}

body {
  background: var(--bg);
  color: var(--text);
}

/* Glassmorphism Header with Gradient Animation */
header {
  background: linear-gradient(270deg, var(--secondary), var(--primary));
  background-size: 400% 400%;
  animation: gradientShift 8s ease infinite;
  color: white;
  text-align: center;
  padding: 2rem 1rem;
  border-bottom: 2px solid rgba(255,255,255,0.2);
  backdrop-filter: blur(12px);
  box-shadow: 0 4px 30px rgba(0,0,0,0.2);
}
@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* Navbar */
nav {
  display: flex;
  justify-content: center;
  gap: 2rem;
  margin-top: 1rem;
}
nav a {
  color: white;
  text-decoration: none;
  font-weight: 600;
  position: relative;
}
nav a::after {
  content: '';
  position: absolute;
  left: 0; bottom: -4px;
  width: 0; height: 2px;
  background: white;
  transition: width 0.3s;
}
nav a:hover::after {
  width: 100%;
}

/* Section Fade-in + Parallax */
section {
  padding: 4rem 2rem;
  animation: fadeUp 1s ease-in;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(6px);
  margin: 2rem auto;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.1);
  max-width: 1100px;
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(40px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Project Cards */
.project-card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  border-radius: 16px;
  overflow: hidden;
  background: white;
}
.project-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 0 8px 30px rgba(142,68,173,0.3);
}

/* Footer */
footer {
  text-align: center;
  padding: 2rem;
  background: linear-gradient(270deg, var(--primary), var(--secondary));
  color: white;
  font-size: 0.9rem;
}

/* Dark Mode */
.dark-mode {
  background: var(--dark-bg);
  color: var(--dark-text);
}
.dark-mode header {
  box-shadow: 0 0 20px rgba(142,68,173,0.6);
}
.dark-mode section {
  background: rgba(255,255,255,0.05);
  box-shadow: 0 0 20px rgba(255,255,255,0.1);
}
.dark-mode footer {
  background: linear-gradient(270deg, #1a1a1a, #3a3a3a);
}

/* Scroll reveal animation */
.reveal {
  opacity: 0;
  transform: translateY(50px);
  transition: all 0.8s ease;
}
.reveal.active {
  opacity: 1;
  transform: translateY(0);
}

/* Back to top button */
#backToTop {
  position: fixed;
  bottom: 25px;
  right: 25px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 50%;
  padding: 14px;
  cursor: pointer;
  font-size: 20px;
  display: none;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  transition: background 0.3s;
}
#backToTop:hover {
  background: var(--secondary);
}
"""

    # ✅ Add interactivity and dark mode persistence
    if "</body>" in html_code:
        html_code = html_code.replace(
            "</body>",
            """<button id="modeToggle" title="Toggle dark mode">🌙</button>
<button id="backToTop" title="Back to top">⬆</button>

<script>
// --- Dark Mode with Persistence ---
const toggle = document.getElementById('modeToggle');
const userPref = localStorage.getItem('theme');
if (userPref === 'dark') document.body.classList.add('dark-mode');

toggle.addEventListener('click', () => {
  document.body.classList.toggle('dark-mode');
  const mode = document.body.classList.contains('dark-mode') ? 'dark' : 'light';
  localStorage.setItem('theme', mode);
  toggle.textContent = mode === 'dark' ? '☀️' : '🌙';
});

// --- Scroll Reveal Effect ---
window.addEventListener('scroll', () => {
  document.querySelectorAll('.reveal').forEach(el => {
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight - 100) el.classList.add('active');
  });
});

// --- Back to Top Button ---
const backToTop = document.getElementById('backToTop');
window.addEventListener('scroll', () => {
  backToTop.style.display = window.scrollY > 300 ? 'block' : 'none';
});
backToTop.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});
</script>
</body>"""
        )

    app_files["index.html"] = html_code
    app_files["styles.css"] = css_code
    return app_files

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
    app_files = enhance_visuals(app_files)

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


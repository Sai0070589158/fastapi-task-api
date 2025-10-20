# main.py
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Student Build API")

# Secret (set in Render or locally)
SECRET = os.getenv("APP_SECRET", "my-secret")


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

    # 3️⃣ Print/log for debugging
    print("Received task:", task, "for", email)

    # 4️⃣ Respond with JSON
    return {
        "status": "ok",
        "email": email,
        "task": task,
        "round": round_,
        "nonce": nonce
    }

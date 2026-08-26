import os
import sys
from pathlib import Path

# Auto-resolve working directory
BASE_DIR = Path(__file__).parent.resolve()
os.chdir(BASE_DIR)
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Prevent crashes under windowless pythonw or encoding errors
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
else:
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')
else:
    try: sys.stderr.reconfigure(encoding='utf-8')
    except: pass

import uuid
import threading
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipeline import pipeline
from pdf_builder import DOWNLOADS_DIR

app = FastAPI(title="Insta CLI Web Harvester")

# Mount downloads static directory
app.mount("/downloads", StaticFiles(directory=str(DOWNLOADS_DIR)), name="downloads")

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

tasks_db = {}

class ReelRequest(BaseModel):
    reel_url: str
    comment_text: str = "Send link"

class LoginRequest(BaseModel):
    username: str = None
    password: str = None
    session_id: str = None
    verification_code: str = None

@app.get("/api/auth-status")
def auth_status_api():
    from auth import auth_manager
    is_logged_in = auth_manager.load_session()
    user = auth_manager.client.username if is_logged_in else None
    
    if is_logged_in and (not user or user == "Connected"):
        import logging
        auth_manager.client.request_logger.setLevel(logging.WARNING)
        try:
            res = auth_manager.client.private_request('accounts/current_user/?edit=true')
            user = res['user']['username']
            auth_manager.client.username = user
        except Exception as e:
            import traceback
            traceback.print_exc()
            user = "Connected"
            
    if is_logged_in and user and user != "Connected":
        try:
            avatar_dir = BASE_DIR / "static" / "avatars"
            avatar_dir.mkdir(parents=True, exist_ok=True)
            u_file = avatar_dir / f"{user.lower()}.jpg"
            if not u_file.exists():
                u_info = auth_manager.client.user_info_by_username(user)
                pic_url = str(getattr(u_info, 'profile_pic_url_hd', '') or getattr(u_info, 'profile_pic_url', ''))
                if pic_url:
                    import httpx
                    resp = httpx.get(pic_url, follow_redirects=True, timeout=8.0)
                    if resp.status_code == 200 and len(resp.content) > 1000:
                        u_file.write_bytes(resp.content)
        except Exception:
            pass

    return {"authenticated": is_logged_in, "username": user}

@app.get("/api/creator-avatar/{username}")
def get_creator_avatar_api(username: str):
    from auth import auth_manager
    from fastapi.responses import RedirectResponse
    import httpx
    
    clean_name = username.strip().lstrip('@').lower()
    if not clean_name or clean_name in ["checking…", "no session", "connected", "undefined", "null"]:
        return RedirectResponse("https://ui-avatars.com/api/?name=User&background=D4622A&color=fff")

    avatar_dir = BASE_DIR / "static" / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    avatar_file = avatar_dir / f"{clean_name}.jpg"

    if avatar_file.exists() and avatar_file.stat().st_size > 1000:
        return FileResponse(avatar_file)

    try:
        if auth_manager.load_session():
            u_info = auth_manager.client.user_info_by_username(clean_name)
            pic_url = str(getattr(u_info, 'profile_pic_url_hd', '') or getattr(u_info, 'profile_pic_url', ''))
            if pic_url:
                resp = httpx.get(pic_url, follow_redirects=True, timeout=10.0)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    avatar_file.write_bytes(resp.content)
                    return FileResponse(avatar_file)
    except Exception as e:
        print(f"Instagrapi avatar fetch note for @{clean_name}: {e}")

    try:
        unavatar_url = f"https://unavatar.io/instagram/{clean_name}"
        resp = httpx.get(unavatar_url, follow_redirects=True, timeout=8.0)
        if resp.status_code == 200 and len(resp.content) > 1000:
            avatar_file.write_bytes(resp.content)
            return FileResponse(avatar_file)
    except Exception:
        pass

    return RedirectResponse(f"https://ui-avatars.com/api/?name={clean_name}&background=D4622A&color=fff&bold=true")

@app.post("/api/disconnect")
def disconnect_api():
    from auth import auth_manager
    try:
        auth_manager.disconnect()
        return {"status": "success", "message": "Disconnected successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/login")
def login_api(req: LoginRequest):
    from auth import auth_manager
    try:
        if req.session_id:
            success = auth_manager.login_with_sessionid(req.session_id)
            if success:
                try:
                    # Resolve and save username to session client context
                    u_info = auth_manager.client.user_info(auth_manager.client.user_id)
                    auth_manager.client.username = u_info.username
                    auth_manager.save_session()
                    return {"status": "success", "username": u_info.username}
                except Exception:
                    return {"status": "success", "username": "Authenticated"}
            else:
                raise HTTPException(status_code=400, detail="Invalid session ID cookie.")

        if req.verification_code:
            auth_manager.client.login(req.username, req.password, verification_code=req.verification_code)
            auth_manager.save_session()
            return {"status": "success", "username": req.username}
        
        success = auth_manager.login(req.username, req.password, interactive=False)
        if success:
            return {"status": "success", "username": req.username}
        else:
            raise HTTPException(status_code=400, detail="Invalid credentials or 2FA required.")
    except Exception as e:
        from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired
        if isinstance(e, (TwoFactorRequired, ChallengeRequired)):
            return {"status": "2fa_required", "message": "Two-Factor authentication code required."}
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = Path(__file__).parent / "templates" / "index.html"
    return html_path.read_text(encoding="utf-8")

def run_pipeline_task(task_id: str, reel_url: str, comment_text: str):
    def update_progress(msg: str, pct: int):
        tasks_db[task_id]["message"] = msg
        tasks_db[task_id]["percentage"] = pct

    try:
        res = pipeline.process_reel(reel_url, comment_text, update_progress)
        tasks_db[task_id]["status"] = "success"
        tasks_db[task_id]["result"] = res
    except Exception as e:
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["error"] = str(e)

@app.post("/api/process-reel")
def process_reel_api(req: ReelRequest):
    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {
        "status": "running",
        "message": "Starting Reel harvest pipeline...",
        "percentage": 0,
        "result": None,
        "error": None
    }

    thread = threading.Thread(target=run_pipeline_task, args=(task_id, req.reel_url, req.comment_text), daemon=True)
    thread.start()

    return {"task_id": task_id}

@app.get("/api/task-status/{task_id}")
def task_status_api(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]

@app.post("/api/login-via-browser")
def login_via_browser_api():
    from auth import auth_manager
    try:
        success = auth_manager.login_via_local_browser()
        if success:
            return {"status": "success", "username": auth_manager.client.username}
        else:
            raise HTTPException(status_code=400, detail="No active Instagram session found in local browser profiles.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/connect-browser")
def connect_browser_api():
    from auth import auth_manager
    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {
        "status": "running",
        "message": "Launching browser window...",
        "percentage": 10,
        "result": None,
        "error": None
    }
    
    def status_callback(msg, pct):
        tasks_db[task_id]["message"] = msg
        tasks_db[task_id]["percentage"] = pct
    
    def run_connect_task():
        try:
            success = auth_manager.login_via_persistent_browser(status_callback=status_callback)
            if success:
                tasks_db[task_id]["status"] = "success"
                tasks_db[task_id]["message"] = f"Connected as @{auth_manager.client.username}!"
                tasks_db[task_id]["percentage"] = 100
                tasks_db[task_id]["result"] = {"username": auth_manager.client.username}
            else:
                tasks_db[task_id]["status"] = "failed"
                tasks_db[task_id]["error"] = "Browser closed or login timed out without capturing session."
        except Exception as e:
            tasks_db[task_id]["status"] = "failed"
            tasks_db[task_id]["error"] = str(e)
            
    thread = threading.Thread(target=run_connect_task, daemon=True)
    thread.start()
    return {"task_id": task_id}

@app.get("/api/history")
def get_history_api():
    import json
    history_file = Path(__file__).parent / "history.json"
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

@app.delete("/api/history/{index}")
def delete_history_item_api(index: int):
    import json
    from pdf_builder import generate_cumulative_pdf
    history_file = Path(__file__).parent / "history.json"
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
            if 0 <= index < len(history_data):
                history_data.pop(index)
                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump(history_data, f, indent=4)
                # Regenerate PDF
                generate_cumulative_pdf("consolidated_report.pdf", history_data)
                return {"status": "success", "history": history_data}
            else:
                raise HTTPException(status_code=400, detail="Invalid index")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success", "history": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

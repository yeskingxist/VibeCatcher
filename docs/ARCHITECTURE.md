# VibeCatcher Architecture & Design

## 🏗️ System Overview

VibeCatcher is designed with a decoupled architecture separating the FastAPI REST API, Playwright persistent browser context worker, and frontend interactive dark glass UI.

```
+-------------------------------------------------------------+
|                VibeCatcher Web Dashboard                    |
|             (FastAPI + HTML5 + CSS3 + 3D Tilt)              |
+------------------------------+------------------------------+
                               | REST API / WebSocket
                               v
+-------------------------------------------------------------+
|                      FastAPI Server                         |
|             (server.py — http://127.0.0.1:8000)             |
+------------------------------+------------------------------+
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
+-----------------------+             +-----------------------+
|  Playwright Worker    |             |   PDF Builder Engine  |
|  (pipeline.py + auth) |             |   (pdf_builder.py)    |
+-----------+-----------+             +-----------+-----------+
            |                                     |
            v                                     v
  Local Chromium Session                 Consolidated PDF Report
  (browser_data/ profile)                (downloads/ report.pdf)
```

---

## 🔒 Security & Local Execution Guard

1. **Persistent Local Profiles:** All Instagram cookies and local sessions reside in `browser_data/` on the user's machine.
2. **Human-like Interaction Guard:** `bot_guard.py` enforces randomized delays, organic mouse paths, and anti-detection headers to prevent automated action blocks.
3. **Zero Third-Party Telemetry:** No user data or credentials leave the local machine.

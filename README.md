# VibeCatcher 🎯

> **Automate Reel Comments, Click DM Buttons, Extract Hidden Resource Links.**
> Turn Instagram Reels into structured, downloadable PDF intelligence reports automatically in sub-15 seconds.

[![Stars](https://img.shields.io/github/stars/yeskingxist/VibeCatcher?style=for-the-badge&logo=github&color=FF7F3E)](https://github.com/yeskingxist/VibeCatcher/stargazers)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-Automated-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

---

## 💡 What is VibeCatcher?

Creator marketing & lead generation on Instagram requires commenting `"Link"`, `"Info"`, or `"PDF"` on Reels, waiting for automated DM replies, manually clicking interactive buttons, and copy-pasting resource links into notes.

**VibeCatcher automates the entire end-to-end workflow in sub-15 seconds:**

```
+-----------------------------------------------------------------------------------+
| 1. Input Reel URL & Keyword                                                       |
|    └─► 2. Auto-Post Comment & Trigger DM Reply                                    |
|         └─► 3. Auto-Click Interactive Bot Buttons ("Send Link", "Get PDF")         |
|              └─► 4. Extract Google Drive, Notion, & PDF Resource Links            |
|                   └─► 5. Export Consolidated PDF Intelligence Report              |
+-----------------------------------------------------------------------------------+
```

---

## ⚡ Quick Start (One Command Setup)

Copy and paste this **Single Line Command** into your PowerShell terminal:

```powershell
git clone https://github.com/yeskingxist/VibeCatcher.git; cd VibeCatcher; .\run.ps1
```

### 🛠️ Standard Step-by-Step Setup:

```bash
# 1. Clone the repository
git clone https://github.com/yeskingxist/VibeCatcher.git

# 2. Enter project directory
cd VibeCatcher

# 3. Launch automated environment & dashboard
.\run.ps1
```

> **What happens automatically when `run.ps1` executes:**
> 1. Verifies Python 3.10+ installation.
> 2. Auto-installs required dependencies from `requirements.txt`.
> 3. Installs Playwright Chromium browser binaries.
> 4. Launches the VibeCatcher Dashboard on `http://127.0.0.1:8000` and opens your browser.

---

## 🔥 Key Features

- 🎯 **Automated Reel Engagement:** Automatically watches Reels and posts your custom trigger keywords.
- 🤖 **Automated DM Button Clicker:** Automatically detects and clicks interactive ManyChat / Cosmofeed bot buttons (*"Send me the link"*, *"Get Access"*, *"Download PDF"*).
- 📥 **Sub-15s Real-Time DM Capture:** Polls incoming creator DMs every 1.5 seconds for instant link extraction.
- 🔗 **Deep Resource Link Extractor:** Uncovers Google Drive files, PDFs, Notion pages, and external landing URLs.
- 📄 **Consolidated PDF Intelligence Report:** Generates clean, downloadable PDF summaries (`consolidated_report.pdf`) with extracted resource links and page highlights.
- 🧹 **Zero-Trace Auto-Clean Guard:** Automatically auto-cleans trigger comments after engagement to keep your profile feed clean.
- 🛡️ **100% Local & Session-Safe:** Runs inside your local persistent Chromium browser session (`browser_data/`). No credentials or cookies ever leave your machine.
- 🎨 **Ultra-Sharp Dark Glass UI:** Built with FastAPI, HTML5, CSS3, and 3D card tilt interactions.

---

## ⚙️ How It Works

```
+-------------------+       +-----------------------+       +-------------------------+
|  User Inputs      |  ---> | Playwright Engine     |  ---> | Automated DM Clicker    |
|  Reel URL & KW    |       | Comments on Target    |       | Clicks ManyChat Buttons |
+-------------------+       +-----------------------+       +-------------------------+
                                                                         |
                                                                         v
+-----------------------+                                   +-------------------------+
| Consolidated PDF      | <-------------------------------- | Resource Link Extractor |
| Intelligence Report   |                                   | Drive / PDFs / Notion   |
+-----------------------+                                   +-------------------------+
```

---

## 📊 Comparison

| Feature | Manual Process | Generic Bot Tools | VibeCatcher 🎯 |
| :--- | :---: | :---: | :---: |
| **Execution Speed** | 5-10 mins/reel | 2-3 mins | **10 - 15 seconds** |
| **Interactive Button Clicker** | Manual Tap | ❌ No | **✅ Automated** |
| **DM Link Extraction** | Manual Copy-Paste | ❌ No | **✅ Automatic** |
| **PDF Intelligence Export**| ❌ No | ❌ No | **✅ Automatic** |
| **Account Safety Guard** | N/A | Low | **✅ High (Human Timing)** |
| **Data Privacy** | Manual | Cloud Third-Party | **100% Local Execution** |

---

## 🛣️ Roadmap

- [x] v1.0 — Initial Release with FastAPI Web Dashboard & Automated DM Button Clicker.
- [ ] v1.1 — Batch Multi-Reel Processing Queue.
- [ ] v1.2 — Telegram & Discord Webhook Notifications.
- [ ] v1.3 — Chrome Extension Companion.

---

## 🤝 Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before submitting Pull Requests.

---

## 📜 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

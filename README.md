# VibeCatcher 🎯

> **Automate Reel Comments, Extract DM Links.**
> Turn Instagram Reels into structured, downloadable PDF intelligence reports automatically.

[![Stars](https://img.shields.io/github/stars/yeskingxist/VibeCatcher?style=for-the-badge&logo=github&color=FF7F3E)](https://github.com/yeskingxist/VibeCatcher/stargazers)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-Automated-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

---

## 💡 Why VibeCatcher?

Creator marketing & lead generation on Instagram requires commenting `"Link"`, `"Info"`, or `"PDF"` on Reels, waiting for automated DMs, opening external links, and manually organizing resources. 

**VibeCatcher automates the entire loop in seconds:**

```
1. Input Reel URL & Keyword ➜ 2. Auto-comment & trigger DM ➜ 3. Extract Drive/PDF Links ➜ 4. Export PDF Report
```

---

## ⚡ Quick Start (One Command)

### Windows (PowerShell / Command Prompt)

Run this single command in your project directory:

```powershell
powershell -ExecutionPolicy Bypass -File run.ps1
```

Or simply double-click **`run.bat`**!

> **What happens automatically:**
> 1. Verifies Python 3.10+ environment.
> 2. Auto-installs Python packages from `requirements.txt`.
> 3. Installs Playwright Chromium browser binaries.
> 4. Launches the VibeCatcher Dashboard on `http://127.0.0.1:8000` and opens your browser.

---

## 🔥 Features

- 🎯 **Automated Reel Interaction:** Opens Reels and posts your custom trigger keywords.
- 📥 **Real-Time DM Capture:** Monitors creator automated DM replies and captures incoming resource links.
- 🔗 **Resource Link Extraction:** Uncovers Google Drive files, PDFs, Notion pages, and external URLs.
- 📄 **PDF Intelligence Report:** Generates consolidated, downloadable PDF intelligence summaries with extracted resources.
- 🛡️ **Session-Safe Local Execution:** Runs locally inside persistent browser context with human-like timing guards.
- 🎨 **Modern Dark Glass UI:** Built with FastAPI, HTML5, CSS3, and 3D card tilt interactions.

---

## ⚙️ How It Works

```
+-------------------+       +--------------------+       +-----------------------+
|  User Inputs      |  ---> | Playwright Worker  |  ---> | Resource Link Extractor|
|  Reel URL & KW    |       | Auto-Comments Reel |       | Google Drive / PDFs   |
+-------------------+       +--------------------+       +-----------------------+
                                                                     |
                                                                     v
                                                         +-----------------------+
                                                         | Consolidated PDF      |
                                                         | Intelligence Report   |
                                                         +-----------------------+
```

---

## 📊 Comparison

| Feature | Manual Process | Generic Bot Tools | VibeCatcher 🎯 |
| :--- | :---: | :---: | :---: |
| **Speed** | 5-10 mins/reel | 2-3 mins | **15 seconds** |
| **DM Link Extraction** | Manual Copy-Paste | ❌ No | **✅ Automatic** |
| **PDF Intelligence Export**| ❌ No | ❌ No | **✅ Automatic** |
| **Account Safety Guard** | N/A | Low | **✅ High (Human Timing)** |
| **Data Privacy** | Manual | Cloud Third-Party | **100% Local Execution** |

---

## 🛣️ Roadmap

- [x] v1.0 — Initial Release with FastAPI Web Dashboard & Playwright DM Extractor.
- [ ] v1.1 — Batch Multi-Reel Processing Queue.
- [ ] v1.2 — Telegram & Discord Webhook Notifications.
- [ ] v1.3 — Chrome Extension Companion.

---

## 🤝 Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before submitting Pull Requests.

---

## 📜 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

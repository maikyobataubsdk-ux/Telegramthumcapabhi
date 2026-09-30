# ADVANCED TELEGRAM THUMBNAIL & CAPTION EDITOR BOT

A production-ready, feature-complete Telegram bot for changing video thumbnails and captions, supporting multiple videos, inline UI submenus, MongoDB with automatic JSON file fallback, Force Subscribe system, and an owner/admin panel.

---

## 🌟 Key Features
- **🖼 Thumbnail Editor (`/thum`):** Send a thumbnail photo and apply it to one or multiple videos sequentially with progress reporting.
- **📝 Caption Editor (`/cap`):** Send a video and supply a custom caption with text formatting support.
- **🔐 Force Subscribe System (`/setfs`, `/delfs`, `/fsstatus`):** Lock bot usage behind channel membership with verification buttons.
- **🛠 Owner/Admin Control Panel (`/admin`):**
  - Live statistics and system metric benchmarks (CPU, RAM, Disk).
  - Broadcast system with FloodWait handling and progress tracking.
  - User ban/unban management.
  - Maintenance mode toggle.
  - Data migration tool (`/migrate`) from JSON to MongoDB.
- **💾 Dual Database Engine:**
  - Attempts connection to MongoDB via `motor`.
  - Automatically falls back to thread/task safe JSON (`data/database.json`) if `MONGO_URI` is empty or connection fails.
- **🧹 Automatic Session Isolation & File Cleanup:** Session-isolated temporary directories in `temp/{user_id}/{session_id}/` with automatic deletion after job completion or cancellation.

---

## 📂 Project Structure

```
thumbnail-editor-bot/
├── main.py
├── config.py
├── database.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── test_bot.py
├── data/
│   └── database.json
├── handlers/
│   ├── start.py
│   ├── thumbnail.py
│   ├── caption.py
│   ├── force_subscribe.py
│   └── admin.py
├── services/
│   ├── video.py
│   ├── thumbnail.py
│   ├── caption.py
│   ├── broadcast.py
│   └── force_subscribe.py
├── keyboards/
│   ├── user.py
│   ├── admin.py
│   └── force_subscribe.py
├── states/
│   └── states.py
└── utils/
    ├── cleanup.py
    ├── logger.py
    ├── rate_limit.py
    └── helpers.py
```

---

## ⚡ Installation & Setup

### 1. Prerequisites
- Python 3.11+
- FFmpeg & FFprobe installed on VPS (`sudo apt install ffmpeg -y`)

### 2. Environment Setup
Clone the repository and install Python dependencies:
```bash
pip install -r requirements.txt
```

Create `.env` file based on `.env.example`:
```env
BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DATABASE_NAME=thumbnail_editor
OWNER_ID=123456789
LOG_CHANNEL_ID=-100123456789
START_IMAGE_URL=
OFFICIAL_CHANNEL=https://t.me/example
SUPPORT_LINK=https://t.me/example
MAX_CONCURRENT_JOBS=2
```

*Note: `MONGO_URI` is completely optional. If left blank or unreachable, the bot automatically initializes `data/database.json`.*

---

## 🚀 Running the Bot

### Normal Execution
```bash
python3 main.py
```

### Run Unit Tests
```bash
python3 test_bot.py
```

### VPS Deployment (Systemd Service)
Create a service file `/etc/systemd/system/thumbbot.service`:
```ini
[Unit]
Description=Telegram Thumbnail Editor Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/thumbnail-editor-bot
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable thumbbot
sudo systemctl start thumbbot
```

---

## 🛠 Commands Reference

- `/start` - Start the bot and open interactive Start menu
- `/thum` - Start thumbnail replacement session
- `/cap` - Start caption edit session
- `/cancel` - Cancel current session and cleanup temporary files
- `/help` - View usage instructions
- `/admin` - Open Admin control panel (Admins only)
- `/stats` - View statistics & server resource usage
- `/broadcast` - Broadcast message to all bot users
- `/ban <user_id>` - Ban user
- `/unban <user_id>` - Unban user
- `/setfs` - Configure force subscribe channel
- `/delfs` - Disable force subscribe
- `/fsstatus` - View force subscribe configuration
- `/maintenance` - Toggle maintenance mode
- `/migrate` - Transfer data from JSON fallback into MongoDB

# AI Discord Bot

A powerful Discord AI bot with per-user memory persistence, multiple AI providers, and a modern UI.

## ✨ Features

- 🧠 **Per-User Memory**: Each user has isolated conversation history stored in SQLite
- 🤖 **Multiple AI Providers**: Google Gemini, Groq, and OpenRouter support
- 🎨 **Modern UI**: Rich embeds with gradient colors and interactive menus
- 🖼️ **Multimodal**: Image understanding with Gemini models
- 📺 **YouTube Integration**: Automatic transcript extraction
- 🔄 **Auto-Failover**: Automatic provider switching on errors
- 🛡️ **Admin Commands**: Full moderation suite (kick, ban, timeout, etc.)

## 📁 Project Structure

```
Discord AI/
├── src/
│   ├── __init__.py
│   ├── bot.py              # Main bot class
│   ├── commands.py         # Slash commands
│   ├── providers.py        # AI provider implementations
│   ├── ui_components.py    # Modern Discord UI components
│   ├── database.py         # SQLite database manager
│   └── utils.py            # Utility functions
├── config/
│   ├── config.json         # Bot configuration
│   ├── models.json         # Available AI models
│   ├── instruction.json    # System instructions
│   └── Admin.json          # Admin directives
├── data/
│   └── user_dbs/           # Per-user SQLite databases
├── logs/
│   └── bot.log             # Application logs
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables
```

## 🚀 Setup

### 1. Install Dependencies

Run the automated installer script:

```bash
python install.py
```

Or install manually:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create/edit `.env` file:

```env
DISCORD_TOKEN="your_discord_bot_token"
GEMINI_API_KEY="your_gemini_api_key"
GROQ_API="your_groq_api_key"
OPENROUTER_API_KEY="your_openrouter_api_key"
CHANNEL_ID="your_discord_channel_id"
ADMIN_USER_ID="your_discord_user_id"
```

### 3. Run the Bot

```bash
python main.py
```

## 🎮 Commands

### AI Commands
- `/model` - Change AI model and provider
- `/stats` - View your usage statistics
- `/help` - Show help message

### Admin Commands (Require Permissions)
- `/reset` - Reset your conversation history
- `/user_reset` - Reset a specific user's memory
- `/kick` - Kick a member from the server
- `/ban` - Ban a member from the server
- `/unban` - Unban a user
- `/timeout` - Timeout a member

## 🔧 Configuration

### config/config.json
Main bot settings including token limits, reset thresholds, and provider defaults.

### config/models.json
Available AI models with metadata (ratings, speeds, capabilities).

### config/instruction.json
System instruction templates for AI behavior.

## 🐛 Bug Fixes (v2.0)

This version includes fixes for:
- ✅ Duplicate code in providers.py
- ✅ Hardcoded admin user ID (now in .env)
- ✅ Error handling variable scope issues
- ✅ Race conditions in session management
- ✅ Missing command sync on startup
- ✅ Improved retry logic with proper variable access

## 🎨 UI Improvements

- Modern color scheme with Discord Blurple theme
- Rich embeds with emojis and visual hierarchy
- Interactive model selection with dropdowns
- Styled error messages with helpful tips
- Loading indicators and status embeds

## 📝 License

Private use project.

## 👤 Author

Created for Discord server automation and AI assistance.

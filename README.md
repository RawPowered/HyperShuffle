# 🎬 HyperShuffle

> **Advanced Plex Collection Shuffling System** — intelligently picks what to watch next from your TV collections, so you never stare at a blank screen again.

HyperShuffle is a polished, terminal-based Python tool that connects to your Plex Media Server, cycles through your curated TV collections, selects the least-watched episode (prioritising content you haven't seen yet), and queues it on any Plex client — all with a single keypress. It also ships as a standalone Windows EXE so you don't need Python installed at all.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🎯 **Smart Episode Selection** | Always picks the episode with the lowest view-count in the current collection — so "unwatched" content comes first |
| 🔄 **Auto Collection Cycling** | Rotates through all your collections automatically on each shuffle, so you cycle through every genre over time |
| 🎄 **Holiday Episode Filtering** | Pushes seasonal/holiday episodes to the back of the queue by default (or promotes them, your call) |
| 📱 **Remote Control Mode** | Full in-terminal remote: skip, pause, stop, volume, subtitle control — without touching your TV |
| 🗣️ **Smart Subtitle Selection** | Scores and selects the most accurate subtitle stream for each episode automatically |
| 🔀 **3-Pass Shuffle Mode** | Extra-randomised shuffle that breaks up predictable ordering |
| 📺 **Samsung/Tizen Support** | Dedicated session-based fallback for Samsung smart TVs with limited API support |
| 🗄️ **SQLite View-Count Tracking** | Local database persists view counts across sessions and multiple Plex servers |
| 🖥️ **Standalone EXE** | One-click build script (PyInstaller) produces a portable `HyperShuffle.exe` |

---

## 🖼️ Interface Preview

```
╔══════════════════════════════════════════════════════════════╗
║                    🎬 HYPER SHUFFLE 🎬                       ║
║              Advanced Plex Collection Shuffling System       ║
║                    Super-Shuffle Default Mode                ║
╚══════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════════════════╗
║                            🎮 COMMAND CENTER 🎮                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║ System Status: 1 server(s) • 2/2 clients online                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║ 🎬 INSTANT ACTIONS                                                            ║
║   shuffle / s    🎯 Smart collection shuffle (default)                        ║
║   quick  / q     🚀 Pick collection → play instantly with subtitles           ║
║   remote / r     📱 Full remote control (skip, pause, subs, volume)           ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## 📋 Requirements

- **Python 3.7+**
- A **Plex Media Server** with TV collections configured
- A **Plex account** (username + password)

### Dependencies

| Package | Version | Purpose |
|---|---|---|
| `plexapi` | ≥ 4.15.0 | Plex server/client API |
| `psutil` | ≥ 5.9.0 | System monitoring |
| `colorama` | ≥ 0.4.6 | Colour terminal output (Windows/macOS/Linux) |

---

## 🚀 Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/HyperShuffle.git
cd HyperShuffle

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your Plex credentials
cp config.example.py config.py
# then edit config.py with your username, password, and server name
```

> ⚠️ `config.py` is listed in `.gitignore` — your credentials will never be committed.

---

## ⚙️ Configuration

Copy `config.example.py` to `config.py` and fill in your details:

```python
username = "your_plex_username_or_email"
password = "your_plex_password"
servers  = ["Your_Server_Name"]   # as shown in your Plex dashboard

audioLang      = "English"   # preferred audio language
subLang        = "English"   # preferred subtitle language
tv_library_name = "TV Shows" # exact name of your TV library in Plex
```

You can list **multiple servers**:
```python
servers = ["HomeServer", "OfficeServer"]
```

---

## 🎮 Usage

```bash
python HyperShuffle.py
```

### Command Reference

#### Primary Commands

| Command | Shortcut | Description |
|---|---|---|
| `shuffle` | `s` or _Enter_ | Smart shuffle — cycles to the next collection and plays the least-watched episode |
| `quick` | `q` | Interactive collection picker with smart subtitle auto-enable |
| `remote` | `r` | Launch remote control mode for a currently playing client |
| `collections` | `c` | List all collections with item counts |
| `config` | `settings` | Open the configuration menu |
| `status` | `st` | Show server, client, and collection status |
| `check` | `health` | Run a system health check |
| `help` | `h` or `?` | Show full command reference |
| `quit` | `exit` | Exit HyperShuffle |

#### Advanced Commands

| Command | Description |
|---|---|
| `diag` | Detailed diagnostics — connection tests, session state, API version |
| `samsung` | Samsung/Tizen TV troubleshooting guide |
| `subs on` | Enable subtitles on the current client (manual, per-session) |
| `subs off` | Disable subtitles on the current client |
| `auto subs on` | Enable automatic subtitle management globally |
| `auto subs off` | Disable automatic subtitle management globally |
| `reset` | Reset collection index back to 0 |
| `clients` | Re-scan and list available Plex clients |

---

## 🔬 How It Works

### 1. Startup & Connection
On launch HyperShuffle:
- Reads `config.py` for your Plex credentials
- Authenticates via `MyPlexAccount`
- Connects to each server listed in `servers`
- Discovers all online Plex clients (filtered to `player` devices on the same public address)
- Loads the collection index from `collection_index.txt` (persists across sessions)
- Bootstraps the local SQLite database (`myShows.db`) if needed

### 2. The Super-Shuffle Flow (`shuffle` command)

```
Step 1 │ Analyse collections → pick the "current" collection from the rotating index
Step 2 │ Select a Plex client (auto-select if only one is online)
Step 3 │ Choose a prioritisation mode (holiday filter, seasonal push, or random)
Step 4 │ Pull the collection's shows from Plex, then query the local DB for their episodes
       │   • Update view counts from all servers (skipped if DB is locked/busy)
       │   • Apply the chosen prioritisation filter
Step 5 │ Select the episode with the lowest total view count
Step 6 │ Convert the DB record → live Plex episode object via server search
Step 7 │ Connect to the client (with retry + Samsung/Tizen fallback)
Step 8 │ Play the episode (preserves shuffle mode if already active on client)
Step 9 │ Advance the collection index → save to disk for the next run
```

### 3. Episode Prioritisation Modes

| Mode | Behaviour |
|---|---|
| `1` Push holiday back _(default)_ | Keyword-scans episode titles; regular episodes play first |
| `2–8` Promote specific holiday | Halloween, Thanksgiving, Christmas, Summer, Valentine's, Easter, New Year |
| `9` True Random | Standard `random.shuffle` |
| `10` 3-Pass Shuffle | Pass 1: shuffle → Pass 2: segment reverse + reshuffle → Pass 3: random pop |

Holiday keywords are defined in `HyperShuffle.py` and can be edited directly. Current sets:

- **Halloween** — `halloween`, `horror`, `treehouse`, `spooky`, `scary`, `ghost`, `witch`, `vampire`, `monster`
- **Thanksgiving** — `thanksgiving`, `turkey`, `pilgrim`, `harvest`, `feast`, `gratitude`
- **Christmas** — `christmas`, `x-mas`, `xmas`, `holy night`, `santa`, `elf`, `reindeer`, `snowman`
- **Summer** — `summer`, `beach`, `vacation`, `hot`, `sun`, `pool`, `barbecue`, `bbq`, `picnic`
- **Valentine's** — `valentine`, `love`, `romance`, `heart`, `cupid`
- **Easter** — `easter`, `bunny`, `egg`, `spring`, `resurrection`
- **New Year** — `new year`, `new years`, `resolution`, `celebration`, `fireworks`

### 4. Smart Subtitle Selection

When subtitle automation is enabled, HyperShuffle scores each available subtitle stream and picks the best one. Scoring criteria:

| Factor | Points |
|---|---|
| Language matches preference | +100 |
| Forced subtitles (foreign-language only) | +50 |
| External subtitle file | +40 |
| SRT / ASS / SSA format | +30 |
| SDH / Closed Caption | +35 |
| Full/Complete label | +25 |
| Auto-generated (machine/Google) | −20 |

### 5. Client Connection Strategy

For **standard clients**: connect → test responsiveness via `timeline()` → retry up to 3× on timeout.

For **Samsung/Tizen clients** (detected by platform or product name):
1. Check for an active server session matching the client → wrap it as a `SessionClientWrapper`
2. If no session exists, fall back to `SamsungClientWrapper` with extended timeout
3. Both wrappers expose the same interface (`play`, `pause`, `stop`, `skipNext`, `setSubtitleStream`, etc.) with graceful fallbacks and user-friendly guidance where the API is limited

### 6. Local Database (`myShows.db`)

SQLite database with a single `episodes` table:

```sql
CREATE TABLE episodes (
    ID        INTEGER PRIMARY KEY,
    Type      TEXT,
    Show      TEXT,
    Season    TEXT,
    Episode   TEXT,
    Title     TEXT,
    Server    TEXT,
    ViewCount INTEGER,
    Length    INTEGER
);
```

View counts are kept in sync on every shuffle. The database path is resolved in order:
1. Same directory as the script / EXE
2. Parent directory (useful when running from `dist/`)
3. Current working directory
4. `%APPDATA%\HyperShuffle\myShows.db` (created automatically as a last resort)

> 💡 **First-time use:** HyperShuffle auto-creates the database schema on startup and populates it progressively as you shuffle. No pre-seeding step is required.

---

## 📦 Building a Standalone EXE (Windows)

A build script is included that uses PyInstaller to produce a single portable `HyperShuffle.exe`:

```bat
build_hypershuffle_exe.bat
```

This will:
1. Upgrade `pip` and install `pyinstaller`, `colorama`, `plexapi`
2. Clean any previous `dist/` and `build/` folders
3. Run PyInstaller in `--onefile` mode
4. Output `dist\HyperShuffle.exe`

> **Note:** Place `config.py` alongside the `.exe` before running, or set up credentials at runtime.
> If an `icon.ico` file exists in the same directory, it will be embedded automatically.

Alternatively, use the `.spec` file directly:
```bash
pyinstaller HyperShuffle.spec
```

---

## 🛠️ Configuration Menu

At runtime, type `config` to open the full configuration menu. All settings are held in memory for the session.

| Setting | Default | Description |
|---|---|---|
| Auto-cycle collections | ✅ On | Advance to the next collection after each shuffle |
| Holiday episode filtering | ✅ On | Push seasonal episodes to the back |
| View count priority | ✅ On | Prefer least-watched episodes |
| Balanced TV lineup | ❌ Off | Limit consecutive same-show episodes |
| Animation domination | ❌ Off | Special mode for animation-heavy collections |
| Auto client selection | ✅ On | Skip client picker if only one client is online |
| Show detailed info | ✅ On | Display episode info box before playback |
| Confirm before playing | ❌ Off | Prompt y/n before sending to client |
| Update view counts | ✅ On | Sync view counts from Plex before selection |
| Skip updates when busy | ❌ Off | Skip DB update if a lock is detected |
| Preserve shuffle mode | ✅ On | Add to existing shuffle queue if client is in shuffle mode |
| Auto-manage subtitles | ❌ Off | Enable/download/select subtitles automatically |
| Auto-download subtitles | ❌ Off | Download missing subtitle files |
| Auto-enable subtitles | ❌ Off | Enable the chosen subtitle stream on playback |
| Smart subtitle selection | ✅ On | Use scoring system to pick the best stream |
| Max consecutive same show | `2` | Max episodes from the same show in a row |
| Collection cycle delay (s) | `5` | Wait time between collection switches |
| Database retry attempts | `3` | Retries for SQLite lock errors |
| Client retry attempts | `3` | Retries for client connection errors |
| Client timeout (s) | `30` | Timeout for client operations |

---

## 🧩 File Structure

```
HyperShuffle/
├── HyperShuffle.py             # Main application (3 200+ lines)
├── config.example.py           # ← Copy this to config.py and fill in credentials
├── config.py                   # Your credentials (gitignored — never committed!)
├── requirements.txt            # Python dependencies
├── HyperShuffle.spec           # PyInstaller build spec (for manual EXE builds)
├── build_hypershuffle_exe.bat  # One-click Windows EXE builder
├── run_hypershuffle.bat        # Launcher: auto-creates venv, installs deps, runs app
├── myShows.db                  # SQLite database (gitignored — created at runtime)
├── collection_index.txt        # Persists current collection position (gitignored)
└── .gitignore
```

---

## 🔧 Troubleshooting

### "No collections found"
- Open Plex and ensure your TV library has **Collections** created
- Check that `config.py` points to the correct server name (must match the name in your Plex dashboard)
- Run `diag` from the HyperShuffle prompt for a detailed server/collection inventory
- Run `check` for a quick health overview

### "No available clients"
- Make sure at least one Plex client (app on TV, phone, desktop) is **open and active**
- Client and server must be on the same public IP address (local network)
- Try `clients` command to force a re-scan

### "Database is locked"
- Enable **Skip updates when busy** in the `config` menu
- Increase **Database retry attempts** in the `config` menu
- Close any other processes that might have `myShows.db` open

### "Read timed out" / client unresponsive
- Increase **Client timeout** and **Client retry attempts** in `config`
- For Samsung TVs: run `samsung` command for a step-by-step guide
- Run `diag` to see exactly which API calls are failing

### Samsung/Tizen TV issues
Run the built-in guide:
```
HyperShuffle> samsung
```
Key points:
- Restart the Plex app on the TV before connecting
- HyperShuffle falls back to session-based control automatically
- Use the TV remote for volume and subtitle toggling — these are not remotely controllable on most Samsung models

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dependencies: `pip install -r requirements.txt`
4. Make your changes and test across different collection sizes and client types
5. Submit a pull request

---

## 📄 License

This project is open source and available under the **MIT License**.

---

## 🙏 Acknowledgements

Inspired by the [plex-trueshuffle](https://github.com/pastram-i/plex-trueshuffle) project. HyperShuffle is a ground-up rewrite with a full interactive interface, smart subtitle management, Samsung TV support, remote control mode, and a significantly expanded configuration system.

---

*Enjoy never having to decide what to watch again.* 🎉
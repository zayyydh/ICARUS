"""
ICARUS Constants
=================
Every fixed value, keyword, and magic string lives here.
No string literals scattered across the codebase.

Rule: if a value appears in more than one file, it belongs here.

Usage:
    from app.config.constants import INTENT, LANGUAGE, PERSONALITY
"""

from enum import Enum


# ══════════════════════════════════════════════════════════════════
# ICARUS IDENTITY
# ══════════════════════════════════════════════════════════════════

ICARUS_NAME        = "ICARUS"
ICARUS_FULL_NAME   = "Intelligent Conversational Agent with Reasoning, Understanding & Synthesis"
ICARUS_AUTHOR      = "Zayd"
ICARUS_GITHUB      = "https://github.com/zayyydh/ICARUS"

ICARUS_BANNER = f"""
╔══════════════════════════════════════════════════════╗
║                                                      ║
║    ██╗ ██████╗ █████╗ ██████╗ ██╗   ██╗███████╗     ║
║    ██║██╔════╝██╔══██╗██╔══██╗██║   ██║██╔════╝     ║
║    ██║██║     ███████║██████╔╝██║   ██║███████╗     ║
║    ██║██║     ██╔══██║██╔══██╗██║   ██║╚════██║     ║
║    ██║╚██████╗██║  ██║██║  ██║╚██████╔╝███████║     ║
║    ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝     ║
║                                                      ║
║         AI Operating System  •  v0.1.0               ║
║         github.com/zayyydh/ICARUS                    ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
"""

# Startup lines — one is picked randomly on boot
BOOT_LINES = [
    "Icarus online. Sab systems ready hain.",
    "All systems operational. How can I assist?",
    "ICARUS initialized. Ready when you are.",
    "Haan bhai, main ready hoon. Bol kya karna hai.",
    "Systems check complete. Standing by.",
]


# ══════════════════════════════════════════════════════════════════
# INTENT TYPES
# ══════════════════════════════════════════════════════════════════

class INTENT(str, Enum):
    """
    Every possible thing a user might want to do.
    The Intent Router maps user input to one of these.
    The Orchestrator then decides what to do with it.
    """

    # ── Knowledge and research ─────────────────────────────────
    QUESTION          = "question"           # General Q&A
    RESEARCH          = "research"           # Deep web search + synthesis
    SUMMARIZE         = "summarize"          # Summarise a document or URL
    EXPLAIN           = "explain"            # Explain a concept

    # ── Productivity ───────────────────────────────────────────
    WRITE             = "write"              # Draft emails, docs, content
    TRANSLATE         = "translate"          # Language translation
    CALCULATE         = "calculate"          # Math and data
    REMIND            = "remind"             # Set a reminder

    # ── Code ───────────────────────────────────────────────────
    CODE_WRITE        = "code_write"         # Write new code
    CODE_EXPLAIN      = "code_explain"       # Explain existing code
    CODE_DEBUG        = "code_debug"         # Debug an error
    CODE_RUN          = "code_run"           # Execute a script

    # ── GitHub ─────────────────────────────────────────────────
    GITHUB_PUSH       = "github_push"        # Push code to GitHub
    GITHUB_CREATE     = "github_create"      # Create a new repo
    GITHUB_LIST       = "github_list"        # List user repos
    GITHUB_STATUS     = "github_status"      # Check repo status

    # ── Music ──────────────────────────────────────────────────
    MUSIC_PLAY        = "music_play"         # Play a song
    MUSIC_PAUSE       = "music_pause"        # Pause current song
    MUSIC_STOP        = "music_stop"         # Stop music
    MUSIC_NEXT        = "music_next"         # Next track

    # ── Browser and web ────────────────────────────────────────
    BROWSER_OPEN      = "browser_open"       # Open a URL
    BROWSER_SEARCH    = "browser_search"     # Search the web
    BROWSER_SCRAPE    = "browser_scrape"     # Extract info from a page
    WEB_SEARCH        = "web_search"         # DuckDuckGo search

    # ── System ─────────────────────────────────────────────────
    SYSTEM_OPEN       = "system_open"        # Open an app
    SYSTEM_CLOSE      = "system_close"       # Close an app
    SYSTEM_VOLUME     = "system_volume"      # Adjust volume
    SYSTEM_INFO       = "system_info"        # System status

    # ── Memory ─────────────────────────────────────────────────
    MEMORY_SAVE       = "memory_save"        # "Remember that..."
    MEMORY_RECALL     = "memory_recall"      # "What did I tell you about..."
    MEMORY_FORGET     = "memory_forget"      # "Forget that..."

    # ── RAG ────────────────────────────────────────────────────
    RAG_QUERY         = "rag_query"          # Query personal knowledge base
    RAG_INGEST        = "rag_ingest"         # Add a new document

    # ── Personality and system ─────────────────────────────────
    PERSONALITY_SWITCH = "personality_switch" # "Switch to developer mode"
    ICARUS_STATUS      = "icarus_status"      # "How are you?"
    ICARUS_HELP        = "icarus_help"        # "What can you do?"

    # ── Fallback ───────────────────────────────────────────────
    UNKNOWN           = "unknown"            # Could not determine intent
    CONVERSATION      = "conversation"       # Casual chat — goes to LLM


# ══════════════════════════════════════════════════════════════════
# INTENT TRIGGER KEYWORDS
# ══════════════════════════════════════════════════════════════════
# These are checked BEFORE the LLM — fast, deterministic routing.
# Each intent maps to English + Hindi + Hinglish trigger phrases.

INTENT_TRIGGERS: dict[INTENT, list[str]] = {

    INTENT.MUSIC_PLAY: [
        "play", "gana", "gaana", "song", "music", "baja",
        "laga", "suno", "bajao", "chalao", "track",
    ],
    INTENT.MUSIC_PAUSE: [
        "pause", "ruk", "ruko", "rok", "hold",
    ],
    INTENT.MUSIC_STOP: [
        "stop music", "band kar", "music band", "stop song",
        "music rok", "gaana band",
    ],
    INTENT.MUSIC_NEXT: [
        "next", "agla", "skip", "next song", "agla gana",
    ],

    INTENT.GITHUB_PUSH: [
        "push", "push to github", "github pe daal",
        "upload code", "commit", "deploy code",
    ],
    INTENT.GITHUB_CREATE: [
        "create repo", "new repo", "naya repo",
        "repo banao", "create repository",
    ],
    INTENT.GITHUB_LIST: [
        "list repos", "show repos", "meri repos",
        "my repositories", "github repos dikha",
    ],

    INTENT.BROWSER_OPEN: [
        "open", "khol", "launch", "start", "go to",
        "website khol", "open website",
    ],
    INTENT.WEB_SEARCH: [
        "search", "dhundh", "find", "look up", "google",
        "search kar", "batao", "kya hai",
    ],

    INTENT.CODE_RUN: [
        "run", "execute", "run this",
        "run code", "script run"
        "run code", "script chala",
        "chala", "chalao", "run this",
    ],
    INTENT.CODE_DEBUG: [
        "debug", "error fix", "why is this not working",
        "kya galat hai", "error kyu aa raha",
    ],

    INTENT.MEMORY_SAVE: [
        "remember", "yaad rakh", "note kar", "save this",
        "don't forget", "bhoolna mat",
    ],
    INTENT.MEMORY_RECALL: [
        "what did i tell you", "recall", "yaad hai",
        "remember when", "you know that",
    ],

    INTENT.PERSONALITY_SWITCH: [
        "switch to", "developer mode", "bro mode",
        "night owl", "mentor mode", "coach mode",
        "minimalist", "mode switch kar",
    ],

    INTENT.SYSTEM_OPEN: [
        "khol", "open app", "launch app", "start app",
        "chrome khol", "spotify khol", "vs code khol",
    ],

    INTENT.ICARUS_STATUS: [
        "how are you", "kaise ho", "sab theek",
        "status", "you okay", "tum theek ho",
    ],
    INTENT.ICARUS_HELP: [
        "what can you do", "help", "capabilities",
        "kya kar sakte ho", "commands", "features",
    ],
}


# ══════════════════════════════════════════════════════════════════
# LANGUAGE CODES
# ══════════════════════════════════════════════════════════════════

class LANGUAGE(str, Enum):
    ENGLISH  = "en"
    HINDI    = "hi"
    MARATHI  = "mr"
    URDU     = "ur"
    HINGLISH = "hinglish"


# Languages that require the Devanagari-aware Whisper prompt
DEVANAGARI_LANGUAGES = {LANGUAGE.HINDI, LANGUAGE.MARATHI, LANGUAGE.URDU}

# Mapping from langdetect output → our LANGUAGE enum
# langdetect sometimes returns unexpected codes for Indian languages
LANGDETECT_MAP: dict[str, LANGUAGE] = {
    "hi": LANGUAGE.HINDI,
    "mr": LANGUAGE.MARATHI,
    "ur": LANGUAGE.URDU,
    "en": LANGUAGE.ENGLISH,
    # langdetect misclassifies Hinglish as these sometimes
    "tl": LANGUAGE.HINGLISH,
    "so": LANGUAGE.HINGLISH,
    "cy": LANGUAGE.HINGLISH,
    "af": LANGUAGE.HINGLISH,
}


# ══════════════════════════════════════════════════════════════════
# PERSONALITY PROFILES
# ══════════════════════════════════════════════════════════════════

class PERSONALITY(str, Enum):
    BRO         = "bro"
    DEVELOPER   = "developer"
    MENTOR      = "mentor"
    COACH       = "coach"
    NIGHT_OWL   = "night_owl"
    MINIMALIST  = "minimalist"


# Context triggers — auto-switch personality based on these signals
PERSONALITY_CONTEXT_TRIGGERS: dict[PERSONALITY, dict] = {
    PERSONALITY.DEVELOPER: {
        "apps":  ["code", "vscode", "pycharm", "cursor", "terminal", "vim"],
        "hours": [],   # Any time
    },
    PERSONALITY.NIGHT_OWL: {
        "apps":  [],
        "hours": [22, 23, 0, 1, 2, 3],   # 10 PM → 3 AM
    },
    PERSONALITY.COACH: {
        "apps":  ["leetcode", "notion", "obsidian", "anki"],
        "hours": [],
    },
    PERSONALITY.BRO: {
        "apps":  ["discord", "spotify", "youtube", "steam"],
        "hours": [],
    },
}


# ══════════════════════════════════════════════════════════════════
# VOICE
# ══════════════════════════════════════════════════════════════════

# Short acknowledgement sounds — played immediately while ICARUS thinks
# Makes conversations feel natural — no dead silence while LLM is running
THINKING_SOUNDS: dict[LANGUAGE, list[str]] = {
    LANGUAGE.HINGLISH: ["Haan...", "Theek hai...", "Dekh raha hoon..."],
    LANGUAGE.HINDI:    ["Haan...", "Ek second...", "Dekhta hoon..."],
    LANGUAGE.MARATHI:  ["Haan...", "Ek minute...", "Baghto..."],
    LANGUAGE.URDU:     ["Haan...", "Ek pal...", "Dekh raha hoon..."],
    LANGUAGE.ENGLISH:  ["On it...", "Let me check...", "One moment..."],
}

# Sample rate Whisper expects
WHISPER_SAMPLE_RATE = 16_000

# Audio chunk size for PyAudio
AUDIO_CHUNK_SIZE = 1_024


# ══════════════════════════════════════════════════════════════════
# API
# ══════════════════════════════════════════════════════════════════

API_V1_PREFIX     = "/api/v1"
API_TITLE         = "Project ICARUS"
API_DESCRIPTION   = "AI Operating System — not just a chatbot."

# CORS origins allowed in development
DEV_CORS_ORIGINS = [
    "http://localhost:3000",   # React dev server
    "http://localhost:8080",
    "http://127.0.0.1:3000",
]


# ══════════════════════════════════════════════════════════════════
# TOOL NAMES
# ══════════════════════════════════════════════════════════════════

class TOOL(str, Enum):
    """
    Canonical tool names — must match the tool's name property.
    The registry uses these to look up and call tools.
    """
    GITHUB     = "github"
    MUSIC      = "music"
    BROWSER    = "browser"
    CODE       = "code"
    WEATHER    = "weather"
    FILESYSTEM = "filesystem"
    WEB_SEARCH = "web_search"


# Intents that go directly to a tool — no LLM needed
DIRECT_TOOL_INTENTS: dict[INTENT, TOOL] = {
    INTENT.MUSIC_PLAY:    TOOL.MUSIC,
    INTENT.MUSIC_PAUSE:   TOOL.MUSIC,
    INTENT.MUSIC_STOP:    TOOL.MUSIC,
    INTENT.MUSIC_NEXT:    TOOL.MUSIC,
    INTENT.GITHUB_PUSH:   TOOL.GITHUB,
    INTENT.GITHUB_CREATE: TOOL.GITHUB,
    INTENT.GITHUB_LIST:   TOOL.GITHUB,
    INTENT.BROWSER_OPEN:  TOOL.BROWSER,
    INTENT.CODE_RUN:      TOOL.CODE,
    INTENT.WEB_SEARCH:    TOOL.WEB_SEARCH,
}

# Intents that need LLM reasoning before or after tool use
LLM_ASSISTED_INTENTS = {
    INTENT.QUESTION,
    INTENT.RESEARCH,
    INTENT.SUMMARIZE,
    INTENT.EXPLAIN,
    INTENT.WRITE,
    INTENT.CODE_WRITE,
    INTENT.CODE_EXPLAIN,
    INTENT.CODE_DEBUG,
    INTENT.CONVERSATION,
    INTENT.UNKNOWN,
}
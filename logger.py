"""
logger.py
─────────────────────────────────────────────────────────────
Centralised logging setup for the Ask Our Docs RAG bot.

Console output is colour-coded and styled:
  ✅  GREEN   → INFO    (normal flow, success)
  ⚠️  YELLOW  → WARNING (unexpected but recoverable)
  ❌  RED     → ERROR   (something failed)
  🔍  CYAN    → DEBUG   (internals, scores, previews)

File output (logs/rag_bot.log) has no colour codes — plain text
so it stays readable in any editor.
─────────────────────────────────────────────────────────────
"""

import logging
import os


LOG_DIR  = "logs"
LOG_FILE = os.path.join(LOG_DIR, "rag_bot.log")


# ──────────────────────────────────────────────────────────────
# ANSI COLOUR CODES
# ──────────────────────────────────────────────────────────────
class Colours:
    RESET      = "\033[0m"
    BOLD       = "\033[1m"

    # Text colours
    GREEN      = "\033[92m"
    YELLOW     = "\033[93m"
    RED        = "\033[91m"
    CYAN       = "\033[96m"
    WHITE      = "\033[97m"
    DIM        = "\033[2m"

    # Background accents (used on level badge)
    BG_GREEN   = "\033[42m"
    BG_YELLOW  = "\033[43m"
    BG_RED     = "\033[41m"
    BG_CYAN    = "\033[46m"


# ──────────────────────────────────────────────────────────────
# LEVEL → STYLE MAP
# ──────────────────────────────────────────────────────────────
LEVEL_STYLES = {
    "DEBUG":    (Colours.CYAN,   "🔍", "DEBUG  "),
    "INFO":     (Colours.GREEN,  "✅", "INFO   "),
    "WARNING":  (Colours.YELLOW, "⚠️ ", "WARNING"),
    "ERROR":    (Colours.RED,    "❌", "ERROR  "),
    "CRITICAL": (Colours.RED,    "🔥", "CRITICAL"),
}


# ──────────────────────────────────────────────────────────────
# CUSTOM COLOUR FORMATTER (console only)
# ──────────────────────────────────────────────────────────────
class ColourFormatter(logging.Formatter):
    """
    Formats log records with colour, emoji badge, and aligned columns.

    Output format:
      HH:MM:SS  ✅ INFO    │ message here
      HH:MM:SS  ⚠️  WARNING │ something odd happened
      HH:MM:SS  ❌ ERROR   │ something broke
    """

    def format(self, record: logging.LogRecord) -> str:
        colour, emoji, label = LEVEL_STYLES.get(
            record.levelname, (Colours.WHITE, "•", record.levelname)
        )

        # Timestamp — dimmed so it doesn't compete with the message
        timestamp = (
            f"{Colours.DIM}"
            f"{self.formatTime(record, '%H:%M:%S')}"
            f"{Colours.RESET}"
        )

        # Coloured badge:  ✅ INFO
        badge = (
            f"{Colours.BOLD}{colour}"
            f"{emoji} {label}"
            f"{Colours.RESET}"
        )

        # Separator
        sep = f"{Colours.DIM}│{Colours.RESET}"

        # Message — coloured to match level
        message = f"{colour}{record.getMessage()}{Colours.RESET}"

        return f"{timestamp}  {badge} {sep} {message}"


# ──────────────────────────────────────────────────────────────
# PLAIN FORMATTER (log file — no ANSI codes)
# ──────────────────────────────────────────────────────────────
class PlainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return (
            f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} "
            f"| {record.levelname:<8} "
            f"| {record.name} "
            f"| {record.getMessage()}"
        )


# ──────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────
def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger with:
      - Coloured console output  (INFO+)
      - Plain file output        (DEBUG+) → logs/rag_bot.log

    Usage:
        from logger import get_logger
        log = get_logger(__name__)

        log.info("Document loaded")          # green
        log.warning("No chunks found")       # yellow
        log.error("API key missing")         # red
        log.debug("Score: 0.8742")           # cyan (file only)
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # ── File handler (plain, DEBUG+) ────────────────────────
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(PlainFormatter())

    # ── Console handler (coloured, INFO+) ───────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColourFormatter())

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def log_separator(logger: logging.Logger, label: str = ""):
    """
    Prints a styled section divider to both console and log file.

    Console:  ── STAGE 1: LOAD DOCUMENTS ──────────────────
    File:     -------------------------------------------------------- STAGE 1
    """
    # Console — cyan dimmed rule with bold label
    width = 55
    if label:
        padding = max(0, width - len(label) - 4)
        rule    = f"{'─' * 2} {label} {'─' * padding}"
    else:
        rule    = "─" * width

    console_line = (
        f"\n{Colours.CYAN}{Colours.BOLD}{rule}{Colours.RESET}"
    )
    print(console_line)

    # File — plain separator
    logger.debug(f"{'─' * 60} {label}")
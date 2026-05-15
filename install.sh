#!/usr/bin/env bash
# Sentinela installer for macOS / Linux.
#
# What this script does (in order):
#   1. Verifies Python 3.10+ is available (installs via brew on macOS if missing)
#   2. Verifies ffmpeg is available (installs via brew on macOS if missing)
#   3. Creates an isolated venv at ~/.claude/skills/sentinela/.venv
#   4. Installs faster-whisper into the venv
#   5. Pre-downloads the 'medium' Whisper model
#   6. Copies the skill (SKILL.md + scripts/) into ~/.claude/skills/sentinela/
#
# Re-running this script is safe: it skips steps already completed.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="${HOME}/.claude/skills/sentinela"
VENV_PATH="${SKILL_ROOT}/.venv"
VENV_PYTHON="${VENV_PATH}/bin/python"

cyan()  { printf "\n\033[1;36m==> %s\033[0m\n" "$1"; }
green() { printf "    \033[0;32m[OK]\033[0m %s\n" "$1"; }
yellow(){ printf "    \033[0;33m[!]\033[0m  %s\n" "$1"; }

OS="$(uname -s)"
case "$OS" in
    Darwin) PLATFORM="macos" ;;
    Linux)  PLATFORM="linux" ;;
    *) echo "Unsupported OS: $OS"; exit 1 ;;
esac

# ---------------------------------------------------------------------------
cyan "1/6 Checking Python 3.10+"
PYTHON_BIN=""
for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        version="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
        major="${version%%.*}"
        minor="${version##*.}"
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON_BIN="$candidate"
            green "Found Python $version ($candidate)"
            break
        fi
    fi
done
if [ -z "$PYTHON_BIN" ]; then
    if [ "$PLATFORM" = "macos" ]; then
        yellow "Python 3.10+ not found. Installing via Homebrew..."
        if ! command -v brew >/dev/null 2>&1; then
            echo "Homebrew is required. Install from https://brew.sh first, then re-run."
            exit 1
        fi
        brew install python@3.12
        green "Python installed — please open a NEW terminal and re-run install.sh"
        exit 0
    else
        echo "Please install Python 3.10+ using your distro's package manager, then re-run."
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
cyan "2/6 Checking ffmpeg"
if ! command -v ffmpeg >/dev/null 2>&1; then
    if [ "$PLATFORM" = "macos" ]; then
        yellow "ffmpeg not found. Installing via Homebrew..."
        brew install ffmpeg
        green "ffmpeg installed"
    else
        echo "Please install ffmpeg via your package manager (e.g. 'sudo apt install ffmpeg'), then re-run."
        exit 1
    fi
else
    green "ffmpeg available"
fi

# ---------------------------------------------------------------------------
cyan "3/6 Creating isolated venv at $VENV_PATH"
mkdir -p "$SKILL_ROOT"
if [ ! -x "$VENV_PYTHON" ]; then
    "$PYTHON_BIN" -m venv "$VENV_PATH"
    green "venv created"
else
    green "venv already exists"
fi

# ---------------------------------------------------------------------------
cyan "4/6 Installing faster-whisper into venv (may take a few minutes)"
"$VENV_PYTHON" -m pip install --upgrade pip --quiet
"$VENV_PYTHON" -m pip install --quiet "faster-whisper>=1.0.0"
green "faster-whisper installed"

# ---------------------------------------------------------------------------
cyan "5/6 Pre-downloading 'medium' Whisper model (~1.5GB, one time only)"
"$VENV_PYTHON" - <<'PYEOF'
from faster_whisper import WhisperModel
print("Downloading medium model — this may take a few minutes...")
m = WhisperModel("medium", device="cpu", compute_type="int8")
print("Model ready.")
PYEOF
green "model ready"

# ---------------------------------------------------------------------------
cyan "6/6 Installing skill files into $SKILL_ROOT"
cp -f "$REPO_ROOT/skills/sentinela/SKILL.md" "$SKILL_ROOT/SKILL.md"
mkdir -p "$SKILL_ROOT/scripts"
cp -f "$REPO_ROOT"/scripts/*.py "$SKILL_ROOT/scripts/"
green "SKILL.md and scripts/ copied"

# ---------------------------------------------------------------------------
echo ""
printf "\033[0;32mSentinela installed successfully!\033[0m\n"
printf "\033[0;32mOpen Claude Code in any terminal and type:  /sentinela\033[0m\n"
echo ""

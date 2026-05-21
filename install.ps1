# Sentinela installer — plug-and-play setup for Windows.
#
# What this script does (in order):
#   1. Verifies Python 3.10+ is available (installs via winget if missing)
#   2. Verifies ffmpeg is available (installs via winget if missing)
#   3. Creates an isolated venv at ~/.claude/skills/sentinela/.venv
#   4. Installs faster-whisper + gdown into the venv
#   5. Detects NVIDIA GPU and (optionally) installs CUDA libraries
#      → membros sem GPU NVIDIA usam CPU automaticamente (10-20min/VSL)
#      → membros com NVIDIA ganham aceleração 5-15x (2-3min/VSL)
#   6. Pre-downloads the 'medium' Whisper model so the first /sentinela run is fast
#   7. Copies the skill (SKILL.md + scripts/) into ~/.claude/skills/sentinela/
#
# Re-running this script is safe: it skips steps already completed.

$ErrorActionPreference = "Stop"

$RepoRoot   = $PSScriptRoot
$SkillRoot  = Join-Path $HOME ".claude\skills\sentinela"
$VenvPath   = Join-Path $SkillRoot ".venv"
$VenvPython = Join-Path $VenvPath  "Scripts\python.exe"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    [!]  $msg" -ForegroundColor Yellow }
function Write-Info($msg) { Write-Host "    $msg" -ForegroundColor Gray }

# ---------------------------------------------------------------------------
Write-Step "1/7 Checking Python 3.10+"
$pythonExe = $null
foreach ($candidate in @("python", "py")) {
    try {
        $version = & $candidate -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $parts = $version.Trim().Split(".")
            if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 10) {
                $pythonExe = $candidate
                Write-OK "Found Python $version ($candidate)"
                break
            }
        }
    } catch {}
}
if (-not $pythonExe) {
    Write-Warn "Python 3.10+ not found. Installing via winget..."
    winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    Write-OK "Python installed — please OPEN A NEW TERMINAL and re-run install.ps1."
    exit 0
}

# ---------------------------------------------------------------------------
Write-Step "2/7 Checking ffmpeg"
try { $null = & ffmpeg -version 2>$null } catch {}
if ($LASTEXITCODE -ne 0) {
    Write-Warn "ffmpeg not found. Installing via winget..."
    winget install --id Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
    Write-OK "ffmpeg installed — please OPEN A NEW TERMINAL and re-run install.ps1."
    exit 0
} else {
    Write-OK "ffmpeg available"
}

# ---------------------------------------------------------------------------
Write-Step "3/7 Creating isolated venv at $VenvPath"
if (-not (Test-Path $SkillRoot)) {
    New-Item -ItemType Directory -Force -Path $SkillRoot | Out-Null
}
if (-not (Test-Path $VenvPython)) {
    & $pythonExe -m venv $VenvPath
    Write-OK "venv created"
} else {
    Write-OK "venv already exists"
}

# ---------------------------------------------------------------------------
Write-Step "4/7 Installing faster-whisper + gdown into venv (may take a few minutes)"
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install --quiet "faster-whisper>=1.0.0" gdown
Write-OK "faster-whisper + gdown installed"

# ---------------------------------------------------------------------------
Write-Step "5/7 Checking for NVIDIA GPU (optional GPU acceleration)"
$hasNvidia = $false
try {
    $null = & nvidia-smi 2>$null
    if ($LASTEXITCODE -eq 0) { $hasNvidia = $true }
} catch {}

if ($hasNvidia) {
    Write-OK "NVIDIA GPU detected"

    # Check disk space before pulling ~1.3GB of CUDA libs
    $freeGB = [math]::Round((Get-PSDrive C).Free / 1GB, 1)
    Write-Info "Free disk space on C:: $freeGB GB"

    if ($freeGB -lt 4) {
        Write-Warn "Less than 4GB free on C: — skipping GPU libs install (transcrição vai usar CPU)."
        Write-Warn "Libere espaço e rode novamente pra ativar GPU."
    } else {
        Write-Info "Installing CUDA libraries (~1.3GB) — speeds up transcription 5-15x..."
        & $VenvPython -m pip install --quiet nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cuda-nvrtc-cu12
        if ($LASTEXITCODE -eq 0) {
            Write-OK "CUDA libraries installed — transcription will use GPU"
        } else {
            Write-Warn "Falha ao instalar libs CUDA — transcrição vai usar CPU. Skill segue funcional."
        }
    }
} else {
    Write-Info "Sem GPU NVIDIA detectada — usando CPU (10-20min/VSL). Skill funciona normalmente."
}

# ---------------------------------------------------------------------------
Write-Step "6/7 Pre-downloading 'medium' Whisper model (~1.5GB, one time only)"
$preload = @"
from faster_whisper import WhisperModel
print('Downloading medium model - this may take a few minutes...')
m = WhisperModel('medium', device='cpu', compute_type='int8')
print('Model ready.')
"@
& $VenvPython -c $preload
Write-OK "model ready"

# ---------------------------------------------------------------------------
Write-Step "7/7 Installing skill files into $SkillRoot"
$srcSkill   = Join-Path $RepoRoot "skills\sentinela\SKILL.md"
$srcScripts = Join-Path $RepoRoot "scripts"
$dstSkill   = Join-Path $SkillRoot "SKILL.md"
$dstScripts = Join-Path $SkillRoot "scripts"

Copy-Item -Force $srcSkill $dstSkill
if (-not (Test-Path $dstScripts)) {
    New-Item -ItemType Directory -Force -Path $dstScripts | Out-Null
}
Copy-Item -Force -Recurse (Join-Path $srcScripts "*.py") $dstScripts
Write-OK "SKILL.md and scripts/ copied"

# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Sentinela installed successfully!" -ForegroundColor Green
Write-Host "Open Claude Code in any terminal and type:  /sentinela" -ForegroundColor Green
Write-Host ""

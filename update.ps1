# Sentinela updater — copies only the skill files (no dependency reinstall).
# Use this after `git pull` when the maintainer publishes skill improvements.
# If you have NEVER installed Sentinela before, run install.ps1 instead.

$ErrorActionPreference = "Stop"

$RepoRoot  = $PSScriptRoot
$SkillRoot = Join-Path $HOME ".claude\skills\sentinela"

if (-not (Test-Path $SkillRoot)) {
    Write-Host "Sentinela is not installed yet. Run .\install.ps1 first." -ForegroundColor Yellow
    exit 1
}

$dstScripts = Join-Path $SkillRoot "scripts"
if (-not (Test-Path $dstScripts)) {
    New-Item -ItemType Directory -Force -Path $dstScripts | Out-Null
}

Copy-Item -Force (Join-Path $RepoRoot "skills\sentinela\SKILL.md") (Join-Path $SkillRoot "SKILL.md")
Copy-Item -Force (Join-Path $RepoRoot "scripts\*.py") $dstScripts

Write-Host "Sentinela skill updated." -ForegroundColor Green

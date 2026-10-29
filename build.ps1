<#
  Regenerate the bilingual text packs (run after editing tools\dualsub.config.json)

  Requirements: Python 3.9+, and Yabber (https://github.com/JKAnderson/Yabber/releases)
  unpacked somewhere on this machine.

  Usage:
    powershell -ExecutionPolicy Bypass -File build.ps1
    powershell -ExecutionPolicy Bypass -File build.ps1 -YabberDir "D:\Tools\Yabber 1.3.1"
    powershell -ExecutionPolicy Bypass -File build.ps1 -GameDir "X:\...\DARK SOULS III\Game" -YabberDir "..."

  Yabber is looked up in this order: -YabberDir, "yabber_dir" in the config,
  the YABBER_DIR environment variable, PATH, then a few common folders.
#>
param(
    [string]$GameDir = '',
    [string]$YabberDir = '',
    [switch]$KeepWork
)
$ErrorActionPreference = 'Stop'
$ModRoot = $PSScriptRoot

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) {
    throw 'Python not found on PATH. Install Python 3 (https://www.python.org/downloads/) and tick "Add python.exe to PATH".'
}

$pArgs = @((Join-Path $ModRoot 'tools\dualsub.py'),
           '--config', (Join-Path $ModRoot 'tools\dualsub.config.json'),
           '--out', $ModRoot)
if ($GameDir) { $pArgs += @('--game', $GameDir) }
if ($YabberDir) { $pArgs += @('--yabber', $YabberDir) }
if ($KeepWork) { $pArgs += '--keep-work' }

$source = Join-Path $ModRoot 'source'
if (Test-Path -LiteralPath $source) {
    $pArgs += @('--source', $source)
} else {
    Write-Host 'source\ not found - reading the text packs straight from the game folder.'
    Write-Host 'Make sure those packs are vanilla (run restore.ps1 first if this mod is installed).'
}

& $py.Source @pArgs
if ($LASTEXITCODE -ne 0) { throw "Build failed (exit $LASTEXITCODE)" }

Write-Host ''
Write-Host 'Build complete. Run install.ps1 to install into the game.'

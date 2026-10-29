<#
  Install DualSubtitle (dual-language text) into the game (UXM loose-file setup)

  Usage (from the DualSubtitle folder):
    powershell -ExecutionPolicy Bypass -File install.ps1
    powershell -ExecutionPolicy Bypass -File install.ps1 -GameDir "D:\steam\steamapps\common\DARK SOULS III\Game"

  Behavior:
    * copies msg\<lang>\*.msgbnd.dcx into <game>\msg\<lang>\
    * overwrites are backed up to <game>\.dualsub-backup\ and recorded in <game>\.dualsub-manifest.json
    * restore.ps1 replays the manifest byte-for-byte
#>
param(
    [string]$GameDir = '',
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$ModRoot = $PSScriptRoot

function Find-DS3Game {
    $cands = @()
    if ($env:DS3_GAME_DIR) { $cands += $env:DS3_GAME_DIR }
    $steam = $null
    try { $steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction Stop).SteamPath } catch { }
    if ($steam) {
        $cands += (Join-Path $steam 'steamapps\common\DARK SOULS III\Game')
        $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) {
            foreach ($m in [regex]::Matches((Get-Content -LiteralPath $vdf -Raw), '"path"\s+"([^"]+)"')) {
                $lib = $m.Groups[1].Value -replace '\\\\', '\'
                $cands += (Join-Path $lib 'steamapps\common\DARK SOULS III\Game')
            }
        }
    }
    foreach ($d in 'C:', 'D:', 'E:', 'F:') {
        $cands += "${d}\steam\steamapps\common\DARK SOULS III\Game"
        $cands += "${d}\SteamLibrary\steamapps\common\DARK SOULS III\Game"
    }
    $cands += 'C:\Program Files (x86)\Steam\steamapps\common\DARK SOULS III\Game'
    foreach ($c in $cands) {
        if ($c -and (Test-Path -LiteralPath (Join-Path $c 'DarkSoulsIII.exe'))) { return $c }
    }
    return $null
}

if (-not $GameDir) { $GameDir = Find-DS3Game }
if (-not $GameDir) {
    throw ('Game folder not found. Pass it explicitly, e.g.' + "`n" +
           '  powershell -ExecutionPolicy Bypass -File install.ps1 -GameDir "X:\STEAM\steamapps\common\DARK SOULS III\Game"')
}
if (-not (Test-Path (Join-Path $GameDir 'DarkSoulsIII.exe'))) {
    throw "Game directory not found (DarkSoulsIII.exe missing): $GameDir"
}
if (-not $Force -and (Get-Process -Name 'DarkSoulsIII' -ErrorAction SilentlyContinue)) {
    throw 'The game is running. Close it before installing (or pass -Force).'
}

$manifestPath = Join-Path $GameDir '.dualsub-manifest.json'
$backupRoot = Join-Path $GameDir '.dualsub-backup'
$records = @()

$msgRoot = Join-Path $ModRoot 'msg'
if (-not (Test-Path -LiteralPath $msgRoot)) {
    throw ("This folder has no msg\ folder - it looks like a git checkout, not the release package.`n" +
           "Download the release zip (which contains msg\) from:`n" +
           "  https://github.com/xiangchi7/darksoulsiii-1.15.0-dual-subtitle/releases/latest")
}

$files = Get-ChildItem $msgRoot -Recurse -File
foreach ($f in $files) {
    $rel = $f.FullName.Substring($ModRoot.Length + 1)
    $target = Join-Path $GameDir $rel
    $existed = Test-Path -LiteralPath $target
    $backupRel = $null

    if ($existed) {
        $backupRel = '.dualsub-backup\' + $rel
        $backupPath = Join-Path $GameDir $backupRel
        if (-not (Test-Path -LiteralPath $backupPath)) {
            New-Item -ItemType Directory -Force (Split-Path $backupPath) | Out-Null
            Copy-Item -LiteralPath $target -Destination $backupPath -Force
        }
    }

    New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
    Copy-Item -LiteralPath $f.FullName -Destination $target -Force

    $records += [pscustomobject]@{
        path    = $rel
        existed = $existed
        backup  = $backupRel
        hash    = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
        size    = (Get-Item -LiteralPath $target).Length
    }
    Write-Host ("  installed " + $rel)
}

$manifest = [pscustomobject]@{
    version     = '1.0'
    installedAt = (Get-Date).ToString('s')
    gameDir     = $GameDir
    files       = $records
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Write-Host ""
Write-Host ("Installed: " + $records.Count + " files")
Write-Host ("Backup dir: " + $backupRoot)
Write-Host "Start the game offline to apply. Run restore.ps1 to uninstall."

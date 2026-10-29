<#
  Uninstall DualSubtitle: replay .dualsub-manifest.json byte-for-byte
    powershell -ExecutionPolicy Bypass -File restore.ps1
    powershell -ExecutionPolicy Bypass -File restore.ps1 -GameDir "X:\...\DARK SOULS III\Game"
    powershell -ExecutionPolicy Bypass -File restore.ps1 -DryRun      # report only
#>
param(
    [string]$GameDir = '',
    [switch]$Force,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'

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
           '  powershell -ExecutionPolicy Bypass -File restore.ps1 -GameDir "X:\STEAM\steamapps\common\DARK SOULS III\Game"')
}

if (-not $Force -and (Get-Process -Name 'DarkSoulsIII' -ErrorAction SilentlyContinue)) {
    throw 'The game is running. Close it first (or pass -Force).'
}

$manifestPath = Join-Path $GameDir '.dualsub-manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Host 'No install record (.dualsub-manifest.json not found); nothing to restore.'
    exit 0
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json

$failed = @()
foreach ($rec in $manifest.files) {
    $target = Join-Path $GameDir $rec.path
    if ($rec.existed -and $rec.backup) {
        $backupPath = Join-Path $GameDir $rec.backup
        if (Test-Path -LiteralPath $backupPath) {
            if ($DryRun) {
                Write-Host ("  would restore " + $rec.path)
            } else {
                Copy-Item -LiteralPath $backupPath -Destination $target -Force
                Remove-Item -LiteralPath $backupPath -Force
                Write-Host ("  restored " + $rec.path)
            }
        } else {
            Write-Warning ("backup missing, skipped: " + $rec.path)
            $failed += $rec.path
        }
    } else {
        if (Test-Path -LiteralPath $target) {
            if ($DryRun) {
                Write-Host ("  would remove " + $rec.path)
            } else {
                Remove-Item -LiteralPath $target -Force
                Write-Host ("  removed " + $rec.path)
            }
        }
    }
}

if ($DryRun) {
    Write-Host 'Dry run: nothing was changed.'
    exit 0
}

# A partially failed restore keeps its manifest + backups so it can be replayed.
if ($failed.Count -gt 0) {
    Write-Warning ("$($failed.Count) file(s) could not be restored; the manifest and the remaining backups were kept. Put the missing backups back and rerun restore.ps1.")
    exit 1
}

# 清理空目录
$backupRoot = Join-Path $GameDir '.dualsub-backup'
if (Test-Path -LiteralPath $backupRoot) {
    Get-ChildItem -LiteralPath $backupRoot -Recurse -Directory -Force |
        Sort-Object { $_.FullName.Length } -Descending |
        ForEach-Object {
            if (-not (Get-ChildItem -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue)) {
                Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
            }
        }
    if (-not (Get-ChildItem -LiteralPath $backupRoot -Force -ErrorAction SilentlyContinue)) {
        Remove-Item -LiteralPath $backupRoot -Force
    }
}
Remove-Item -LiteralPath $manifestPath -Force
Write-Host 'Restore complete.'

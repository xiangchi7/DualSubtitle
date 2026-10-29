<#
  Uninstall DualSubtitle: replay .dualsub-manifest.json byte-for-byte
    powershell -ExecutionPolicy Bypass -File restore.ps1
#>
param(
    [string]$GameDir = 'D:\steam\steamapps\common\DARK SOULS III\Game',
    [switch]$Force
)
$ErrorActionPreference = 'Stop'

if (-not $Force -and (Get-Process -Name 'DarkSoulsIII' -ErrorAction SilentlyContinue)) {
    throw 'The game is running. Close it first (or pass -Force).'
}

$manifestPath = Join-Path $GameDir '.dualsub-manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Host 'No install record (.dualsub-manifest.json not found); nothing to restore.'
    exit 0
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json

foreach ($rec in $manifest.files) {
    $target = Join-Path $GameDir $rec.path
    if ($rec.existed -and $rec.backup) {
        $backupPath = Join-Path $GameDir $rec.backup
        if (Test-Path -LiteralPath $backupPath) {
            Copy-Item -LiteralPath $backupPath -Destination $target -Force
            Remove-Item -LiteralPath $backupPath -Force
            Write-Host ("  restored " + $rec.path)
        } else {
            Write-Warning ("backup missing, skipped: " + $rec.path)
        }
    } else {
        if (Test-Path -LiteralPath $target) {
            Remove-Item -LiteralPath $target -Force
            Write-Host ("  removed " + $rec.path)
        }
    }
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

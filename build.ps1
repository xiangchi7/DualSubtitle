<#
  Regenerate dual-language text (run after editing tools\dualsub.config.json)

  Usage:
    powershell -ExecutionPolicy Bypass -File build.ps1
    powershell -ExecutionPolicy Bypass -File build.ps1 -GameDir "D:\steam\steamapps\common\DARK SOULS III\Game"
#>
param(
    [string]$GameDir = 'D:\steam\steamapps\common\DARK SOULS III\Game'
)
$ErrorActionPreference = 'Stop'
$ModRoot = $PSScriptRoot

$source = Join-Path $ModRoot 'source'
if (Test-Path $source) { $srcArg = @('--source', $source) } else { $srcArg = @() }

python (Join-Path $ModRoot 'tools\dualsub.py') `
    --game $GameDir `
    @srcArg `
    --config (Join-Path $ModRoot 'tools\dualsub.config.json') `
    --out $ModRoot
if ($LASTEXITCODE -ne 0) { throw "Build failed (exit $LASTEXITCODE)" }

Write-Host ""
Write-Host "Build complete. Run install.ps1 to install into the game."

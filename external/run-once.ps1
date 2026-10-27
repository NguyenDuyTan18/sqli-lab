[CmdletBinding()]
param(
    [string] $Target = '127.0.0.1:18080',
    [string] $StateFile = (Join-Path (Split-Path -Parent $PSScriptRoot) 'runtime/manual-state.json')
)
$ErrorActionPreference = 'Stop'
$labRoot = Split-Path -Parent $PSScriptRoot
$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction Stop }
& $python.Source (Join-Path $labRoot 'provisioning/files/monitor.py') --target $Target --state $StateFile --once
exit $LASTEXITCODE

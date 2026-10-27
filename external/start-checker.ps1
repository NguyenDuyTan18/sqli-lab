[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $SshConfig,
    [string] $SshHost = 'checker',
    [ValidateSet('check', 'round')] [string] $Action = 'round',
    [string[]] $Targets = @(),
    [ValidateRange(1, 86400)] [int] $Interval = 60,
    [switch] $Once
)
$ErrorActionPreference = 'Stop'
$resolvedConfig = (Resolve-Path -LiteralPath $SshConfig).Path
$labRoot = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $labRoot 'runtime'
$resultsFile = Join-Path $runtime 'external-results.jsonl'
$ssh = (Get-Command ssh -ErrorAction Stop).Source

if ($SshHost -notmatch '^[a-zA-Z0-9][a-zA-Z0-9._-]*$') {
    throw 'SshHost must be a host alias from the downloaded management SSH config.'
}
foreach ($targetId in $Targets) {
    if ($targetId -notmatch '^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$') {
        throw "Invalid service ID: $targetId"
    }
}
New-Item -ItemType Directory -Path $runtime -Force | Out-Null

# Establish management access and let OpenSSH verify host fingerprints before
# starting the periodic controller loop.
Write-Host 'Checking SSH management access (verify host fingerprints if prompted)...'
& $ssh -F $resolvedConfig -o ConnectTimeout=15 $SshHost true
if ($LASTEXITCODE -ne 0) { throw 'SSH management connection failed. Check the downloaded config, key paths and host alias.' }

$request = @{ action = $Action }
if ($Targets.Count -gt 0) { $request.targets = @($Targets) }
$requestJson = $request | ConvertTo-Json -Compress -Depth 4
# Base64 keeps the payload shell-safe while the fixed remote command reads it
# from stdin. The remote runner only accepts allow-listed actions and service IDs.
$requestBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($requestJson))
$remoteCommand = "printf '%s' '$requestBase64' | sudo -n -u sqli-checker /opt/sqli-checker/run-command"

do {
    $output = & $ssh -F $resolvedConfig -T -o BatchMode=yes -o ConnectTimeout=15 $SshHost $remoteCommand 2>&1
    $sshExitCode = $LASTEXITCODE
    $remoteOutput = ($output | ForEach-Object { [string]$_ }) -join "`n"
    $remoteResult = $remoteOutput
    if ($remoteOutput) {
        try { $remoteResult = ConvertFrom-Json -InputObject $remoteOutput -ErrorAction Stop }
        catch { }
    }

    $record = [ordered]@{
        controller_time = [DateTime]::UtcNow.ToString('o')
        action = $Action
        ssh_exit_code = $sshExitCode
        result = $remoteResult
    }
    $jsonLine = $record | ConvertTo-Json -Compress -Depth 8
    Add-Content -LiteralPath $resultsFile -Value $jsonLine -Encoding UTF8
    Write-Host $jsonLine

    if ($Once) { exit $sshExitCode }
    Start-Sleep -Seconds $Interval
} while ($true)

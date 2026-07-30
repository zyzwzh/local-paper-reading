# run.ps1 — fixed entry point (never rename)
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot   # skill root
$Bin  = Join-Path $Root 'bin'

# --- 1. Hardware detection (Intel AIPC) -----------------------------------
$platform = Join-Path $Bin 'platform.exe'
if (Test-Path $platform) {
    $isAipc = (& $platform --is-aipc).Trim()
    if ($isAipc -ne '1') {
        Write-Output 'This skill requires an Intel AIPC platform.'
        exit 1
    }
}

# --- 2. Ensure Python environment -----------------------------------------
& (Join-Path $PSScriptRoot 'install-env.ps1')
if ($LASTEXITCODE -ne 0) { exit 1 }

# --- 3. Resolve venv python ------------------------------------------------
$infoPath = Join-Path $Root 'info.json'
$info = Get-Content $infoPath -Raw | ConvertFrom-Json
$venv  = Join-Path $env:USERPROFILE ".openvino\venv\$($info.venv_name)"
$python = Join-Path $venv 'Scripts\python.exe'

# --- 4. Launch client (forward all args) -----------------------------------
& $python (Join-Path $PSScriptRoot 'client.py') @args
exit $LASTEXITCODE

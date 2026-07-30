# install-env.ps1 — ensure Python venv + deps are installed
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Bin  = Join-Path $Root 'bin'

# --- 1. Find or download uv.exe -------------------------------------------
$uv = Join-Path $Bin 'uv.exe'
if (-not (Test-Path $uv)) {
    Write-Output '[install-env] Downloading uv.exe ...'
    New-Item -ItemType Directory -Force -Path $Bin | Out-Null
    $uvUrl = 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.exe'
    Invoke-WebRequest -Uri $uvUrl -OutFile $uv -UseBasicParsing
}

# --- 2. Read info.json -----------------------------------------------------
$infoPath = Join-Path $Root 'info.json'
$info = Get-Content $infoPath -Raw | ConvertFrom-Json
$venvDir = Join-Path $env:USERPROFILE ".openvino\venv\$($info.venv_name)"

# --- 3. Create venv --------------------------------------------------------
if (-not (Test-Path $venvDir)) {
    Write-Output "[install-env] Creating venv: $($info.venv_name) (Python $($info.python_version))"
    & $uv venv --python $info.python_version $venvDir
}

# --- 4. Install dependencies ----------------------------------------------
$reqPath = Join-Path $Root 'requirements.txt'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'

# Check if deps already installed (hash cache)
$hashFile = Join-Path $venvDir '.req_hash'
$currentHash = (Get-FileHash $reqPath -Algorithm SHA256).Hash
if (Test-Path $hashFile) {
    $cachedHash = Get-Content $hashFile -Raw
    if ($cachedHash.Trim() -eq $currentHash) {
        Write-Output '[install-env] Dependencies already up to date.'
        exit 0
    }
}

Write-Output '[install-env] Installing dependencies (mirror first, PyPI fallback) ...'
# Try mirror first
& $uv pip install --python $venvPython -r $reqPath -i https://mirrors.aliyun.com/pypi/simple/ 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Output '[install-env] Mirror failed, falling back to PyPI ...'
    & $uv pip install --python $venvPython -r $reqPath
}
if ($LASTEXITCODE -ne 0) {
    Write-Output '[install-env] Failed to install dependencies.'
    exit 1
}

# Save hash
$currentHash | Out-File -FilePath $hashFile -NoNewline
Write-Output '[install-env] Done.'

# --- 5. Install wheels (if any) -------------------------------------------
$wheelsDir = Join-Path $Root 'wheels'
if (Test-Path $wheelsDir) {
    $wheels = Get-ChildItem -Path $wheelsDir -Filter '*.whl'
    foreach ($wheel in $wheels) {
        Write-Output "[install-env] Installing wheel: $($wheel.Name)"
        & $uv pip install --python $venvPython $wheel.FullName
    }
}

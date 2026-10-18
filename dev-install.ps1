[CmdletBinding()]
param(
    [switch]$Test,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = if ($env:VENV_DIR) { $env:VENV_DIR } else { Join-Path $ProjectRoot ".venv" }
$VenvPython = Join-Path $VenvPath "Scripts/python.exe"

function Assert-LastExitCode {
    param([string]$Operation)
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with exit code $LASTEXITCODE."
    }
}

try {
    & $Python -c "import sys; raise SystemExit(sys.version_info < (3, 10))"
    if ($LASTEXITCODE -ne 0) { throw "Templar requires Python 3.10 or newer." }
}
catch {
    throw "Python executable '$Python' was not found or is older than Python 3.10. Use -Python to select one."
}

Set-Location $ProjectRoot

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment: $VenvPath"
    & $Python -m venv $VenvPath
    Assert-LastExitCode "Virtual-environment creation"
}

Write-Host "Installing Templar in editable development mode..."
& $VenvPython -m pip install --upgrade pip
Assert-LastExitCode "pip upgrade"
& $VenvPython -m pip install -e ".[dev]"
Assert-LastExitCode "Templar development installation"

Write-Host ""
Write-Host "Development environment is ready."
Write-Host "Activate it with: & `"$VenvPath\Scripts\Activate.ps1`""
Write-Host "Run the CLI with:  & `"$VenvPath\Scripts\templar.exe`" --help"

if ($Test) {
    Write-Host ""
    Write-Host "Running tests..."
    & $VenvPython -m pytest -q
    Assert-LastExitCode "Test suite"
}

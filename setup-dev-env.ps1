#Requires -Version 5.1
$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DevTools = Join-Path $env:LOCALAPPDATA 'Programs\DevTools'
$PythonExe = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
$JavaExe = Join-Path $DevTools 'java\jdk-21.0.11+10\bin\java.exe'
$MvnCmd = Join-Path $DevTools 'maven\apache-maven-3.9.16\bin\mvn.cmd'
$MysqlExe = Join-Path $DevTools 'mysql\PFiles64\MySQL\MySQL Server 8.4\bin\mysql.exe'
$MysqldExe = Join-Path $DevTools 'mysql\PFiles64\MySQL\MySQL Server 8.4\bin\mysqld.exe'
$MysqlConfig = Join-Path $DevTools 'mysql\my.ini'
$EngineRoot = Join-Path $Root 'overseas-loc-mvp'
$WorkbenchDir = Get-ChildItem -LiteralPath $Root -Directory | Where-Object {
    (Test-Path -LiteralPath (Join-Path $_.FullName 'web\index.html')) -and
    (Test-Path -LiteralPath (Join-Path $_.FullName 'app\main.py'))
} | Select-Object -First 1
$Fail = $false

Write-Host '============================================================'
Write-Host ' Overseas Video Loc - Dev Environment Check / Setup'
Write-Host '============================================================'

function Resolve-Python {
    if (Test-Path -LiteralPath $PythonExe) { return $PythonExe }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { return $cmd.Source }
    return $null
}

function Show-Status {
    param([string]$Name, [string]$Path)
    if (Test-Path -LiteralPath $Path) {
        Write-Host "[OK] $Name"
        Write-Host "     $Path"
        return $true
    }
    Write-Host "[MISS] $Name"
    Write-Host "       $Path"
    return $false
}

function Ensure-Venv {
    param([string]$Label, [string]$ProjectDir)
    if (-not (Test-Path -LiteralPath $ProjectDir)) {
        Write-Host "[MISS] $Label project dir: $ProjectDir"
        return $false
    }
    $venvPy = Join-Path $ProjectDir '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $venvPy) { return $true }
    $py = Resolve-Python
    if (-not $py) {
        Write-Host "[MISS] Python required to create $Label venv"
        return $false
    }
    Write-Host "[SETUP] Creating $Label venv..."
    & $py -m venv (Join-Path $ProjectDir '.venv')
    if (-not (Test-Path -LiteralPath $venvPy)) { return $false }
    $req = Join-Path $ProjectDir 'requirements.txt'
    if (Test-Path -LiteralPath $req) {
        & $venvPy -m pip install --disable-pip-version-check -q -r $req
    }
    Write-Host "[OK] $Label venv ready"
    return $true
}

$pyResolved = Resolve-Python
if (-not $pyResolved) {
    Write-Host '[MISS] Python 3.12'
    Write-Host "       $PythonExe"
    $Fail = $true
} else {
    Write-Host "[OK] Python"
    Write-Host "     $pyResolved"
}

if ($WorkbenchDir) {
    if (-not (Ensure-Venv 'Workbench (8788)' $WorkbenchDir.FullName)) { $Fail = $true }
} else {
    Write-Host '[MISS] Workbench directory (web + app/main.py)'
    $Fail = $true
}

if (-not (Ensure-Venv 'Delivery engine' $EngineRoot)) { $Fail = $true }

Write-Host ''
Write-Host '===== Optional Phase 2 tools ====='
[void](Show-Status 'Java (optional)' $JavaExe)
[void](Show-Status 'Maven (optional)' $MvnCmd)
[void](Show-Status 'MySQL client (optional mirror/import)' $MysqlExe)

Write-Host ''
Write-Host '===== MySQL port 3306 ====='
$listening = Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue
if ($listening) {
    Write-Host '[OK] listening'
} elseif ((Test-Path -LiteralPath $MysqldExe) -and (Test-Path -LiteralPath $MysqlConfig)) {
    Start-Process -FilePath $MysqldExe -ArgumentList "--defaults-file=$MysqlConfig" -WindowStyle Hidden
    Start-Sleep -Seconds 2
    if (Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue) {
        Write-Host '[OK] started and listening'
    } else {
        Write-Host '[INFO] not listening; web pages still use CSV/JSON/runs data'
    }
} else {
    Write-Host '[INFO] mysqld or config missing; only MySQL import is unavailable'
}

Write-Host ''
Write-Host '===== Local workbench ====='
try {
    $null = Invoke-RestMethod -Uri 'http://127.0.0.1:8788/api/health' -TimeoutSec 2
    Write-Host '[OK] Workbench: http://127.0.0.1:8788'
} catch {
    Write-Host '[INFO] Workbench is not running — use 启动工作台.cmd'
}

Write-Host ''
Write-Host '===== If Python is missing ====='
Write-Host 'winget install Python.Python.3.12'
Write-Host ''
Write-Host 'Note: CSV/JSON/runs are the source of truth; MySQL is optional.'
Write-Host ''
if ($Fail) { Write-Host 'Result: action needed.'; exit 1 }
Write-Host 'Result: ready.'
exit 0

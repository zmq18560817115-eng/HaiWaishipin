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
$VenvPy = Join-Path $Root 'overseas-loc-mvp\.venv\Scripts\python.exe'
$Fail = $false

Write-Host '============================================================'
Write-Host ' Overseas Video Loc - Dev Environment Check'
Write-Host '============================================================'

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

if (-not (Show-Status 'Python' $PythonExe)) { $Fail = $true }
if (-not (Show-Status 'Java' $JavaExe)) { $Fail = $true }
if (-not (Show-Status 'Maven' $MvnCmd)) { $Fail = $true }
if (-not (Show-Status 'MySQL' $MysqlExe)) { $Fail = $true }
if (-not (Show-Status 'MVP venv' $VenvPy)) { $Fail = $true }

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
        Write-Host '[WARN] not listening'
        $Fail = $true
    }
} else {
    Write-Host '[WARN] mysqld or config missing'
    $Fail = $true
}

Write-Host ''
Write-Host '===== MVP page ====='
try {
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8787/api/health' -TimeoutSec 2
    Write-Host '[OK] page running at http://127.0.0.1:8787'
} catch {
    Write-Host '[INFO] page not running. Double-click 启动工作台.cmd'
}

Write-Host ''
Write-Host '===== Install only if [MISS] above ====='
Write-Host 'winget install Python.Python.3.12'
Write-Host 'winget install Apache.Maven'
Write-Host 'winget install Oracle.MySQL'
Write-Host ''
Write-Host 'Note: current page MVP uses files only (runs/ + knowledge/).'
Write-Host 'MySQL/Maven are Phase 2 placeholders, not required for Step 1-5 demo.'
Write-Host ''
if ($Fail) { Write-Host 'Result: action needed.'; exit 1 }
Write-Host 'Result: ready.'
exit 0

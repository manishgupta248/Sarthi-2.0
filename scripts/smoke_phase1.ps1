$root = "D:\Sarthi"
$py = "$root\.venv\Scripts\python.exe"
$script:fail = 0
function Check($name, $ok) {
    if ($ok) { Write-Host "PASS  $name" -ForegroundColor Green }
    else { Write-Host "FAIL  $name" -ForegroundColor Red; $script:fail++ }
}
Set-Location $root
Write-Host "=== Sarthi Phase 1 smoke test ===" -ForegroundColor Cyan

Check "On branch develop" ((git branch --show-current) -eq "develop")

$files = "manage.py","requirements.txt","requirements-lock.txt",".env",".env.example",
  "config\settings\base.py","config\settings\development.py","config\settings\production.py","config\urls.py",
  "apps\core\exceptions.py","apps\core\middleware.py","apps\core\logging_utils.py","apps\core\models.py",
  "apps\accounts\models.py","apps\accounts\migrations\0001_initial.py",
  "templates\404.html","templates\500.html","templates\errors\sarthi_error.html","docs\ARCHITECTURE.md"
foreach ($f in $files) { Check "File $f" (Test-Path "$root\$f") }

& $py manage.py check 2>&1 | Out-Null
Check "Django system check" ($LASTEXITCODE -eq 0)

& $py manage.py makemigrations --check --dry-run 2>&1 | Out-Null
Check "No missing migrations" ($LASTEXITCODE -eq 0)

& $py manage.py test 2>&1 | Out-Null
Check "Automated tests pass" ($LASTEXITCODE -eq 0)

Check "Log file created" (Test-Path "$root\logs\sarthi.log")

git ls-files --error-unmatch .env 2>&1 | Out-Null
Check ".env is NOT tracked by Git" ($LASTEXITCODE -ne 0)
$dbTracked = git ls-files "*.sqlite3"
Check "No database file tracked by Git" (-not $dbTracked)

$proc = Start-Process -FilePath $py -ArgumentList "manage.py","runserver","8765","--noreload" -WorkingDirectory $root -PassThru -WindowStyle Hidden
try {
    Start-Sleep -Seconds 7
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health/" -TimeoutSec 10
    Check "Live /health/ answers (app and database ok)" (($r.app -eq "ok") -and ($r.database -eq "ok"))
} catch {
    Check "Live /health/ answers (app and database ok)" $false
} finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

Write-Host ""
if ($script:fail -eq 0) { Write-Host "ALL CHECKS PASSED" -ForegroundColor Green }
else { Write-Host "$($script:fail) CHECK(S) FAILED" -ForegroundColor Red }

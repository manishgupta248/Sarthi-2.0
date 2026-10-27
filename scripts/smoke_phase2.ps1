$root = "D:\Sarthi"
$py = "$root\.venv\Scripts\python.exe"
$script:fail = 0
function Check($name, $ok) {
    if ($ok) { Write-Host "PASS  $name" -ForegroundColor Green }
    else { Write-Host "FAIL  $name" -ForegroundColor Red; $script:fail++ }
}
Set-Location $root
Write-Host "=== Sarthi Phase 2 smoke test ===" -ForegroundColor Cyan

Check "On branch develop" ((git branch --show-current) -eq "develop")

$files = "static\vendor\bootstrap\bootstrap.min.css","static\vendor\bootstrap\bootstrap.bundle.min.js",
  "static\vendor\bootstrap-icons\bootstrap-icons.min.css","static\vendor\bootstrap-icons\fonts\bootstrap-icons.woff2",
  "static\css\sarthi.css","static\js\sarthi.js",
  "templates\base.html","templates\core\dashboard.html","templates\core\backups.html","templates\core\audit.html","templates\registration\login.html",
  "apps\core\backup.py","apps\core\audit.py","apps\core\signals.py","apps\core\navigation.py","apps\core\migrations\0001_initial.py",
  "docs\ARCHITECTURE.md"
foreach ($f in $files) { Check "File $f" ((Test-Path "$root\$f") -and ((Get-Item "$root\$f").Length -gt 200)) }

& $py manage.py check 2>&1 | Out-Null
Check "Django system check" ($LASTEXITCODE -eq 0)
& $py manage.py makemigrations --check --dry-run 2>&1 | Out-Null
Check "No missing migrations" ($LASTEXITCODE -eq 0)
& $py manage.py test 2>&1 | Out-Null
Check "Automated tests pass" ($LASTEXITCODE -eq 0)

$envText = Get-Content "$root\.env" -Raw
Check "Backup encryption key is set in .env" ($envText -match "BACKUP_ENCRYPTION_KEY=\S+")

$out = & $py manage.py backup_db --kind manual 2>&1 | Out-String
$code = $LASTEXITCODE
Check "Backup created and verified" (($code -eq 0) -and ($out -match "created and verified"))
Check "Backup file is encrypted (.zip.enc)" ($out -match "\.zip\.enc")
$out2 = & $py manage.py verify_backup 2>&1 | Out-String
$code = $LASTEXITCODE
Check "Newest backup passes the full check" (($code -eq 0) -and ($out2 -match "is healthy"))

Check "Daily backup task is scheduled" ($null -ne (Get-ScheduledTask -TaskName "Sarthi Daily Backup" -ErrorAction SilentlyContinue))

git ls-files --error-unmatch .env 2>&1 | Out-Null
Check ".env is NOT tracked by Git" ($LASTEXITCODE -ne 0)
$trackedBackups = git ls-files backups | Where-Object { $_ -ne "backups/.gitkeep" }
Check "No backup files tracked by Git" (-not $trackedBackups)
$trackedDb = git ls-files "*.sqlite3"
Check "No database file tracked by Git" (-not $trackedDb)

$proc = Start-Process -FilePath $py -ArgumentList "manage.py","runserver","8766","--noreload" -WorkingDirectory $root -PassThru -WindowStyle Hidden
try {
    Start-Sleep -Seconds 8
    $login = Invoke-WebRequest -Uri "http://127.0.0.1:8766/accounts/login/" -UseBasicParsing -TimeoutSec 10
    Check "Live login page loads" (($login.StatusCode -eq 200) -and ($login.Content -match "Sarthi"))
    $css = Invoke-WebRequest -Uri "http://127.0.0.1:8766/static/css/sarthi.css" -UseBasicParsing -TimeoutSec 10
    Check "Live stylesheet is served" ($css.StatusCode -eq 200)
    $h = Invoke-RestMethod -Uri "http://127.0.0.1:8766/health/" -TimeoutSec 10
    Check "Live /health/ answers (app and database ok)" (($h.app -eq "ok") -and ($h.database -eq "ok"))
} catch {
    Check "Live server checks ran without error ($($_.Exception.Message))" $false
} finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    Get-NetTCPConnection -LocalPort 8766 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

Write-Host ""
if ($script:fail -eq 0) { Write-Host "ALL CHECKS PASSED" -ForegroundColor Green }
else { Write-Host "$($script:fail) CHECK(S) FAILED" -ForegroundColor Red }

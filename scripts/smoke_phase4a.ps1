$root = "D:\Sarthi"
$py = "$root\.venv\Scripts\python.exe"
$script:fail = 0
function Check($name, $ok) {
    if ($ok) { Write-Host "PASS  $name" -ForegroundColor Green }
    else { Write-Host "FAIL  $name" -ForegroundColor Red; $script:fail++ }
}
Set-Location $root
Write-Host "=== Sarthi Phase 4A smoke test ===" -ForegroundColor Cyan

Check "On branch develop" ((git branch --show-current) -eq "develop")

$files = "apps\wealth\models.py","apps\wealth\services.py","apps\wealth\views.py","apps\wealth\export.py","apps\wealth\forms.py",
  "apps\wealth\migrations\0001_initial.py","apps\wealth\migrations\0002_load_account_types.py",
  "apps\core\templatetags\sarthi_extras.py",
  "templates\wealth\dashboard.html","templates\wealth\account_detail.html","templates\wealth\account_list.html","templates\wealth\update_balances.html",
  "static\js\wealth.js","static\js\wealth_charts.js","static\vendor\chartjs\chart.umd.js","docs\ARCHITECTURE.md"
foreach ($f in $files) { Check "File $f" ((Test-Path "$root\$f") -and ((Get-Item "$root\$f").Length -gt 200)) }

& $py manage.py check 2>&1 | Out-Null
Check "Django system check" ($LASTEXITCODE -eq 0)
& $py manage.py makemigrations --check --dry-run 2>&1 | Out-Null
Check "No missing migrations" ($LASTEXITCODE -eq 0)
& $py manage.py test 2>&1 | Out-Null
Check "Automated tests pass" ($LASTEXITCODE -eq 0)

$envText = Get-Content "$root\.env" -Raw
Check "Backup encryption key is set in .env" ($envText -match "BACKUP_ENCRYPTION_KEY=\S+")
Check "Field encryption key is set in .env" ($envText -match "FIELD_ENCRYPTION_KEY=\S+")

$out = & $py manage.py backup_db --kind manual 2>&1 | Out-String
$code = $LASTEXITCODE
Check "Backup created and verified" (($code -eq 0) -and ($out -match "created and verified"))
$out2 = & $py manage.py verify_backup 2>&1 | Out-String
$code = $LASTEXITCODE
Check "Newest backup passes the full check" (($code -eq 0) -and ($out2 -match "is healthy"))

Check "Daily backup task is scheduled" ($null -ne (Get-ScheduledTask -TaskName "Sarthi Daily Backup" -ErrorAction SilentlyContinue))

git ls-files --error-unmatch .env 2>&1 | Out-Null
Check ".env is NOT tracked by Git" ($LASTEXITCODE -ne 0)
$trackedData = git ls-files data | Where-Object { $_ -ne "data/.gitkeep" }
Check "No vault or database files tracked by Git" (-not $trackedData)
$trackedBackups = git ls-files backups | Where-Object { $_ -ne "backups/.gitkeep" }
Check "No backup files tracked by Git" (-not $trackedBackups)
$trackedExports = git ls-files | Where-Object { $_ -like "*.xlsx" }
Check "No Excel files tracked by Git" (-not $trackedExports)

$proc = Start-Process -FilePath $py -ArgumentList "manage.py","runserver","8768","--noreload" -WorkingDirectory $root -PassThru -WindowStyle Hidden
try {
    Start-Sleep -Seconds 8
    $page = Invoke-WebRequest -Uri "http://127.0.0.1:8768/wealth/" -UseBasicParsing -TimeoutSec 10
    Check "Wealth page asks for sign-in when logged out" (($page.StatusCode -eq 200) -and ($page.Content -match "Sign in"))
    $chart = Invoke-WebRequest -Uri "http://127.0.0.1:8768/static/vendor/chartjs/chart.umd.js" -UseBasicParsing -TimeoutSec 10
    Check "Live chart library is served" ($chart.StatusCode -eq 200)
    $h = Invoke-RestMethod -Uri "http://127.0.0.1:8768/health/" -TimeoutSec 10
    Check "Live /health/ answers (app and database ok)" (($h.app -eq "ok") -and ($h.database -eq "ok"))
} catch {
    Check "Live server checks ran without error ($($_.Exception.Message))" $false
} finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    Get-NetTCPConnection -LocalPort 8768 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

Write-Host ""
if ($script:fail -eq 0) { Write-Host "ALL CHECKS PASSED" -ForegroundColor Green }
else { Write-Host "$($script:fail) CHECK(S) FAILED" -ForegroundColor Red }

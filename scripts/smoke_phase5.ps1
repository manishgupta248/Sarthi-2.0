$root = "D:\Sarthi"
$py = "$root\.venv\Scripts\python.exe"
$script:fail = 0
function Check($name, $ok) {
    if ($ok) { Write-Host "PASS  $name" -ForegroundColor Green }
    else { Write-Host "FAIL  $name" -ForegroundColor Red; $script:fail++ }
}
Set-Location $root
Write-Host "=== Sarthi Phase 5 smoke test ===" -ForegroundColor Cyan

Check "On branch develop" ((git branch --show-current) -eq "develop")
$files = "apps\wealth\networth.py","apps\wealth\forms_holdings.py","apps\wealth\views_holdings.py","apps\wealth\holding_export.py",
  "apps\wealth\test_networth.py","apps\wealth\migrations\0010_*.py",
  "templates\wealth\networth.html","templates\wealth\holding_list.html","templates\wealth\holding_detail.html",
  "templates\wealth\update_values.html","static\js\networth_charts.js"
foreach ($f in $files) { Check "File $f" ((Get-ChildItem "$root\$f" -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt 200 }).Count -ge 1) }

& $py manage.py check 2>&1 | Out-Null
Check "Django system check" ($LASTEXITCODE -eq 0)
& $py manage.py makemigrations --check --dry-run 2>&1 | Out-Null
Check "No missing migrations" ($LASTEXITCODE -eq 0)
& $py manage.py test 2>&1 | Out-Null
Check "Automated tests pass" ($LASTEXITCODE -eq 0)

$out = & $py manage.py backup_db --kind manual 2>&1 | Out-String
$code = $LASTEXITCODE
Check "Backup created and verified" (($code -eq 0) -and ($out -match "created and verified"))
Check "Daily backup task is scheduled" ($null -ne (Get-ScheduledTask -TaskName "Sarthi Daily Backup" -ErrorAction SilentlyContinue))

git ls-files --error-unmatch .env 2>&1 | Out-Null
Check ".env is NOT tracked by Git" ($LASTEXITCODE -ne 0)
$trackedData = git ls-files data | Where-Object { $_ -ne "data/.gitkeep" }
Check "No vault or database files tracked by Git" (-not $trackedData)
$trackedExports = git ls-files | Where-Object { $_ -like "*.xlsx" }
Check "No Excel files tracked by Git" (-not $trackedExports)

$proc = Start-Process -FilePath $py -ArgumentList "manage.py","runserver","8772","--noreload" -WorkingDirectory $root -PassThru -WindowStyle Hidden
try {
    Start-Sleep -Seconds 8
    $page = Invoke-WebRequest -Uri "http://127.0.0.1:8772/wealth/networth/" -UseBasicParsing -TimeoutSec 10
    Check "Net worth page asks for sign-in when logged out" (($page.StatusCode -eq 200) -and ($page.Content -match "Sign in"))
    $js = Invoke-WebRequest -Uri "http://127.0.0.1:8772/static/js/networth_charts.js" -UseBasicParsing -TimeoutSec 10
    Check "Live net worth chart script is served" ($js.StatusCode -eq 200)
    $h = Invoke-RestMethod -Uri "http://127.0.0.1:8772/health/" -TimeoutSec 10
    Check "Live /health/ answers (app and database ok)" (($h.app -eq "ok") -and ($h.database -eq "ok"))
} catch {
    Check "Live server checks ran without error ($($_.Exception.Message))" $false
} finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    Get-NetTCPConnection -LocalPort 8772 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

Write-Host ""
if ($script:fail -eq 0) { Write-Host "ALL CHECKS PASSED" -ForegroundColor Green }
else { Write-Host "$($script:fail) CHECK(S) FAILED" -ForegroundColor Red }

$root = "D:\Sarthi"
$py = "$root\.venv\Scripts\python.exe"
$script:fail = 0
function Check($name, $ok) {
    if ($ok) { Write-Host "PASS  $name" -ForegroundColor Green }
    else { Write-Host "FAIL  $name" -ForegroundColor Red; $script:fail++ }
}
Set-Location $root
Write-Host "=== Sarthi Phase 4A-2 smoke test ===" -ForegroundColor Cyan

Check "On branch develop" ((git branch --show-current) -eq "develop")
$files = "apps\vault\services.py","apps\wealth\views_attachments.py","apps\wealth\test_attachments.py",
  "apps\wealth\migrations\0003_accountremark.py","apps\wealth\migrations\0004_copy_remarks_to_entries.py",
  "templates\wealth\account_detail.html"
foreach ($f in $files) { Check "File $f" ((Test-Path "$root\$f") -and ((Get-Item "$root\$f").Length -gt 200)) }
Check "Old remarks column removed (migration 0005 exists)" ((Get-ChildItem "$root\apps\wealth\migrations\0005_*.py" -ErrorAction SilentlyContinue).Count -eq 1)

& $py manage.py check 2>&1 | Out-Null
Check "Django system check" ($LASTEXITCODE -eq 0)
& $py manage.py makemigrations --check --dry-run 2>&1 | Out-Null
Check "No missing migrations" ($LASTEXITCODE -eq 0)
& $py manage.py test 2>&1 | Out-Null
Check "Automated tests pass" ($LASTEXITCODE -eq 0)

$out = & $py manage.py backup_db --kind manual 2>&1 | Out-String
$code = $LASTEXITCODE
Check "Backup created and verified" (($code -eq 0) -and ($out -match "created and verified"))

git ls-files --error-unmatch .env 2>&1 | Out-Null
Check ".env is NOT tracked by Git" ($LASTEXITCODE -ne 0)
$trackedData = git ls-files data | Where-Object { $_ -ne "data/.gitkeep" }
Check "No vault or database files tracked by Git" (-not $trackedData)
$trackedExports = git ls-files | Where-Object { $_ -like "*.xlsx" }
Check "No Excel files tracked by Git" (-not $trackedExports)

$proc = Start-Process -FilePath $py -ArgumentList "manage.py","runserver","8769","--noreload" -WorkingDirectory $root -PassThru -WindowStyle Hidden
try {
    Start-Sleep -Seconds 8
    $h = Invoke-RestMethod -Uri "http://127.0.0.1:8769/health/" -TimeoutSec 10
    Check "Live /health/ answers (app and database ok)" (($h.app -eq "ok") -and ($h.database -eq "ok"))
} catch {
    Check "Live server check ran without error ($($_.Exception.Message))" $false
} finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    Get-NetTCPConnection -LocalPort 8769 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

Write-Host ""
if ($script:fail -eq 0) { Write-Host "ALL CHECKS PASSED" -ForegroundColor Green }
else { Write-Host "$($script:fail) CHECK(S) FAILED" -ForegroundColor Red }

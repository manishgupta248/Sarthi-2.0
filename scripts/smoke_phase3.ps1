$root = "D:\Sarthi"
$py = "$root\.venv\Scripts\python.exe"
$script:fail = 0
function Check($name, $ok) {
    if ($ok) { Write-Host "PASS  $name" -ForegroundColor Green }
    else { Write-Host "FAIL  $name" -ForegroundColor Red; $script:fail++ }
}
Set-Location $root
Write-Host "=== Sarthi Phase 3 smoke test ===" -ForegroundColor Cyan

Check "On branch develop" ((git branch --show-current) -eq "develop")

$files = "apps\core\fields.py","apps\core\forms.py","apps\core\backup.py",
  "apps\family\models.py","apps\family\views.py","apps\family\migrations\0001_initial.py",
  "apps\vault\models.py","apps\vault\validators.py","apps\vault\storage.py","apps\vault\views.py","apps\vault\migrations\0001_initial.py",
  "templates\family\person_list.html","templates\vault\document_list.html","templates\core\_form.html",
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
Check "Field encryption key is set in .env" ($envText -match "FIELD_ENCRYPTION_KEY=\S+")

$out = & $py manage.py backup_db --kind manual 2>&1 | Out-String
$code = $LASTEXITCODE
Check "Backup created and verified" (($code -eq 0) -and ($out -match "created and verified"))
$out2 = & $py manage.py verify_backup 2>&1 | Out-String
$code = $LASTEXITCODE
Check "Newest backup passes the full check (includes vault files)" (($code -eq 0) -and ($out2 -match "is healthy") -and ($out2 -match "vault files"))

Check "Daily backup task is scheduled" ($null -ne (Get-ScheduledTask -TaskName "Sarthi Daily Backup" -ErrorAction SilentlyContinue))

git ls-files --error-unmatch .env 2>&1 | Out-Null
Check ".env is NOT tracked by Git" ($LASTEXITCODE -ne 0)
$trackedVault = git ls-files data | Where-Object { $_ -ne "data/.gitkeep" }
Check "No vault or database files tracked by Git" (-not $trackedVault)
$trackedBackups = git ls-files backups | Where-Object { $_ -ne "backups/.gitkeep" }
Check "No backup files tracked by Git" (-not $trackedBackups)

$proc = Start-Process -FilePath $py -ArgumentList "manage.py","runserver","8767","--noreload" -WorkingDirectory $root -PassThru -WindowStyle Hidden
try {
    Start-Sleep -Seconds 8
    $login = Invoke-WebRequest -Uri "http://127.0.0.1:8767/vault/" -UseBasicParsing -TimeoutSec 10
    Check "Vault page asks for sign-in when logged out" (($login.StatusCode -eq 200) -and ($login.Content -match "Sign in"))
    $h = Invoke-RestMethod -Uri "http://127.0.0.1:8767/health/" -TimeoutSec 10
    Check "Live /health/ answers (app and database ok)" (($h.app -eq "ok") -and ($h.database -eq "ok"))
} catch {
    Check "Live server checks ran without error ($($_.Exception.Message))" $false
} finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    Get-NetTCPConnection -LocalPort 8767 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

Write-Host ""
if ($script:fail -eq 0) { Write-Host "ALL CHECKS PASSED" -ForegroundColor Green }
else { Write-Host "$($script:fail) CHECK(S) FAILED" -ForegroundColor Red }

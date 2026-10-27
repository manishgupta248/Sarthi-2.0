$root = "D:\Sarthi"
$script:fail = 0
function Check($name, $ok) {
    if ($ok) { Write-Host "PASS  $name" -ForegroundColor Green }
    else { Write-Host "FAIL  $name" -ForegroundColor Red; $script:fail++ }
}
Set-Location $root
Write-Host "=== Sarthi Phase 0 smoke test ===" -ForegroundColor Cyan
Check "Project folder exists" (Test-Path $root)
Check "Virtual environment exists" (Test-Path "$root\.venv\Scripts\python.exe")
foreach ($f in "apps","backups","data","logs","templates","static","docs","scripts") {
    Check "Folder $f" (Test-Path "$root\$f")
}
foreach ($f in "AGENTS.md","CURRENT_STATE.md","README.md",".gitignore","docs\DECISIONS.md","docs\ROADMAP.md") {
    Check "File $f" (Test-Path "$root\$f")
}
$branch = git branch --show-current
Check "On branch develop (now: $branch)" ($branch -eq "develop")
$remote = git remote get-url origin
Check "GitHub remote set ($remote)" ($remote -like "*github.com*")
git check-ignore -q .venv
Check ".venv is ignored by Git" ($LASTEXITCODE -eq 0)
git check-ignore -q .env
Check ".env is ignored by Git" ($LASTEXITCODE -eq 0)
git check-ignore -q db.sqlite3
Check "Database files are ignored by Git" ($LASTEXITCODE -eq 0)
$dirty = git status --porcelain
Check "No uncommitted changes" (-not $dirty)
Write-Host ""
if ($script:fail -eq 0) { Write-Host "ALL CHECKS PASSED" -ForegroundColor Green }
else { Write-Host "$($script:fail) CHECK(S) FAILED" -ForegroundColor Red }

$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$taskBundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskPython = if ($env:AG_PYTHON) { $env:AG_PYTHON } elseif (Test-Path $taskBundledPython) { $taskBundledPython } else { (Get-Command python).Source }
$taskNode = Join-Path $env:ProgramFiles 'nodejs\node.exe'
$taskNpm = Join-Path $env:ProgramFiles 'nodejs\npm.cmd'
$taskNpx = Join-Path $env:ProgramFiles 'nodejs\npx.cmd'
& $taskPython scripts/run_cloud_tests.py
if ($LASTEXITCODE) { exit $LASTEXITCODE }
& $taskNpm run test:ui
if ($LASTEXITCODE) { exit $LASTEXITCODE }
foreach ($taskFile in @('cloud-app.js','landing.js','assets/day-ui.js','assets/ui.js','cloud-sw.js')) {
  & $taskNode --check $taskFile
  if ($LASTEXITCODE) { exit $LASTEXITCODE }
}
& $taskNpx eslint assets
if ($LASTEXITCODE) { exit $LASTEXITCODE }
Invoke-RestMethod -Uri 'http://127.0.0.1:5187/v1/demo/reset' -Method Post -ContentType 'application/json' -Headers @{Origin='http://127.0.0.1:5187';'X-Preview-Role'='admin'} -Body '{}' | Out-Null
& $taskNpm run test:browser
exit $LASTEXITCODE


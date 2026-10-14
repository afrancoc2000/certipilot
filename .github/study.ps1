[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if ($env:COPILOT_ALLOW_ALL -and $env:COPILOT_ALLOW_ALL -ne 'false' -and $env:COPILOT_ALLOW_ALL -ne '0') {
    throw 'Remove COPILOT_ALLOW_ALL before using study-only approvals.'
}
$settingsJson = & copilot config --list --json
if ($LASTEXITCODE -ne 0) {
    throw "Cannot check Copilot permission settings (exit code $LASTEXITCODE)."
}
$settings = ($settingsJson -join "`n") | ConvertFrom-Json
if ($settings.defaultPermissionMode -and $settings.defaultPermissionMode -ne 'manual') {
    throw 'Study-only launch requires defaultPermissionMode manual; broader automatic permissions are already configured.'
}

$helper = Join-Path $PSScriptRoot 'study-helper.ps1'
$arguments = @('--mode', 'interactive', '--allow-tool', "shell($helper)")
foreach ($exam in Get-ChildItem -LiteralPath (Join-Path $root 'exams') -Directory) {
    if (-not (Test-Path -LiteralPath (Join-Path $exam.FullName 'exam.md') -PathType Leaf)) {
        continue
    }
    foreach ($name in @('progress.md', '.study-record-input.json', '.study-checkpoint-input.json')) {
        $path = Join-Path $exam.FullName "assets\$name"
        $arguments += @('--allow-tool', "write($path)")
    }
}

$prompt = 'Use interactive study with preapproved tracking. For coverage.py and session.py, invoke the absolute .github\study-helper.ps1 path directly with & and its named parameters, not through python, powershell, or pwsh. Write record/checkpoint payloads only to the fixed exam-local .study-record-input.json and .study-checkpoint-input.json files; cleanup through the helper. Ask me which exam or resume my unambiguous saved exam checkpoint. Never invent my answers.'
$arguments += @('-i', $prompt)

Push-Location $root
try {
    & copilot @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Copilot exited with code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

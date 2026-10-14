$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$fixture = Join-Path ([IO.Path]::GetTempPath()) ("certipilot-study-" + [guid]::NewGuid().ToString('N'))
$global:CertipilotStudyTest = @{
    Calls = @()
    PythonExit = 0
    PermissionMode = 'manual'
}

function Assert-True($Condition, $Message) {
    if (-not $Condition) { throw $Message }
}
function Assert-Rejected([scriptblock]$Action, [string]$Message) {
    $rejected = $false
    try { & $Action } catch { $rejected = $true }
    Assert-True $rejected $Message
}
function python {
    $global:CertipilotStudyTest.Calls += ,@($args)
    Set-Variable -Name LASTEXITCODE -Value $global:CertipilotStudyTest.PythonExit -Scope 1
}
function copilot {
    if ($args[0] -eq 'config') {
        @{ defaultPermissionMode = $global:CertipilotStudyTest.PermissionMode } | ConvertTo-Json -Compress
    } else {
        $global:CertipilotStudyTest.LaunchArgs = @($args)
    }
    Set-Variable -Name LASTEXITCODE -Value 0 -Scope 1
}

$previousAllowAll = $env:COPILOT_ALLOW_ALL
try {
    $github = Join-Path $fixture '.github'
    $assets = Join-Path $fixture 'exams\az-104\assets'
    New-Item -ItemType Directory -Path $github, $assets -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $root '.github\study.ps1') -Destination $github
    Copy-Item -LiteralPath (Join-Path $root '.github\study-helper.ps1') -Destination $github
    Set-Content -LiteralPath (Join-Path $fixture 'exams\az-104\exam.md') -Value 'Synthetic exam'
    $helper = Join-Path $github 'study-helper.ps1'
    $launcher = Join-Path $github 'study.ps1'

    & $helper -Tool coverage -Command audit -Exam az-104 -AsOf 2026-10-14 -Json
    $call = $global:CertipilotStudyTest.Calls[-1]
    Assert-True ($call[1] -eq (Join-Path $github 'skills\coverage-audit\scripts\coverage.py')) 'Wrong script.'
    Assert-True ($call[6] -eq $fixture) 'Root was not fixed to the fixture.'
    Assert-True ($call[-1] -eq '--json') 'JSON output was not forwarded.'
    Assert-Rejected { & $helper -Tool coverage -Command resume -Exam az-104 } 'Cross-tool command accepted.'
    Assert-Rejected { & $helper -Tool session -Command resume -Exam '..\outside' } 'Traversal accepted.'
    Assert-Rejected { & $helper -Tool session -Command resume -Exam az-305 } 'Missing exam accepted.'
    Assert-Rejected { & $helper -Tool coverage -Command audit -Exam az-104 -Root C:\outside } 'Root override accepted.'
    Assert-Rejected { & $helper -Tool coverage -Command audit -Exam az-104 -QuestionCount 10 } 'Wrong option accepted.'
    Assert-Rejected { & $helper -Tool coverage -Command record -Exam az-104 } 'Missing hash accepted.'
    Assert-Rejected { & $helper -Tool session -Command checkpoint -Exam az-104 -ExpectedSha256 missing } 'Missing payload accepted.'

    $record = Join-Path $assets '.study-record-input.json'
    $checkpoint = Join-Path $assets '.study-checkpoint-input.json'
    $progress = Join-Path $assets 'progress.md'
    Set-Content -LiteralPath $record, $checkpoint -Value '{}'
    Set-Content -LiteralPath $progress -Value 'Untouched'
    & $helper -Tool coverage -Command record -Exam az-104 -ExpectedSha256 ('a' * 64)
    Assert-True ($global:CertipilotStudyTest.Calls[-1] -contains $record) 'Record did not use fixed payload.'
    & $helper -Tool session -Command checkpoint -Exam az-104 -ExpectedSha256 missing
    Assert-True ($global:CertipilotStudyTest.Calls[-1] -contains $checkpoint) 'Checkpoint did not use fixed payload.'
    $global:CertipilotStudyTest.PythonExit = 2
    Assert-Rejected { & $helper -Tool session -Command resume -Exam az-104 } 'Helper failure was hidden.'
    $global:CertipilotStudyTest.PythonExit = 0
    & $helper -Tool coverage -Command cleanup -Exam az-104
    Assert-True (-not (Test-Path -LiteralPath $record)) 'Record input survived cleanup.'
    Assert-True (Test-Path -LiteralPath $checkpoint) 'Cleanup removed the other payload.'
    Assert-True ((Get-Content -LiteralPath $progress) -eq 'Untouched') 'Progress was altered.'
    & $helper -Tool coverage -Command cleanup -Exam az-104

    $env:COPILOT_ALLOW_ALL = $null
    & $launcher
    $launchArgs = $global:CertipilotStudyTest.LaunchArgs
    Assert-True ($launchArgs[0] -eq '--mode' -and $launchArgs[1] -eq 'interactive') 'Not interactive.'
    Assert-True ($launchArgs -contains "shell($helper)") 'Scoped helper approval missing.'
    Assert-True ($launchArgs -contains "write($progress)") 'Progress approval missing.'
    Assert-True ($launchArgs -contains "write($record)") 'Payload approval missing.'
    Assert-True (-not ($launchArgs -match 'allow-all|shell\(python|shell\(powershell|shell\(pwsh')) 'Broad approval added.'
    $global:CertipilotStudyTest.PermissionMode = 'allow-all'
    Assert-Rejected { & $launcher } 'Existing broad permissions were ignored.'
    $global:CertipilotStudyTest.PermissionMode = 'manual'
    $env:COPILOT_ALLOW_ALL = 'true'
    Assert-Rejected { & $launcher } 'Broad environment override was ignored.'
    Write-Output 'Study permission tests passed (synthetic storage; no learner files changed).'
} finally {
    $env:COPILOT_ALLOW_ALL = $previousAllowAll
    Remove-Item -LiteralPath $fixture -Recurse -Force
    Remove-Variable -Name CertipilotStudyTest -Scope Global
}

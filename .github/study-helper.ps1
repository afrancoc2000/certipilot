[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('coverage', 'session')]
    [string]$Tool,

    [Parameter(Mandatory)]
    [ValidateSet('audit', 'init', 'record', 'checkpoint', 'resume', 'mock-quotas', 'cleanup')]
    [string]$Command,

    [Parameter(Mandatory)]
    [ValidatePattern('^[a-z][a-z0-9]*-[a-z0-9]+$')]
    [string]$Exam,

    [string]$ExpectedSha256,
    [ValidatePattern('^\d{4}-\d{2}-\d{2}$')]
    [string]$AsOf,
    [ValidateRange(1, 3650)]
    [int]$StaleDays = 10,
    [ValidateRange(1, 100)]
    [int]$QuestionCount = 10,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$examPath = Join-Path $root "exams\$Exam"
if (-not (Test-Path -LiteralPath (Join-Path $examPath 'exam.md') -PathType Leaf)) {
    throw "Unknown exam: $Exam"
}

$commands = @{
    coverage = @('audit', 'init', 'record', 'cleanup')
    session = @('checkpoint', 'resume', 'mock-quotas', 'cleanup')
}
if ($Command -notin $commands[$Tool]) {
    throw "$Command is not a $Tool command."
}
if ($Tool -eq 'session' -and $PSBoundParameters.ContainsKey('StaleDays')) {
    throw 'StaleDays applies only to coverage.'
}
if ($Tool -eq 'coverage' -and $PSBoundParameters.ContainsKey('QuestionCount')) {
    throw 'QuestionCount applies only to session.'
}

$inputName = if ($Tool -eq 'coverage') { '.study-record-input.json' } else { '.study-checkpoint-input.json' }
$inputPath = Join-Path $examPath "assets\$inputName"
if ($Command -eq 'cleanup') {
    if ($PSBoundParameters.Keys | Where-Object { $_ -notin @('Tool', 'Command', 'Exam') }) {
        throw 'Cleanup accepts only Tool, Command, and Exam.'
    }
    if (Test-Path -LiteralPath $inputPath) {
        Remove-Item -LiteralPath $inputPath
    }
    return
}

$arguments = @('-B', (Join-Path $PSScriptRoot "skills\coverage-audit\scripts\$Tool.py"),
    $Command, '--exam', $Exam, '--root', $root)
if ($Command -in @('record', 'checkpoint')) {
    if (-not $ExpectedSha256) {
        throw "$Command requires ExpectedSha256."
    }
    if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
        throw "Prepare the validated input at $inputPath before running $Command."
    }
    $arguments += @('--input', $inputPath, '--expected-sha256', $ExpectedSha256)
} elseif ($ExpectedSha256) {
    throw 'ExpectedSha256 applies only to record or checkpoint.'
}
if ($AsOf) { $arguments += @('--as-of', $AsOf) }
if ($Tool -eq 'coverage') { $arguments += @('--stale-days', "$StaleDays") }
if ($Tool -eq 'session') { $arguments += @('--question-count', "$QuestionCount") }
if ($Json) { $arguments += '--json' }

& python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Study helper failed with exit code $LASTEXITCODE; no success is claimed."
}

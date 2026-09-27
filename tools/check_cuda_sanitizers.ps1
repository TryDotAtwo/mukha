param(
    [string]$Sanitizer = 'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\compute-sanitizer\compute-sanitizer.exe',
    [string]$Python = (Get-Command python).Source,
    [ValidateSet('tools/check_cuda_reference.py','tools/check_cuda_state.py')]
    [string]$TestScript = 'tools/check_cuda_reference.py',
    [ValidateSet('float32','float64')]
    [string]$Dtype = 'float32'
)
$ErrorActionPreference = 'Stop'
$checks = @()
if ($Dtype -eq 'float64' -and $TestScript -ne 'tools/check_cuda_state.py') { throw 'FP64 requires the state test' }
$testArgs = @()
if ($TestScript -eq 'tools/check_cuda_state.py') { $testArgs += @('--dtype',$Dtype) }
foreach ($checkName in @('memcheck', 'initcheck', 'racecheck', 'synccheck')) {
    $reportPrefix = if ($TestScript -eq 'tools/check_cuda_state.py') { 'cuda_state' } else { 'cuda' }
    if ($Dtype -eq 'float64') { $reportPrefix='cuda64_state' }
    $logPath = "reports/${reportPrefix}_$checkName.log"
    $checkArgs = @('--tool', $checkName, '--error-exitcode', '99', '--log-file', $logPath)
    if ($checkName -eq 'memcheck') { $checkArgs += @('--leak-check', 'full') }
    & $Sanitizer @checkArgs $Python $TestScript --instrumentation $checkName @testArgs
    $processCode = $LASTEXITCODE
    $logText = Get-Content -LiteralPath $logPath -Raw
    $summaryPattern = if ($checkName -eq 'racecheck') {
        'RACECHECK SUMMARY: 0 hazards displayed \(0 errors, 0 warnings\)'
    } else { 'ERROR SUMMARY: 0 errors' }
    $passed = ($processCode -eq 0) -and ($logText -match $summaryPattern)
    if ($checkName -eq 'memcheck') { $passed = $passed -and ($logText -match '0 bytes leaked in 0 allocations') }
    $checks += @{ tool=$checkName; exit_code=$processCode; passed=$passed; log=$logPath;
        log_sha256=(Get-FileHash -LiteralPath $logPath -Algorithm SHA256).Hash.ToLower() }
    if (-not $passed) { throw "CUDA $checkName did not pass; inspect $logPath" }
}
$libraryPath = if ($Dtype -eq 'float64') { 'build/fly_cuda64.dll' } else { 'build/fly_cuda_probe.dll' }
@{
    scope='Five-neuron native CUDA checks only; no full-graph validation'; test_script=$TestScript;
    library_sha256=(Get-FileHash -LiteralPath $libraryPath -Algorithm SHA256).Hash.ToLower();
    checks=$checks; passed=$true
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "reports/${reportPrefix}_sanitizers.json" -Encoding utf8

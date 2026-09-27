param([string]$Sanitizer='C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\compute-sanitizer\compute-sanitizer.exe')
$ErrorActionPreference='Stop'
$checks=@()
foreach ($checkName in @('memcheck','racecheck','initcheck','synccheck')) {
    $logPath="reports/photon_abi_$checkName.log"
    $checkArgs=@('--tool',$checkName,'--error-exitcode','99','--log-file',$logPath)
    if ($checkName -eq 'memcheck') { $checkArgs+=@('--leak-check','full') }
    & $Sanitizer @checkArgs .\build\photon_abi_probe.exe
    $processCode=$LASTEXITCODE
    $logText=Get-Content -LiteralPath $logPath -Raw
    $pattern=if($checkName -eq 'racecheck'){'RACECHECK SUMMARY: 0 hazards displayed \(0 errors, 0 warnings\)'}else{'ERROR SUMMARY: 0 errors'}
    $passed=($processCode -eq 0) -and ($logText -match $pattern)
    if($checkName -eq 'memcheck'){$passed=$passed -and ($logText -match '0 bytes leaked in 0 allocations')}
    if(-not $passed){throw "Failed $checkName; inspect $logPath"}
    $checks+=@{tool=$checkName;passed=$true;exit_code=$processCode;log_sha256=(Get-FileHash -LiteralPath $logPath -Algorithm SHA256).Hash.ToLower()}
    Write-Output "PASS $checkName"
}
@{passed=$true;scope='C ABI populations 1/3/33, 1001 microvilli each; nonzero neural feedback, save at tick 20, restore/replay to tick 30, corrupt metadata, invalid feedback and explicit reset; not full retina';checks=$checks;
  binary_sha256=(Get-FileHash -LiteralPath build/fly_photon.dll -Algorithm SHA256).Hash.ToLower();
  probe_sha256=(Get-FileHash -LiteralPath build/photon_abi_probe.exe -Algorithm SHA256).Hash.ToLower()
} | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 reports/photon_abi_sanitizers.json

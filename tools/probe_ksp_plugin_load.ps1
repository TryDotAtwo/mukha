param([int]$TimeoutSeconds = 150)
$ErrorActionPreference = 'Stop'
$kspRoot = 'D:\SteamLibrary\steamapps\common\Kerbal Space Program'
$exe = Join-Path $kspRoot 'KSP_x64.exe'
$log = Join-Path $kspRoot 'KSP.log'
$workspace = Split-Path -Parent $PSScriptRoot
$reportPath = Join-Path $workspace 'reports\ksp_plugin_load_probe.json'
$backupName = 'ksp_prelaunch_log_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '.log'
$backupPath = Join-Path $workspace ('data\reference\' + $backupName)
if (Get-Process KSP_x64 -ErrorAction SilentlyContinue) {
    throw 'KSP is already running; refusing to take ownership of that process'
}
if (!(Test-Path -LiteralPath $exe)) { throw 'KSP executable missing' }
if (Test-Path -LiteralPath $log) {
    Copy-Item -LiteralPath $log -Destination $backupPath
}
$started = Get-Date
$owned = Start-Process -FilePath $exe -WorkingDirectory $kspRoot -ArgumentList @('-batchmode','-nographics') -WindowStyle Hidden -PassThru
$observed = @()
$mainMenuReached = $false
$deadline = $started.AddSeconds($TimeoutSeconds)
try {
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        $owned.Refresh()
        if (Test-Path -LiteralPath $log) {
            $item = Get-Item -LiteralPath $log
            if ($item.LastWriteTime -ge $started) {
                $observed = @(Select-String -LiteralPath $log -Pattern 'kRPC','KRPC' | Select-Object -First 25 | ForEach-Object { $_.Line })
                $mainMenuReached = [bool](Select-String -LiteralPath $log -Pattern 'Scene Change : From LOADING to MAINMENU' -Quiet)
                if ($mainMenuReached) { break }
            }
        }
        if ($owned.HasExited) { break }
    }
} finally {
    $owned.Refresh()
    $forcedStop = $false
    if (!$owned.HasExited) {
        $null = $owned.CloseMainWindow()
        Start-Sleep -Seconds 5
        $owned.Refresh()
        if (!$owned.HasExited) {
            Stop-Process -Id $owned.Id -Force
            $forcedStop = $true
        }
    }
}
$owned.Refresh()
$report = [ordered]@{
    scope = 'Headless diagnostic game launch and kRPC log observation only; no flight scene, server or physics stepping'
    launch_arguments = @('-batchmode','-nographics')
    owned_process_id = $owned.Id
    started_utc = $started.ToUniversalTime().ToString('o')
    process_exited = $owned.HasExited
    forced_stop = $forcedStop
    krpc_log_lines = $observed
    krpc_log_lines_found = $observed.Count -gt 0
    main_menu_reached = $mainMenuReached
    previous_log_backup = if (Test-Path -LiteralPath $backupPath) { $backupPath } else { $null }
    previous_log_backed_up = Test-Path -LiteralPath $backupPath
}
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding utf8
$report | ConvertTo-Json -Depth 5

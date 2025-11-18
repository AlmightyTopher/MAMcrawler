# Setup Weekly Audiobook Batch Download Schedule
# This script creates a Windows Task Scheduler task to run the automated batch downloader

param(
    [string]$TaskName = "AudiobookWeeklyBatch",
    [string]$DayOfWeek = "Friday",
    [string]$Time = "02:00",
    [switch]$DryRun
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Audiobook Weekly Batch Scheduler Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get current directory
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Get-Location
}

Write-Host "Project Directory: $ScriptDir" -ForegroundColor Yellow
Write-Host ""

# Find Python executable in venv
$PythonExe = Join-Path $ScriptDir "venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Python venv not found at: $PythonExe" -ForegroundColor Red
    Write-Host "Please create a virtual environment first:" -ForegroundColor Yellow
    Write-Host "  python -m venv venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Found Python: $PythonExe" -ForegroundColor Green

# Check if batch script exists
$BatchScript = Join-Path $ScriptDir "audiobook_auto_batch.py"

if (-not (Test-Path $BatchScript)) {
    Write-Host "[ERROR] Batch script not found: $BatchScript" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Found batch script: $BatchScript" -ForegroundColor Green
Write-Host ""

# Prepare command
$Command = "`"$PythonExe`" `"$BatchScript`""

if ($DryRun) {
    $Command += " --dry-run"
    Write-Host "[INFO] Dry-run mode enabled" -ForegroundColor Yellow
}

Write-Host "Task Configuration:" -ForegroundColor Cyan
Write-Host "  Name:        $TaskName"
Write-Host "  Day:         $DayOfWeek"
Write-Host "  Time:        $Time"
Write-Host "  Command:     $Command"
Write-Host ""

# Check if task already exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($ExistingTask) {
    Write-Host "[WARNING] Task '$TaskName' already exists" -ForegroundColor Yellow
    $Confirm = Read-Host "Do you want to replace it? (y/n)"

    if ($Confirm -ne 'y') {
        Write-Host "[CANCELLED] Setup cancelled" -ForegroundColor Yellow
        exit 0
    }

    Write-Host "[INFO] Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create scheduled task
Write-Host ""
Write-Host "[CREATING] Setting up scheduled task..." -ForegroundColor Cyan

try {
    # Create action
    $Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$BatchScript`"" -WorkingDirectory $ScriptDir

    # Create trigger (weekly on specified day at specified time)
    $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $Time

    # Create settings
    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 4)

    # Create principal (run with highest privileges)
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

    # Register task
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "Automated weekly audiobook batch download" `
        -Force | Out-Null

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "[SUCCESS] Task created successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "  Name:     $TaskName"
    Write-Host "  Schedule: Every $DayOfWeek at $Time"
    Write-Host "  Script:   $BatchScript"
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Review config: audiobook_auto_config.json"
    Write-Host "  2. Test manually: python audiobook_auto_batch.py --dry-run"
    Write-Host "  3. View task:     Task Scheduler -> Task Scheduler Library"
    Write-Host "  4. Test run:      schtasks /Run /TN `"$TaskName`""
    Write-Host ""
    Write-Host "To modify the schedule, edit audiobook_auto_config.json" -ForegroundColor Yellow
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to create task: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Try running PowerShell as Administrator" -ForegroundColor Yellow
    exit 1
}

# Show task info
Write-Host "Task Information:" -ForegroundColor Cyan
Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State, Date, Author
Write-Host ""
Write-Host "To manually run the task now:" -ForegroundColor Yellow
Write-Host "  schtasks /Run /TN `"$TaskName`"" -ForegroundColor White
Write-Host ""
Write-Host "To disable the task:" -ForegroundColor Yellow
Write-Host "  Disable-ScheduledTask -TaskName `"$TaskName`"" -ForegroundColor White
Write-Host ""
Write-Host "To remove the task:" -ForegroundColor Yellow
Write-Host "  Unregister-ScheduledTask -TaskName `"$TaskName`" -Confirm:`$false" -ForegroundColor White
Write-Host ""

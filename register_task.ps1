$action = New-ScheduledTaskAction -Execute "C:\Users\dogma\Projects\MAMcrawler\start_mamcrawler.bat"
$trigger = New-ScheduledTaskTrigger -AtLogon
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0
Register-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -TaskName "MAMcrawlerAPI" -Description "Starts MAMcrawler API Server at logon" -Force
Write-Host "Task Registered Successfully"

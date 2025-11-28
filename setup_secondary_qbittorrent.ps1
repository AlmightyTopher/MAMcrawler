# Secondary qBittorrent Instance - Automated Setup Script
# Version: 1.0
# Last Updated: 2025-11-28
#
# This script automates the complete setup of a secondary qBittorrent instance
# for VPN-resilient failover support.
#
# Usage:
#   Right-click → Run with PowerShell
#   OR
#   powershell -ExecutionPolicy Bypass -File setup_secondary_qbittorrent.ps1

#Requires -RunAsAdministrator

# Configuration
$SecondaryRoot = "C:\qbittorrent_secondary"
$ProfileDir = "$SecondaryRoot\profile"
$DownloadsDir = "$SecondaryRoot\downloads"
$IncompleteDir = "$DownloadsDir\.incomplete"
$ConfigDir = "$ProfileDir\qBittorrent"
$ConfigFile = "$ConfigDir\qBittorrent.conf"
$BatchFile = "$SecondaryRoot\start_secondary.bat"
$ProjectRoot = "C:\Users\dogma\Projects\MAMcrawler"
$TemplateConfig = "$ProjectRoot\qbittorrent_secondary_config.ini"
$EnvFile = "$ProjectRoot\.env"

# qBittorrent installation path
$QBittorrentExe = "C:\Program Files (x86)\qBittorrent\qbittorrent.exe"
$QBittorrentExeAlt = "C:\Program Files\qBittorrent\qbittorrent.exe"

# Color functions
function Write-Success { param($Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }
function Write-Step { param($Message) Write-Host "`n==== $Message ====" -ForegroundColor Magenta }

# Banner
Clear-Host
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "     Secondary qBittorrent Instance - Automated Setup" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Info "This script will configure a local qBittorrent instance for VPN failover"
Write-Info "Installation location: $SecondaryRoot"
Write-Host ""

# Prompt for confirmation
$Confirm = Read-Host "Continue with setup? (Y/N)"
if ($Confirm -ne 'Y' -and $Confirm -ne 'y') {
    Write-Warning "Setup cancelled by user"
    exit 0
}

# Error counter
$ErrorCount = 0

# ============================================================
# Step 1: Verify Prerequisites
# ============================================================
Write-Step "Step 1: Verifying Prerequisites"

# Check if running as Administrator
$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $IsAdmin) {
    Write-Error "This script must be run as Administrator"
    Write-Info "Right-click the script and select 'Run as Administrator'"
    exit 1
}
Write-Success "Running as Administrator"

# Check qBittorrent installation
if (Test-Path $QBittorrentExe) {
    Write-Success "qBittorrent found: $QBittorrentExe"
    $QBExePath = $QBittorrentExe
} elseif (Test-Path $QBittorrentExeAlt) {
    Write-Success "qBittorrent found: $QBittorrentExeAlt"
    $QBExePath = $QBittorrentExeAlt
} else {
    Write-Error "qBittorrent not found at either:"
    Write-Error "  - $QBittorrentExe"
    Write-Error "  - $QBittorrentExeAlt"
    Write-Info "Please install qBittorrent first: https://www.qbittorrent.org/download.php"
    exit 1
}

# Check template config exists
if (-not (Test-Path $TemplateConfig)) {
    Write-Error "Template configuration not found: $TemplateConfig"
    Write-Info "Ensure you're running this script from the MAMcrawler project directory"
    exit 1
}
Write-Success "Template configuration found"

# Check .env file exists (for reference)
if (Test-Path $EnvFile) {
    Write-Success ".env file found (will use for credentials)"
} else {
    Write-Warning ".env file not found - you'll need to set credentials manually"
}

# ============================================================
# Step 2: Create Directory Structure
# ============================================================
Write-Step "Step 2: Creating Directory Structure"

$Directories = @(
    $SecondaryRoot,
    $ProfileDir,
    $DownloadsDir,
    $IncompleteDir,
    $ConfigDir
)

foreach ($Dir in $Directories) {
    try {
        if (-not (Test-Path $Dir)) {
            New-Item -Path $Dir -ItemType Directory -Force | Out-Null
            Write-Success "Created: $Dir"
        } else {
            Write-Info "Already exists: $Dir"
        }
    } catch {
        Write-Error "Failed to create directory: $Dir"
        Write-Error $_.Exception.Message
        $ErrorCount++
    }
}

# ============================================================
# Step 3: Copy and Configure qBittorrent.conf
# ============================================================
Write-Step "Step 3: Creating Configuration File"

try {
    # Copy template to destination
    Copy-Item -Path $TemplateConfig -Destination $ConfigFile -Force
    Write-Success "Configuration file created: $ConfigFile"

    # Read and modify configuration
    $ConfigContent = Get-Content $ConfigFile -Raw

    # Update paths to use actual Windows username
    $Username = $env:USERNAME
    $ConfigContent = $ConfigContent -replace '\{YourUsername\}', $Username

    # Save modified configuration
    Set-Content -Path $ConfigFile -Value $ConfigContent -Force
    Write-Success "Configuration updated with username: $Username"

} catch {
    Write-Error "Failed to create configuration file"
    Write-Error $_.Exception.Message
    $ErrorCount++
}

# ============================================================
# Step 4: Create Startup Batch File
# ============================================================
Write-Step "Step 4: Creating Startup Batch File"

$BatchContent = @"
@echo off
REM Secondary qBittorrent Instance Startup Script
REM Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

echo ================================================================
echo     Starting qBittorrent Secondary Instance
echo ================================================================
echo.
echo WebUI will be available at: http://localhost:52095
echo Profile: $ProfileDir
echo Downloads: $DownloadsDir
echo.
echo Press Ctrl+C to stop the secondary instance
echo ================================================================
echo.

REM Set profile path via environment variable
set APPDATA=$ProfileDir

REM Launch qBittorrent with custom profile
"$QBExePath" --webui-port=52095 --profile=$ProfileDir

echo.
echo Secondary instance stopped
pause
"@

try {
    Set-Content -Path $BatchFile -Value $BatchContent -Force
    Write-Success "Startup batch file created: $BatchFile"
} catch {
    Write-Error "Failed to create batch file"
    Write-Error $_.Exception.Message
    $ErrorCount++
}

# ============================================================
# Step 5: Create Desktop Shortcut
# ============================================================
Write-Step "Step 5: Creating Desktop Shortcut"

try {
    $WshShell = New-Object -ComObject WScript.Shell
    $ShortcutPath = "$env:USERPROFILE\Desktop\qBittorrent Secondary.lnk"
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $BatchFile
    $Shortcut.WorkingDirectory = $SecondaryRoot
    $Shortcut.Description = "Start qBittorrent Secondary Instance (localhost:52095)"
    $Shortcut.IconLocation = "$QBExePath,0"
    $Shortcut.Save()
    Write-Success "Desktop shortcut created: $ShortcutPath"
} catch {
    Write-Warning "Failed to create desktop shortcut"
    Write-Info "You can manually create a shortcut to: $BatchFile"
}

# ============================================================
# Step 6: Configure Firewall Rules
# ============================================================
Write-Step "Step 6: Configuring Firewall Rules"

try {
    # Check if firewall rules already exist
    $ExistingRule = Get-NetFirewallRule -DisplayName "qBittorrent Secondary WebUI" -ErrorAction SilentlyContinue

    if ($ExistingRule) {
        Write-Info "Firewall rule already exists (skipping)"
    } else {
        # Allow localhost traffic (usually not needed but doesn't hurt)
        New-NetFirewallRule -DisplayName "qBittorrent Secondary WebUI" `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort 52095 `
            -LocalAddress 127.0.0.1 `
            -Action Allow `
            -Profile Any `
            -ErrorAction Stop | Out-Null
        Write-Success "Firewall rule created for localhost:52095"
    }

    # BitTorrent ports
    $ExistingBTRule = Get-NetFirewallRule -DisplayName "qBittorrent Secondary BitTorrent" -ErrorAction SilentlyContinue

    if ($ExistingBTRule) {
        Write-Info "BitTorrent firewall rule already exists (skipping)"
    } else {
        New-NetFirewallRule -DisplayName "qBittorrent Secondary BitTorrent" `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort 6881-6920 `
            -Action Allow `
            -Profile Any `
            -ErrorAction Stop | Out-Null
        Write-Success "Firewall rule created for BitTorrent ports (6881-6920)"
    }

} catch {
    Write-Warning "Failed to create firewall rules (may already exist or require manual setup)"
    Write-Info "Localhost traffic is usually allowed by default"
}

# ============================================================
# Step 7: Update .env File
# ============================================================
Write-Step "Step 7: Updating .env File"

if (Test-Path $EnvFile) {
    try {
        $EnvContent = Get-Content $EnvFile -Raw

        # Check if QBITTORRENT_SECONDARY_URL already exists
        if ($EnvContent -match 'QBITTORRENT_SECONDARY_URL') {
            Write-Info "QBITTORRENT_SECONDARY_URL already configured in .env"
        } else {
            # Add secondary URL to .env
            $EnvContent += "`n`n# Secondary qBittorrent Instance (Local Fallback)`nQBITTORRENT_SECONDARY_URL=http://localhost:52095/`n"
            Set-Content -Path $EnvFile -Value $EnvContent -Force
            Write-Success "Added QBITTORRENT_SECONDARY_URL to .env file"
        }

    } catch {
        Write-Warning "Failed to update .env file"
        Write-Info "Manually add: QBITTORRENT_SECONDARY_URL=http://localhost:52095/"
    }
} else {
    Write-Warning ".env file not found"
    Write-Info "Create .env file and add: QBITTORRENT_SECONDARY_URL=http://localhost:52095/"
}

# ============================================================
# Step 8: Test Directory Permissions
# ============================================================
Write-Step "Step 8: Testing Directory Permissions"

try {
    # Test write access to profile directory
    $TestFile = "$ProfileDir\test_permissions.tmp"
    "test" | Out-File -FilePath $TestFile -Force
    Remove-Item $TestFile -Force
    Write-Success "Profile directory writable"

    # Test write access to downloads directory
    $TestFile = "$DownloadsDir\test_permissions.tmp"
    "test" | Out-File -FilePath $TestFile -Force
    Remove-Item $TestFile -Force
    Write-Success "Downloads directory writable"

} catch {
    Write-Error "Permission test failed"
    Write-Error $_.Exception.Message
    Write-Info "Try running the setup script as Administrator"
    $ErrorCount++
}

# ============================================================
# Step 9: Verify Configuration
# ============================================================
Write-Step "Step 9: Verifying Configuration"

$VerificationChecks = @{
    "Secondary root directory" = (Test-Path $SecondaryRoot)
    "Profile directory" = (Test-Path $ProfileDir)
    "Downloads directory" = (Test-Path $DownloadsDir)
    "Configuration file" = (Test-Path $ConfigFile)
    "Startup batch file" = (Test-Path $BatchFile)
    "qBittorrent executable" = (Test-Path $QBExePath)
}

$AllPassed = $true
foreach ($Check in $VerificationChecks.GetEnumerator()) {
    if ($Check.Value) {
        Write-Success "$($Check.Key): OK"
    } else {
        Write-Error "$($Check.Key): FAILED"
        $AllPassed = $false
        $ErrorCount++
    }
}

# ============================================================
# Summary
# ============================================================
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "     Setup Complete!" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

if ($ErrorCount -eq 0 -and $AllPassed) {
    Write-Success "Secondary qBittorrent instance configured successfully!"
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Start secondary instance:" -ForegroundColor White
    Write-Host "     - Double-click: $BatchFile" -ForegroundColor Gray
    Write-Host "     - OR use Desktop shortcut: 'qBittorrent Secondary'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Configure WebUI password (FIRST LAUNCH ONLY):" -ForegroundColor White
    Write-Host "     - Open browser: http://localhost:52095" -ForegroundColor Gray
    Write-Host "     - Login: admin / adminadmin (default)" -ForegroundColor Gray
    Write-Host "     - Tools → Options → Web UI" -ForegroundColor Gray
    Write-Host "     - Change username to: TopherGutbrod" -ForegroundColor Gray
    Write-Host "     - Change password to match primary (from .env)" -ForegroundColor Gray
    Write-Host "     - Click Save" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  3. Verify health check:" -ForegroundColor White
    Write-Host "     cd $ProjectRoot" -ForegroundColor Gray
    Write-Host "     python monitor_qbittorrent_health.py" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  4. Test failover:" -ForegroundColor White
    Write-Host "     - Disconnect VPN" -ForegroundColor Gray
    Write-Host "     - Run: python execute_full_workflow.py" -ForegroundColor Gray
    Write-Host "     - Verify workflow uses secondary instance (check logs)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Installation Details:" -ForegroundColor Yellow
    Write-Host "  Location:    $SecondaryRoot" -ForegroundColor Gray
    Write-Host "  Profile:     $ProfileDir" -ForegroundColor Gray
    Write-Host "  Downloads:   $DownloadsDir" -ForegroundColor Gray
    Write-Host "  WebUI:       http://localhost:52095" -ForegroundColor Gray
    Write-Host "  Startup:     $BatchFile" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Documentation:" -ForegroundColor Yellow
    Write-Host "  Full setup guide:      SECONDARY_QBITTORRENT_SETUP.md" -ForegroundColor Gray
    Write-Host "  Deployment checklist:  SECONDARY_DEPLOYMENT_CHECKLIST.md" -ForegroundColor Gray
    Write-Host "  Troubleshooting:       See 'Common Issues' in setup guide" -ForegroundColor Gray
    Write-Host ""

} else {
    Write-Error "Setup completed with $ErrorCount error(s)"
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Verify you're running as Administrator" -ForegroundColor Gray
    Write-Host "  2. Check disk space on C:\ drive" -ForegroundColor Gray
    Write-Host "  3. Review error messages above" -ForegroundColor Gray
    Write-Host "  4. Consult SECONDARY_QBITTORRENT_SETUP.md for detailed help" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

# Prompt to start secondary instance now
Write-Host ""
$StartNow = Read-Host "Would you like to start the secondary instance now? (Y/N)"
if ($StartNow -eq 'Y' -or $StartNow -eq 'y') {
    Write-Info "Starting secondary instance..."
    Write-Info "Browser will open to http://localhost:52095 in 5 seconds..."
    Start-Process -FilePath $BatchFile
    Start-Sleep -Seconds 5
    Start-Process "http://localhost:52095"
    Write-Success "Secondary instance started!"
    Write-Info "Login with default credentials (admin/adminadmin) and change password immediately"
} else {
    Write-Info "Setup complete. Start manually when ready using the Desktop shortcut or batch file."
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Thank you for using MAMcrawler!" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

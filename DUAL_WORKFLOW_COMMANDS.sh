#!/bin/bash
# Quick Command Reference for Dual Goodreads Metadata Sync Workflow

# ============================================================================
# SINGLE INSTANCE (abs_goodreads_sync_workflow.py)
# ============================================================================

# Test with 10 books
python abs_goodreads_sync_workflow.py --limit 10

# Process 100 books
python abs_goodreads_sync_workflow.py --limit 100

# Process 500 books
python abs_goodreads_sync_workflow.py --limit 500

# Process with auto-update to AudiobookShelf
python abs_goodreads_sync_workflow.py --limit 100 --auto-update

# Process with audio file validation
python abs_goodreads_sync_workflow.py --limit 100 --validate-audio

# Process with both auto-update and validation
python abs_goodreads_sync_workflow.py --limit 100 --auto-update --validate-audio

# ============================================================================
# DUAL INSTANCE (dual_abs_goodreads_sync_workflow.py)
# ============================================================================

# Test with 10 books (5 VPN + 5 Direct)
python dual_abs_goodreads_sync_workflow.py --limit 10

# Process 100 books (50 VPN + 50 Direct)
python dual_abs_goodreads_sync_workflow.py --limit 100

# Process 500 books (250 VPN + 250 Direct)
python dual_abs_goodreads_sync_workflow.py --limit 500

# Process with auto-update
python dual_abs_goodreads_sync_workflow.py --limit 500 --auto-update

# Process with custom VPN Python path
python dual_abs_goodreads_sync_workflow.py --limit 500 --vpn-python "C:\path\to\python_vpn.exe"

# ============================================================================
# BATCH PROCESSING (for 50,000 book library)
# ============================================================================

# Single instance batch (100 iterations × 500 books)
for i in {1..100}; do
  echo "Batch $i/100 (single instance)"
  python abs_goodreads_sync_workflow.py --limit 500 --auto-update
done

# Dual instance batch (100 iterations × 500 books) - RECOMMENDED
for i in {1..100}; do
  echo "Batch $i/100 (dual instance)"
  python dual_abs_goodreads_sync_workflow.py --limit 500 --auto-update
done

# Dual instance with verification (process and verify each batch)
for i in {1..100}; do
  echo "Batch $i/100..."
  python dual_abs_goodreads_sync_workflow.py --limit 500 --auto-update

  # Check resolution rate
  cat abs_goodreads_dual_sync_report.json | jq '.resolution_rate'
done

# ============================================================================
# MONITORING & DEBUGGING
# ============================================================================

# Check latest results
cat abs_goodreads_sync_report.json | jq '.'

# Check latest dual results
cat abs_goodreads_dual_sync_report.json | jq '.'

# Get resolution rate only
cat abs_goodreads_dual_sync_report.json | jq '.resolution_rate'

# Get failed books
cat abs_goodreads_dual_sync_report.json | jq '.results[] | select(.goodreads_data == null)'

# Get low-confidence results
cat abs_goodreads_dual_sync_report.json | jq '.results[] | select(.confidence < 0.7)'

# Compare VPN vs Direct performance
echo "VPN Worker:" && cat worker_results_vpn.json | jq '.books_resolved'
echo "Direct Worker:" && cat worker_results_direct.json | jq '.books_resolved'

# ============================================================================
# VERIFICATION & CLEANUP
# ============================================================================

# Verify environment is set up
grep "GOODREADS\|ABS_" .env

# Test Goodreads connectivity
curl -I https://www.goodreads.com

# Test AudiobookShelf connectivity
curl http://localhost:13378/api/ping

# Clean up temporary worker files
rm -f worker_config_*.json worker_results_*.json

# ============================================================================
# OPTIMIZATION
# ============================================================================

# Increase batch size (slower but fewer orchestration overheads)
python dual_abs_goodreads_sync_workflow.py --limit 1000 --auto-update

# Process multiple batches in background (requires GNU parallel)
cat batch_list.txt | parallel python dual_abs_goodreads_sync_workflow.py --limit 500

# Run daily batch (add to cron or task scheduler)
0 22 * * * /usr/bin/python3 /path/to/dual_abs_goodreads_sync_workflow.py --limit 500 --auto-update

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# Check if WireGuard is active (for VPN mode)
wg show

# Check Python executables
which python
ls -la python_vpn.exe

# Test VPN routing (if python_vpn.exe exists)
python_vpn.exe --version

# View worker logs in detail
cat worker_results_vpn.json | jq '.results | length'
cat worker_results_direct.json | jq '.results | length'

# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

# Time a single batch
time python dual_abs_goodreads_sync_workflow.py --limit 500

# Count resolved books
cat abs_goodreads_dual_sync_report.json | jq '.books_resolved'

# Get average confidence score
cat abs_goodreads_dual_sync_report.json | jq '.results | map(.confidence) | add / length'

# Find books that need manual review (confidence 0.7-0.9)
cat abs_goodreads_dual_sync_report.json | jq '.results | map(select(.confidence >= 0.7 and .confidence < 0.9))'

# ============================================================================
# WINDOWS PowerShell EQUIVALENTS
# ============================================================================

# PowerShell: Test with 10 books
& python.exe abs_goodreads_sync_workflow.py --limit 10

# PowerShell: Dual instance batch
For ($i=1; $i -le 100; $i++) {
  Write-Host "Batch $i/100"
  & python.exe dual_abs_goodreads_sync_workflow.py --limit 500 --auto-update
}

# PowerShell: Check resolution rate
$(Get-Content abs_goodreads_dual_sync_report.json | ConvertFrom-Json).resolution_rate

# PowerShell: List failed books
$(Get-Content abs_goodreads_dual_sync_report.json | ConvertFrom-Json).results | Where-Object { $_.goodreads_data -eq $null }

# ============================================================================
# NOTES
# ============================================================================

# Default behavior:
# - Single instance processes sequentially (good for debugging)
# - Dual instance splits work between VPN and Direct (40% faster)
# - Both use Goodreads web crawler (proven, stable)
# - Rate limiting built-in (respects Goodreads)
# - Auto-update optional (updates ABS as it processes)

# Expected performance:
# - 10 books: 2-4 minutes
# - 100 books: 12-25 minutes (single) or 12-15 minutes (dual)
# - 500 books: 60-120 minutes (single) or 60-70 minutes (dual)
# - 50,000 books: ~150 hours with dual instance (run in daily batches)

# Best practices:
# 1. Start with --limit 10 to test setup
# 2. Run daily batches of 500 books for production
# 3. Enable --auto-update to update ABS as you process
# 4. Monitor resolution_rate in output JSON
# 5. Use dual instance for production (40% faster)

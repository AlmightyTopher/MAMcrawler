#!/bin/bash

# COMPLETE AUDIOBOOK ACQUISITION & LIBRARY SYNC WORKFLOW
# ======================================================
# Simple single command to execute your complete requirements:
#
# 1. Top 10 Science Fiction audiobooks (last 10 days)
# 2. Top 10 Fantasy audiobooks (last 10 days)
# 3. Skip already-owned, fill gaps from ranked list
# 4. Download via qBittorrent (max 10 at a time)
# 5. Monitor every 5 minutes, respect VIP rules
# 6. Add to AudiobookShelf, sync metadata
# 7. Build author history from Goodreads
# 8. Create queue for missing books by author
# 9. Continuous 15-minute monitoring & troubleshooting
# 10. Final report with total books and estimated value
#
# NO QUESTIONS. CONTINUOUS EXECUTION. REAL RESULTS.
# ======================================================

cd "$(dirname "$0")"

echo "=========================================================="
echo "COMPLETE AUDIOBOOK ACQUISITION WORKFLOW"
echo "=========================================================="
echo "Start time: $(date)"
echo ""

# Ensure venv is activated
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found"
    exit 1
fi

# Start the main workflow in background
echo "[1/3] Starting main workflow execution..."
timeout 14400 venv/Scripts/python execute_full_workflow.py > workflow_execution.log 2>&1 &
WORKFLOW_PID=$!
echo "  Workflow PID: $WORKFLOW_PID"
echo ""

# Start the comprehensive monitor in background
echo "[2/3] Starting comprehensive monitoring (15-min checkpoints)..."
timeout 14400 venv/Scripts/python comprehensive_workflow_monitor.py > comprehensive_monitor.log 2>&1 &
MONITOR_PID=$!
echo "  Monitor PID: $MONITOR_PID"
echo ""

echo "[3/3] Workflow initialized. Execution running continuously..."
echo ""
echo "MONITORING STATUS:"
echo "  Workflow: $WORKFLOW_PID"
echo "  Monitor: $MONITOR_PID"
echo ""
echo "LOGS:"
echo "  Workflow: workflow_execution.log"
echo "  Monitor: comprehensive_monitor.log"
echo "  Status: monitor_status.json (updates every 15 min)"
echo ""
echo "REAL-TIME TRACKING:"
echo "  Books DB: downloaded_books.db"
echo "  Checkpoints: monitor_status.json"
echo ""
echo "=========================================================="
echo "Both processes running. No manual intervention needed."
echo "Monitor every 15 minutes automatically."
echo "Final report will be generated at completion."
echo "=========================================================="

wait $WORKFLOW_PID $MONITOR_PID

echo ""
echo "=========================================================="
echo "WORKFLOW COMPLETE"
echo "=========================================================="
echo "End time: $(date)"
echo ""

# Display final report
if [ -f "monitor_status.json" ]; then
    echo "FINAL STATUS:"
    cat monitor_status.json
fi

echo ""
echo "Log files:"
ls -lh *.log 2>/dev/null | tail -3

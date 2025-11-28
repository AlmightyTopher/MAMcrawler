#!/usr/bin/env python3
"""
CHECKPOINT TIMER - Displays countdown for next checkpoint
Generates a file that shows current checkpoint status and countdown
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

def get_checkpoint_info():
    """Calculate current checkpoint and next checkpoint times"""

    # Workflow started at 02:03:55 UTC
    start_time = datetime(2025, 11, 27, 2, 3, 55)
    checkpoint_interval = 900  # 15 minutes in seconds

    now = datetime.utcnow()

    # Calculate elapsed time
    elapsed = (now - start_time).total_seconds()

    # Calculate current checkpoint number
    current_checkpoint = int(elapsed // checkpoint_interval) + 1

    # Calculate next checkpoint time
    next_checkpoint_seconds = current_checkpoint * checkpoint_interval
    next_checkpoint_time = start_time + timedelta(seconds=next_checkpoint_seconds)

    # Calculate time remaining until next checkpoint
    time_remaining = (next_checkpoint_time - now).total_seconds()

    if time_remaining < 0:
        time_remaining = 0
        current_checkpoint += 1
        next_checkpoint_time = start_time + timedelta(seconds=current_checkpoint * checkpoint_interval)
        time_remaining = (next_checkpoint_time - now).total_seconds()

    # Format countdown
    minutes = int(time_remaining // 60)
    seconds = int(time_remaining % 60)
    countdown_str = f"{minutes:02d}:{seconds:02d}"

    return {
        'current_checkpoint': current_checkpoint,
        'next_checkpoint_time': next_checkpoint_time.strftime('%H:%M:%S UTC'),
        'countdown': countdown_str,
        'time_remaining_seconds': time_remaining,
        'elapsed_total_seconds': elapsed,
        'elapsed_minutes': elapsed / 60,
        'current_time': now.strftime('%H:%M:%S UTC')
    }

def display_timer():
    """Display the checkpoint timer"""
    info = get_checkpoint_info()

    timer_display = f"""
================================================================================
CHECKPOINT TIMER - NEXT REFRESH IN: {info['countdown']}
================================================================================
Current Time:           {info['current_time']}
Current Checkpoint:     #{info['current_checkpoint']}
Next Checkpoint:        {info['next_checkpoint_time']}
Time Until Refresh:     {info['countdown']} ({int(info['time_remaining_seconds'])} seconds)
Elapsed Since Start:    {info['elapsed_minutes']:.1f} minutes
================================================================================
"""
    return timer_display

def save_timer_file():
    """Save timer info to file for display"""
    info = get_checkpoint_info()

    timer_content = f"""{info['countdown']}|{info['current_checkpoint']}|{info['next_checkpoint_time']}|{int(info['time_remaining_seconds'])}"""

    with open('checkpoint_timer.txt', 'w') as f:
        f.write(timer_content)

if __name__ == '__main__':
    print(display_timer())
    save_timer_file()
    print("Timer saved to checkpoint_timer.txt")

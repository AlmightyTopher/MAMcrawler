[STATE REPORT]
Objective:
Integrate "mam-exporter" functionality, ensure robust service management, and provide a Real-time UI Dashboard.

High-Level Task Understanding (your mental model of the task):
The user wants a self-healing, intelligent audiobook crawler with a modern "Command Center" interface.
1.  **Intelligence**: Pacing based on real-time MAM ratio.
2.  **Robustness**: Auto-start dependent services (ABS, qBit, Prowlarr).
3.  **Visibility**: A web-based UI to monitor stats, logs, and control the crawler.
4.  **Self-Healing**: Automatically detect and fix qBittorrent issues (stalling, binding).
5.  **Aesthetics**: "Rich Aesthetics" with animated terminal logs.

Reasoning History (why decisions were made):
-   **UI Stack**: Chosen Vue.js 3 (CDN) + Tailwind CSS (CDN) + FastAPI. This avoids complex Node.js build steps (user has old Node version) while delivering the requested "Rich Aesthetics" (Glassmorphism, Dark Mode).
-   **Backend**: `api_server.py` acts as the bridge, serving the HTML and exposing endpoints that run the `master_audiobook_manager.py` script as a subprocess.
-   **Log Parsing**: The API reads the latest log file to stream updates to the UI, ensuring the UI always shows the truth without complex websocket setups.
-   **Port Change**: Port 8000 was in use, switched to 8081.
-   **qBittorrent Fix**: The API server wasn't loading `.env`, so it defaulted to port 8080 instead of the configured 52095. Added `load_dotenv()` to fix this.
-   **Stalled Torrents Fix**: qBittorrent was bound to a specific network interface (`iftype53_32768`) that wasn't working. Reset it to bind to ALL interfaces, which fixed the connectivity. Torrents moved from `stalledDL` (0%) to `stalledUP` (100%).
-   **Automated Healing**: Created `QBitHealer` class to encapsulate the diagnostic logic (reset binding, re-announce trackers) and integrated it into `QBittorrentMonitor`. Now, if a torrent stalls twice, the system automatically runs the healer.
-   **Log Animation**: Implemented a "Typewriter" effect in `dashboard.html` with a translation layer to convert raw logs into human-readable text.
-   **Cache Busting**: Added `Cache-Control` headers to `api_server.py` to prevent the browser from serving stale versions of the dashboard.
-   **Translation Updates**: Added more patterns to `dashboard.html` to cover qBittorrent logs that were appearing as raw text.
-   **Log Parsing Fix**: Fixed a critical bug in `api_server.py` where 3-part log lines (Time-Level-Message) were being parsed incorrectly, causing the message to be empty and the level to contain the message text. This fixed the "unreadable logs" and "no typing animation" issue.

Progress Summary:
-   **MAM Stats**: Implemented & Verified.
-   **Service Manager**: Implemented & Verified.
-   **UI Dashboard**: Created `dashboard.html` and `api_server.py`.
-   **Server Status**: API Server is currently RUNNING at `http://localhost:8081`.
-   **Troubleshooting**:
    -   Fixed qBittorrent status detection in the UI.
    -   Fixed "Stalled" torrents by resetting network binding.
    -   Verified Tracker Status is now `2` (Working).
    -   Fixed Log Parsing logic in backend.
-   **Automation**: Implemented `QBitHealer` and integrated it into the monitor loop.
-   **UX**: Updated System Logs to be animated and human-readable, with cache busting to ensure updates apply.

Current Step:
The system is fully operational. The UI now features the requested animated logs with expanded translations and cache prevention.

Next Step:
1.  Inform the user about the fix (log parsing logic + translations).
2.  Wait for user feedback.

Active Constraints and Assumptions:
-   **OS**: Windows.
-   **UI Port**: 8081.
-   **Browser**: User needs to open `http://localhost:8081`.

Important Insights Discovered:
-   **Env Loading**: Always ensure `load_dotenv()` is called in entry points (`api_server.py`) to pick up configuration.
-   **qBit Binding**: Specific interface binding can cause connectivity issues if the interface changes (e.g., VPN reconnect). Binding to "Any" is safer for automation.
-   **Browser Caching**: FastAPI `FileResponse` needs explicit headers to prevent caching during development/iteration.
-   **Log Parsing**: Always verify log format (3 parts vs 4 parts) when parsing text logs.

Pending Tasks:
-   None. System is fully operational.

Relevant Data / File Locations:
-   `dashboard.html`: The Frontend.
-   `api_server.py`: The Backend.
-   `master_audiobook_manager.py`: The Core Logic.
-   `mamcrawler/qbit_healer.py`: The new self-healing module.

Conversation or Context Needed for Continuity:
-   User asked for "Full code" and "Rich Aesthetics".
-   User provided specific paths for services.
-   User asked for "general troubleshooting diagnosis... automatically run this".
-   User asked for "animated... terminal-style" logs.
-   User reported "jumped back to old style" issue.
-   User reported "logs not readable" issue.

Notes:
The system is now a complete "Product" with a backend logic layer, a frontend presentation layer, and an automated maintenance layer.
[/STATE REPORT]

<objective>
Build a real-time status page for the MAMcrawler system that provides users with immediate visibility into the crawling operations, system health, and current activities. This page will serve as a monitoring dashboard for users to track the progress and status of their audiobook crawling and downloading operations.

The status page should enable users to:
- View real-time crawler progress and statistics
- Monitor system resource usage
- Track download queue status and speeds
- View recent activity logs and errors
- Access quick system controls
- Receive alerts for important events

This will be the go-to page for users wanting to see what's happening with their MAMcrawler system at any given moment.
</objective>

<context>
This is for the MAMcrawler project users who need to monitor the system's operation in real-time. The status page should provide a clear, at-a-glance view of all system activities without requiring deep technical knowledge.

The page needs to integrate with the existing MAMcrawler components:
- Crawler state and progress tracking
- qBittorrent download status
- System resource monitoring
- Log aggregation and filtering
- Error detection and alerting
- Performance metrics and trends

It should be lightweight, fast-loading, and provide real-time updates without overwhelming the user.
</context>

<requirements>
Create a real-time status monitoring page with the following features:

1. **System Overview**
   - Overall system status (running, paused, error)
   - Uptime and last activity timestamp
   - Quick action buttons (start/stop crawler, clear logs)

2. **Crawler Status**
   - Current crawling progress and statistics
   - Active sources being crawled
   - Books discovered, processed, and downloaded
   - Crawler speed and efficiency metrics

3. **Download Monitoring**
   - Active downloads with progress bars
   - Download speeds and ETA calculations
   - Queue status and pending downloads
   - Completed downloads summary

4. **System Resources**
   - CPU, memory, and disk usage
   - Network activity and bandwidth usage
   - Database connection status
   - VPN/proxy status indicators

5. **Activity Feed**
   - Real-time log stream with filtering
   - Error alerts and warnings
   - Recent successful operations
   - Configurable log levels and categories

6. **Performance Charts**
   - Historical performance trends
   - Download speed over time
   - System resource usage graphs
   - Error rate monitoring

Implement auto-refresh capabilities and push notifications for critical events.
</requirements>

<implementation>
**Technology Stack:**
- HTML5 with real-time dashboard layout
- CSS3 with status-specific styling (charts, indicators, alerts)
- JavaScript with real-time updates (WebSocket/Server-Sent Events)
- Canvas or SVG for performance charts
- Progressive enhancement for older browsers

**Real-time Architecture:**
- WebSocket connection for live updates
- Server-Sent Events as fallback
- Polling with exponential backoff for reliability
- Push notifications for critical alerts
- Background sync for offline status viewing

**Status Indicators:**
- Color-coded status badges (green/yellow/red)
- Animated progress indicators
- Alert badges for errors and warnings
- Loading spinners for data fetching
- Connection status indicators

**Performance Optimizations:**
- Efficient data structures for real-time updates
- Minimal DOM manipulation
- Lazy loading of historical data
- Compression for large log streams
- Caching strategies for static assets

**User Experience:**
- Auto-refresh with manual refresh option
- Configurable update intervals
- Alert sound toggles
- Dark/light theme support
- Mobile-responsive design
</implementation>

<output>
Create the following files in the `frontend/` directory:

- `./frontend/status.html` - Main status page
- `./frontend/css/status.css` - Status-specific styling and animations
- `./frontend/js/status.js` - Main status logic and real-time updates
- `./frontend/js/components/status/` - Status components:
  - `system-overview.js` - System status summary
  - `crawler-monitor.js` - Crawler progress and stats
  - `download-tracker.js` - Download progress monitoring
  - `resource-monitor.js` - System resource displays
  - `activity-feed.js` - Real-time log streaming
  - `performance-charts.js` - Charts and graphs
- `./frontend/js/services/status/` - Status service modules:
  - `realtime-service.js` - WebSocket/real-time communication
  - `metrics-service.js` - System metrics API
  - `logs-service.js` - Log streaming and filtering
- `./frontend/js/utils/` - Utility functions:
  - `chart-utils.js` - Chart rendering utilities
  - `time-utils.js` - Time formatting and calculations
  - `status-utils.js` - Status parsing and formatting

Update navigation in main dashboard to include status page link.
</output>

<verification>
Before declaring complete, verify:

1. Status page loads quickly and displays current system state
2. Real-time updates work correctly via WebSocket
3. All status indicators show accurate information
4. Performance charts render correctly with historical data
5. Activity feed streams logs in real-time
6. Error alerts and notifications work properly
7. Interface remains responsive during high update frequency
8. Mobile layout works correctly
9. Auto-refresh and manual refresh both function
10. Integration with MAMcrawler backend provides accurate data

Test with active MAMcrawler operations to ensure real-time accuracy.
</verification>

<success_criteria>
- Real-time, accurate display of all MAMcrawler system status
- Intuitive dashboard layout with clear status indicators
- Performance charts and historical data visualization
- Real-time activity feed with filtering capabilities
- Responsive design working on all devices
- Reliable real-time updates with fallback mechanisms
- Alert system for critical events and errors
- Clean, maintainable code with proper error handling
- Documentation for status page features and API integration
</success_criteria>
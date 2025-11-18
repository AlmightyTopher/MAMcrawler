<objective>
Build a comprehensive dashboard UI for the MAMcrawler audiobook management system that works in a browser. This dashboard will allow users to view, manage, and monitor their audiobook downloads and collection.

The dashboard should provide an intuitive interface for users to:
- View their complete audiobook library with rich metadata
- Monitor active downloads and their progress
- See system status and crawler activity
- Access quick actions for common tasks
- Visualize collection statistics and trends

This will serve as the main control center for the MAMcrawler system, giving users full visibility and control over their audiobook ecosystem.
</objective>

<context>
This is for the MAMcrawler project, a Python-based system for crawling and managing audiobooks from MyAnonamouse. The dashboard will be the primary user interface for interacting with the audiobook collection and download management features.

The UI should integrate with the existing Python backend scripts and data structures. Key data sources include:
- Audiobook metadata from various sources (MAM, Goodreads, Audiobookshelf)
- Download status from qBittorrent integration
- Crawler state and logs
- Series and collection data

The dashboard should be responsive and work well on desktop and mobile browsers.
</context>

<requirements>
Create a modern, responsive web dashboard with the following features:

1. **Library Overview**
   - Grid/list view of all audiobooks with cover images
   - Search and filter capabilities (by author, series, genre, status)
   - Sort options (title, author, date added, file size)
   - Pagination for large collections

2. **Download Management**
   - Active downloads table with progress bars
   - Download speed and ETA displays
   - Pause/resume/cancel controls
   - Download queue management

3. **System Status Panel**
   - Crawler status (running, paused, error)
   - qBittorrent connection status
   - Disk space usage
   - Recent activity log

4. **Statistics Dashboard**
   - Total books, downloads, file sizes
   - Genre distribution charts
   - Download activity over time
   - Series completion status

5. **Quick Actions**
   - Start/stop crawler
   - Refresh library
   - Export collection data
   - Access admin settings

Use modern web technologies (HTML5, CSS3, JavaScript) with a clean, professional design. Include proper error handling and loading states.
</requirements>

<implementation>
**Technology Stack:**
- HTML5 for structure
- CSS3 with Flexbox/Grid for responsive layout
- Vanilla JavaScript (ES6+) for functionality
- No external frameworks to keep it lightweight
- Local storage for user preferences
- Fetch API for backend communication

**Design Principles:**
- Clean, modern interface with dark/light theme options
- Responsive design that works on all screen sizes
- Fast loading with progressive enhancement
- Accessible with proper ARIA labels and keyboard navigation
- Consistent styling and interaction patterns

**Backend Integration:**
- RESTful API endpoints for data retrieval
- WebSocket or polling for real-time updates
- JSON data exchange format
- Error handling for network issues

**Performance Considerations:**
- Lazy loading for large lists
- Efficient DOM manipulation
- Minimal re-renders
- Caching strategies for static data
</implementation>

<output>
Create the following files in a new `frontend/` directory:

- `./frontend/index.html` - Main dashboard HTML structure
- `./frontend/css/styles.css` - Complete styling with responsive design
- `./frontend/js/dashboard.js` - Main dashboard logic and API integration
- `./frontend/js/components/` - Modular component files:
  - `library-view.js` - Library display and management
  - `download-manager.js` - Download controls and progress
  - `stats-panel.js` - Statistics and charts
  - `status-monitor.js` - System status and logs
- `./frontend/js/api/` - API communication modules:
  - `audiobooks.js` - Library data operations
  - `downloads.js` - Download management
  - `system.js` - System status and controls
- `./frontend/assets/` - Static assets (icons, placeholder images)

Include a README.md in the frontend directory explaining how to run the dashboard and connect it to the backend.
</output>

<verification>
Before declaring complete, verify:

1. Dashboard loads successfully in multiple browsers (Chrome, Firefox, Safari)
2. All UI components render correctly on desktop and mobile
3. API calls work with mock data (create test endpoints if needed)
4. Search and filter functionality works correctly
5. Responsive design adapts to different screen sizes
6. Error states are handled gracefully
7. Performance is acceptable with large datasets (1000+ books)

Test the integration with the actual MAMcrawler backend once the UI is complete.
</verification>

<success_criteria>
- Fully functional dashboard that displays audiobook library
- Responsive design working on all devices
- Real-time updates for download progress and system status
- Intuitive user interface with clear navigation
- Proper error handling and loading states
- Clean, maintainable code structure
- Documentation for setup and usage
</success_criteria>
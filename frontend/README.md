# MAMcrawler Dashboard

A modern, responsive web dashboard for managing your MAMcrawler audiobook collection and download system.

## Features

### 📚 Library Management
- **Grid/List View**: Browse your audiobook collection with cover images
- **Advanced Search**: Find books by title, author, series, or genre
- **Smart Filtering**: Filter by status, genre, and other metadata
- **Bulk Operations**: Select and manage multiple books at once
- **Pagination**: Efficiently navigate large collections

### ⬇️ Download Management
- **Real-time Progress**: Monitor active downloads with live progress bars
- **Queue Management**: View and control download queues
- **Download Controls**: Pause, resume, cancel, and retry downloads
- **Status Tracking**: Track download history and success rates

### 📊 Statistics & Analytics
- **Collection Overview**: Total books, series, authors, and file sizes
- **Genre Distribution**: Visual charts showing your collection breakdown
- **Download Activity**: Track download trends over time
- **Metadata Quality**: Monitor completeness of book metadata

### 🔧 System Monitoring
- **Service Status**: Real-time status of crawler, database, and integrations
- **Activity Logs**: Recent system activity and error tracking
- **Performance Metrics**: CPU, memory, and storage usage
- **System Controls**: Start/stop crawler and trigger system scans

## Quick Start

### Prerequisites

1. **Backend API**: Ensure the MAMcrawler backend is running on `http://localhost:8000`
2. **Modern Browser**: Chrome 90+, Firefox 88+, Safari 14+, or Edge 90+
3. **Web Server**: For local development, use any static file server

### Running the Dashboard

1. **Clone or navigate to the frontend directory**:
   ```bash
   cd frontend/
   ```

2. **Start a local web server**:
   ```bash
   # Using Python (if available)
   python -m http.server 8080

   # Using Node.js (if available)
   npx http-server -p 8080

   # Or use any static file server
   ```

3. **Open your browser** and navigate to:
   ```
   http://localhost:8080/index.html
   ```

4. **Configure API connection** (if needed):
   - The dashboard defaults to `http://localhost:8000/api`
   - If your backend runs on a different port/host, modify `apiBaseUrl` in `js/dashboard.js`

## Configuration

### API Configuration

Edit `js/dashboard.js` to change the backend API URL:

```javascript
this.apiBaseUrl = 'http://your-backend-host:port/api';
```

### Authentication

If your backend requires API keys:

1. Set the API key in localStorage:
   ```javascript
   localStorage.setItem('mamcrawler-api-key', 'your-api-key-here');
   ```

2. Or modify the dashboard initialization to prompt for the key

### Theme Preferences

The dashboard supports light and dark themes:

- **Auto-detection**: Follows your system preference by default
- **Manual toggle**: Use the theme toggle button in the header
- **Persistent**: Your choice is saved in localStorage

## File Structure

```
frontend/
├── index.html              # Main dashboard HTML
├── css/
│   └── styles.css          # Complete styling and responsive design
├── js/
│   ├── dashboard.js        # Main application logic
│   ├── components/
│   │   ├── library-view.js     # Library display and management
│   │   ├── download-manager.js # Download controls and progress
│   │   ├── stats-panel.js      # Statistics and charts
│   │   └── status-monitor.js   # System status and logs
│   └── api/
│       ├── audiobooks.js   # Library data operations
│       ├── downloads.js    # Download management
│       └── system.js       # System status and controls
└── assets/                 # Static assets (icons, images)
```

## Browser Support

- **Chrome**: 90+
- **Firefox**: 88+
- **Safari**: 14+
- **Edge**: 90+
- **Mobile browsers**: iOS Safari 14+, Chrome Mobile 90+

## Features in Detail

### Library View

- **Cover Images**: Displays book covers with fallback to title initials
- **Metadata Display**: Shows author, series, status, and other details
- **Quick Actions**: Download, view details, archive, or delete books
- **Responsive Grid**: Adapts from 1 column (mobile) to 4+ columns (desktop)

### Download Management

- **Progress Visualization**: Animated progress bars with percentage and ETA
- **Status Indicators**: Color-coded status badges (queued, downloading, completed, failed)
- **Action Buttons**: Context-sensitive controls based on download status
- **Bulk Operations**: Select multiple downloads for batch actions

### Statistics Dashboard

- **Real-time Updates**: Charts update automatically with new data
- **Interactive Elements**: Hover tooltips and clickable legends
- **Export Options**: Download charts as images
- **Responsive Charts**: Adapt to different screen sizes

### System Status

- **Health Indicators**: Visual status dots (green/yellow/red)
- **Detailed Metrics**: CPU, memory, disk usage, and connection counts
- **Activity Timeline**: Recent system events with timestamps
- **Control Panel**: Quick access to system management functions

## Development

### Adding New Features

1. **Components**: Add new component files in `js/components/`
2. **API Modules**: Add API communication logic in `js/api/`
3. **Styling**: Extend `css/styles.css` with new styles
4. **Integration**: Initialize new components in `dashboard.js`

### Code Style

- **ES6+ Features**: Modern JavaScript with async/await
- **Modular Design**: Separate concerns across multiple files
- **Error Handling**: Comprehensive try/catch blocks
- **Accessibility**: ARIA labels and keyboard navigation support

### Testing

The dashboard includes mock data fallbacks for development:

- **API Failures**: Graceful degradation when backend is unavailable
- **Loading States**: Skeleton screens and loading indicators
- **Error Boundaries**: User-friendly error messages
- **Offline Mode**: Basic functionality without backend connection

## Troubleshooting

### Common Issues

**Dashboard won't load**
- Check that your web server is running
- Verify the HTML file path is correct
- Check browser console for JavaScript errors

**API connection fails**
- Ensure backend is running on the expected port
- Check CORS settings if running on different domains
- Verify API endpoints match the expected format

**Styling issues**
- Clear browser cache
- Check for CSS loading errors in developer tools
- Verify responsive breakpoints are working

**Performance problems**
- Enable browser developer tools performance tab
- Check for memory leaks in long-running sessions
- Monitor network requests for slow API calls

### Debug Mode

Enable debug logging by opening browser console:

```javascript
localStorage.setItem('mamcrawler-debug', 'true');
```

This will show detailed API request/response information.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly across different browsers
5. Submit a pull request

## License

This dashboard is part of the MAMcrawler project. See the main project license for details.

## Support

For issues or questions:

1. Check this README for common solutions
2. Review browser console for error messages
3. Check backend logs for API-related issues
4. Create an issue in the main MAMcrawler repository

---

**Happy listening! 📖🎧**
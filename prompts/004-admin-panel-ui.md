<objective>
Build a comprehensive admin panel for the MAMcrawler system that allows administrators to configure, monitor, and manage all aspects of the audiobook crawling and management platform. This panel will provide fine-grained control over system settings, user management, and operational parameters.

The admin panel should enable administrators to:
- Configure crawler settings and schedules
- Manage user accounts and permissions
- Monitor system performance and logs
- Configure integrations (qBittorrent, Audiobookshelf, etc.)
- View and manage system backups
- Access advanced troubleshooting tools
- Generate system reports and analytics

This will be the control center for system administrators to maintain and optimize the MAMcrawler platform.
</objective>

<context>
This is for the MAMcrawler project administrators, providing a web-based interface to manage the complex Python-based audiobook crawling and management system. The admin panel needs to expose all configuration options and monitoring capabilities in an intuitive, secure interface.

The panel should integrate with all existing MAMcrawler components:
- Crawler configuration and scheduling
- qBittorrent integration settings
- Audiobookshelf API configuration
- Database management and backups
- User authentication and authorization
- System logging and monitoring
- VPN and proxy configurations

Security is critical - this interface should require proper authentication and authorization.
</context>

<requirements>
Create a secure, feature-rich admin panel with the following sections:

1. **System Configuration**
   - Crawler settings (intervals, limits, sources)
   - Database connection and backup settings
   - File system paths and storage management
   - Network settings (proxies, VPN, timeouts)

2. **Integration Management**
   - qBittorrent connection and authentication
   - Audiobookshelf server configuration
   - External API credentials (Goodreads, etc.)
   - Webhook and notification settings

3. **User Management**
   - User account creation and management
   - Role-based access control
   - Authentication settings
   - Session management

4. **Monitoring & Analytics**
   - Real-time system metrics (CPU, memory, disk)
   - Crawler performance statistics
   - Error logs and troubleshooting tools
   - Download and processing analytics

5. **Maintenance Tools**
   - Database maintenance and optimization
   - Log file management and rotation
   - System backup and restore
   - Cache clearing and system reset options

6. **Security Settings**
   - Password policies and security settings
   - API key management
   - Audit logging
   - Access control and permissions

Implement proper authentication, input validation, and secure API communication.
</requirements>

<implementation>
**Technology Stack:**
- HTML5 with semantic admin interface structure
- CSS3 with admin-specific styling (forms, tables, modals)
- JavaScript with secure API communication
- JWT or session-based authentication
- Progressive Web App features for offline access
- Service Worker for background sync

**Security Architecture:**
- HTTPS-only communication
- JWT token management with refresh
- CSRF protection on all forms
- Input sanitization and validation
- Role-based UI component visibility
- Audit logging for all admin actions

**Admin UX Patterns:**
- Tabbed interface for different admin sections
- Modal dialogs for complex forms
- Confirmation dialogs for destructive actions
- Toast notifications for feedback
- Loading states and progress indicators
- Responsive design for mobile admin access

**Performance Considerations:**
- Lazy loading of admin sections
- Efficient data fetching and caching
- Real-time updates via WebSocket
- Optimized bundle size and loading

**Integration:**
- RESTful admin API endpoints
- WebSocket for real-time monitoring
- File upload for configuration imports
- Export functionality for reports and backups
</implementation>

<output>
Create the following files in the `frontend/` directory:

- `./frontend/admin.html` - Main admin panel page
- `./frontend/css/admin.css` - Admin-specific styling and themes
- `./frontend/js/admin.js` - Main admin logic and authentication
- `./frontend/js/components/admin/` - Admin components:
  - `config-panel.js` - System configuration interface
  - `integration-panel.js` - Integration management
  - `user-management.js` - User account controls
  - `monitoring-dashboard.js` - System monitoring displays
  - `maintenance-tools.js` - Maintenance and backup tools
  - `security-settings.js` - Security configuration
- `./frontend/js/services/admin/` - Admin service modules:
  - `auth-service.js` - Authentication and authorization
  - `config-service.js` - Configuration management
  - `monitoring-service.js` - System monitoring API
  - `maintenance-service.js` - Maintenance operations
- `./frontend/js/utils/` - Additional utilities:
  - `validation.js` - Form validation utilities
  - `security.js` - Security helper functions

Create a separate authentication system that protects the admin panel.
</output>

<verification>
Before declaring complete, verify:

1. Admin panel requires proper authentication
2. All configuration options are accessible and functional
3. User management works correctly with role permissions
4. System monitoring displays accurate real-time data
5. Maintenance tools perform operations safely
6. Security settings are properly implemented
7. Interface is responsive and works on tablets
8. All forms have proper validation and error handling
9. Audit logging captures admin actions
10. Integration with MAMcrawler backend APIs works correctly

Test with actual MAMcrawler system to ensure all settings take effect properly.
</verification>

<success_criteria>
- Secure, fully functional admin panel with all MAMcrawler settings
- Role-based access control working correctly
- Real-time monitoring and alerting system
- Comprehensive maintenance and backup tools
- Intuitive interface for complex system management
- Proper security measures and audit logging
- Responsive design for various admin devices
- Complete documentation for all admin features
</success_criteria>
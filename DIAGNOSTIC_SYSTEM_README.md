# MAMcrawler Unified Diagnostic System

A comprehensive diagnostic and monitoring framework that consolidates all diagnostic scripts into a single, unified system.

## Overview

The diagnostic system replaces 10+ scattered diagnostic scripts with a modular, extensible framework that provides:

- **System Health Checks**: Comprehensive validation of all MAMcrawler components
- **Modular Architecture**: Specialized diagnostic modules for each service
- **CLI Interface**: Command-line tools with subcommands for different operations
- **Report Generation**: JSON and HTML report formats
- **Continuous Monitoring**: Real-time system monitoring capabilities
- **Error Handling**: Robust error handling and troubleshooting guidance

## Architecture

```
diagnostic_system.py          # Main CLI entry point
├── diagnostic_modules/       # Modular diagnostic components
│   ├── __init__.py
│   ├── base_diagnostic.py    # Base classes and utilities
│   ├── abs_diagnostic.py     # Audiobookshelf diagnostics
│   ├── qbittorrent_diagnostic.py  # qBittorrent diagnostics
│   ├── vpn_diagnostic.py     # VPN connectivity diagnostics
│   ├── mam_diagnostic.py     # MAM account diagnostics
│   ├── prowlarr_diagnostic.py     # Prowlarr diagnostics
│   ├── workflow_diagnostic.py     # Workflow monitoring
│   └── system_diagnostic.py       # System health checks
└── diagnostic_reports/       # Generated reports directory
```

## Quick Start

### Full System Health Check
```bash
python diagnostic_system.py health
```

### Individual Component Checks
```bash
python diagnostic_system.py abs           # Audiobookshelf diagnostics
python diagnostic_system.py qbittorrent   # qBittorrent diagnostics
python diagnostic_system.py vpn           # VPN connectivity check
python diagnostic_system.py mam           # MAM account status
python diagnostic_system.py prowlarr      # Prowlarr diagnostics
python diagnostic_system.py workflow      # Workflow monitoring
python diagnostic_system.py system        # System configuration
```

### Continuous Monitoring
```bash
# Monitor every 5 minutes for 1 hour
python diagnostic_system.py monitor --interval 300 --duration 3600
```

### Generate Reports
```bash
# JSON report (default)
python diagnostic_system.py report

# HTML report
python diagnostic_system.py report --format html --filename my_report
```

## Diagnostic Modules

### Audiobookshelf (ABS)
- Process status and port availability
- Database location and size validation
- Configuration file checks
- API connectivity testing

### qBittorrent
- Authentication and connectivity
- Queue status and torrent categorization
- Audiobooks category validation
- Server state and health analysis
- Torrent error detection

### VPN
- Process detection and network adapters
- SOCKS proxy port scanning
- Proxy functionality testing
- Split tunneling validation

### MAM (MyAnonamouse)
- Account credentials validation
- Website connectivity
- VIP status checking (when implemented)

### Prowlarr
- API connectivity and health checks
- Indexer configuration validation
- Search functionality testing

### Workflow
- Log file analysis and monitoring
- Progress tracking
- Error detection and reporting

### System
- Environment variable validation
- Python environment checks
- Required directory structure
- Overall system health assessment

## Report Formats

### JSON Reports
Structured data format suitable for:
- Automated processing
- Integration with other tools
- Historical analysis
- API consumption

### HTML Reports
Human-readable format with:
- Color-coded status indicators
- Collapsible sections
- Recommendations and troubleshooting guidance
- Print-friendly layout

## Configuration

The diagnostic system uses the same environment variables as the main MAMcrawler application:

```bash
# Required
ABS_URL=http://localhost:13378
ABS_TOKEN=your_abs_api_token
QBITTORRENT_URL=http://192.168.0.48:52095
QBITTORRENT_USERNAME=your_username
QBITTORRENT_PASSWORD=your_password
PROWLARR_URL=http://localhost:9696
PROWLARR_API_KEY=your_prowlarr_key

# Optional
MAM_USERNAME=your_mam_username
MAM_PASSWORD=your_mam_password
```

## Status Codes

- **OK**: Component is functioning correctly
- **WARNING**: Non-critical issues detected
- **ERROR**: Component has issues requiring attention
- **CRITICAL**: System-critical failure requiring immediate action

## Troubleshooting

### Common Issues

1. **Environment Variables Missing**
   ```
   ERROR: Missing required environment variables
   Solution: Set required variables in .env file
   ```

2. **Service Not Running**
   ```
   ERROR: Service connectivity failed
   Solution: Start the required service and check configuration
   ```

3. **Authentication Failed**
   ```
   ERROR: Authentication failed
   Solution: Verify credentials in .env file
   ```

### Debug Mode

Enable detailed logging:
```bash
export DIAGNOSTIC_LOG_LEVEL=DEBUG
python diagnostic_system.py health
```

## Integration

The diagnostic system integrates with existing MAMcrawler components:

- **Logging**: Uses the same logging infrastructure
- **Configuration**: Reads from the same .env file
- **Reports**: Stored in `diagnostic_reports/` directory
- **Monitoring**: Can be integrated with external monitoring systems

## Development

### Adding New Diagnostic Modules

1. Create new module in `diagnostic_modules/`
2. Inherit from `BaseDiagnostic`
3. Implement `run_diagnostics()` method
4. Add to `__init__.py` imports
5. Update CLI parser if needed

### Extending Reports

- Modify `_generate_html_report()` for custom HTML formatting
- Add new export formats in `save_report()` method
- Customize summary generation in `_generate_summary()`

## Migration from Old Scripts

The following scripts have been consolidated into the unified system:

| Old Script | New Command |
|------------|-------------|
| `diagnostic_abs.py` | `python diagnostic_system.py abs` |
| `check_vpn_connection.py` | `python diagnostic_system.py vpn` |
| `check_qb_queue.py` | `python diagnostic_system.py qbittorrent` |
| `comprehensive_workflow_monitor.py` | `python diagnostic_system.py workflow` |
| `prowlarr_diagnostic.py` | `python diagnostic_system.py prowlarr` |
| Various check_*.py scripts | `python diagnostic_system.py health` |

Old scripts are archived in `archived_diagnostics/` directory.

## Performance

- **Health Check**: < 30 seconds for full system
- **Individual Modules**: < 10 seconds each
- **Report Generation**: < 5 seconds
- **Memory Usage**: < 50MB during execution

## Future Enhancements

- Real-time dashboard web interface
- Alert system integration (email, Slack, etc.)
- Historical trend analysis
- Automated remediation actions
- Custom diagnostic plugins
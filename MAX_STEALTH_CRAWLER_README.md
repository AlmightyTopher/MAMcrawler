# Max Stealth Crawler

## Overview

The **Max Stealth Crawler** is a comprehensive implementation of state-of-the-art anti-detection techniques for web scraping. This crawler implements the complete blueprint for maximally stealthy scraping of sites with advanced anti-bot defenses like MyAnonamouse.

## Features Implemented

### ✅ Browser Automation Environment
- **Playwright** with **playwright-stealth** plugin integration
- Randomized viewport sizes and user agents
- Headful/browser mode for better stealth (configurable)
- Persistent browser profiles with cookie/localStorage retention

### ✅ TLS and Network Fingerprint Spoofing
- Custom TLS ClientHello parameters matching real browsers
- HTTP/2 support with proper frame ordering
- Randomized network flow timing to mimic browser behavior
- Comprehensive header spoofing (Sec-*, DNT, etc.)

### ✅ Proxy Management
- Rotating residential/mobile proxy support
- Sticky session IP affinity (one session = one IP)
- Geo-targeting capabilities
- Automatic proxy failure detection and rotation
- Support for premium proxy providers (BrightData, Oxylabs, etc.)

### ✅ Behavioral Simulation
- Realistic mouse movement with acceleration/deceleration curves
- Human-like scrolling patterns with reading pauses
- Natural typing delays and pauses
- Randomized dwell times on pages
- Session timing that mimics real user behavior

### ✅ CAPTCHA Handling
- Multi-provider CAPTCHA solving (2Captcha, AntiCaptcha, Capsolver)
- Automatic CAPTCHA detection and solving
- Robust retry logic with fallback options
- Token caching and reuse prevention

### ✅ JavaScript Challenge Handling
- Full page JavaScript execution in browser environment
- Custom JS injection capabilities for challenge override
- Analysis and mimicry of anti-bot scripts (fingerprintjs, Akamai, Cloudflare)
- Real-time telemetry pattern replication

### ✅ HTTP Request and Header Management
- Site-specific, realistic User-Agent strings
- Complete header sets matching real browsers
- Randomized header rotation to prevent repetition
- Proper Referer, Origin, Accept-Language headers
- Do-Not-Track and Sec-* header implementation

### ✅ Network Request Interception
- XHR/fetch/GraphQL request interception
- WebSocket message monitoring
- API endpoint discovery and scraping
- Request/response header modification in-flight

### ✅ Adaptive Rate Limiting and Scheduling
- Exponential backoff with jitter on failures
- Dynamic rate adjustment based on response patterns
- Time zone-aware scheduling (normal activity hours)
- Burst control and request queuing

### ✅ Comprehensive Monitoring and Logging
- Detailed request/response logging
- Performance metrics collection
- CAPTCHA encounter/solve tracking
- Proxy usage and failure monitoring
- Session recovery and manual override modes

## Installation

### Prerequisites
```bash
# Python 3.8+
python --version

# Node.js (for Playwright browser installation)
node --version
```

### Setup
```bash
# Clone or ensure you're in the MAMcrawler project directory
cd /path/to/MAMcrawler

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install playwright python-dotenv httpx
pip install playwright-stealth  # For stealth plugin

# Install Playwright browsers
playwright install
```

### Environment Configuration
Create a `.env` file with your credentials and API keys:

```bash
# MyAnonamouse Credentials
MAM_USERNAME=your_mam_username
MAM_PASSWORD=your_mam_password

# Proxy Configuration (optional)
STEALTH_PROXIES=http://user:pass@proxy1.example.com:8080,http://user:pass@proxy2.example.com:8080

# CAPTCHA API Keys (optional)
CAPTCHA_2CAPTCHA_KEY=your_2captcha_key
CAPTCHA_ANTICAPTCHA_KEY=your_anticaptcha_key
CAPTCHA_CAPSOLVER_KEY=your_capsolver_key
```

## Usage

### Basic Usage

```python
import asyncio
from max_stealth_crawler import MaxStealthCrawler

async def main():
    # Initialize crawler
    target_url = "https://www.myanonamouse.net"
    credentials = {
        'username': "your_username",
        'password': "your_password"
    }

    crawler = MaxStealthCrawler(target_url, credentials)

    # Define URLs to crawl
    urls = [
        f"{target_url}/torrents.php",
        f"{target_url}/browse.php?cat=13",  # Audiobooks category
    ]

    # Define data extraction selectors
    selectors = {
        'titles': 'a[href*="torrent"]',
        'categories': '.category',
        'sizes': '.size',
        'seeders': '.seeders',
        'leechers': '.leechers'
    }

    try:
        # Run stealth crawl
        results = await crawler.crawl_with_stealth(urls, selectors)

        # Process results
        for result in results:
            print(f"Crawled: {result['url']}")
            print(f"Data extracted: {result['data']}")

    finally:
        await crawler.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Configuration

```python
from max_stealth_crawler import MaxStealthCrawler, StealthConfig

# Custom configuration
config = StealthConfig()
config.browser_type = "firefox"  # Use Firefox instead of Chromium
config.headless = True  # Run headless for server environments
config.behavior_config['mouse_speed_min'] = 200  # Faster mouse movements
config.rate_limit_config['requests_per_minute'] = 5  # More conservative rate limiting

# Create crawler with custom config
crawler = MaxStealthCrawler(target_url, credentials)
crawler.config = config  # Override default config
```

### Proxy Configuration

```python
# Environment variable approach
# STEALTH_PROXIES=http://user:pass@us-proxy.example.com:8080,http://user:pass@eu-proxy.example.com:8080

# Or programmatic configuration
crawler.config.proxy_config.update({
    'rotation_enabled': True,
    'sticky_sessions': True,
    'geo_targeting': 'US',
    'max_failures': 5
})
```

### CAPTCHA Solving Setup

```python
# Set API keys in environment or programmatically
crawler.captcha_solver.api_keys.update({
    '2captcha': 'your_2captcha_key',
    'anticaptcha': 'your_anticaptcha_key'
})

# Configure solving preferences
crawler.config.captcha_config.update({
    'solvers': ['2captcha', 'anticaptcha'],  # Priority order
    'max_retries': 5,
    'timeout': 180
})
```

## Configuration Options

### StealthConfig Class

| Setting | Default | Description |
|---------|---------|-------------|
| `browser_type` | "chromium" | Browser type: chromium, firefox, webkit |
| `headless` | False | Run browser in headless mode |
| `user_agents` | [...] | List of user agent strings to rotate |
| `viewports` | [...] | List of viewport sizes (width, height) |

### Proxy Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `rotation_enabled` | True | Enable automatic proxy rotation |
| `sticky_sessions` | True | Use same proxy for entire session |
| `geo_targeting` | "US" | Target specific geographic region |
| `max_failures` | 3 | Max failures before marking proxy dead |

### Behavioral Simulation

| Setting | Default | Description |
|---------|---------|-------------|
| `mouse_speed_min/max` | 100/800 | Mouse movement speed range (pixels/sec) |
| `scroll_pause_min/max` | 500/2000 | Pause between scroll actions (ms) |
| `typing_delay_min/max` | 80/250 | Typing delay between characters (ms) |
| `page_read_time_min/max` | 3000/8000 | Time spent "reading" pages (ms) |

### Rate Limiting

| Setting | Default | Description |
|---------|---------|-------------|
| `requests_per_minute` | 10 | Max requests per minute |
| `burst_limit` | 3 | Max burst requests |
| `backoff_base` | 5 | Base backoff time (seconds) |
| `jitter_range` | (0.5, 1.5) | Backoff jitter multiplier range |

## Monitoring and Debugging

### Log Files
- `max_stealth_crawler.log` - Main application logs
- `stealth_crawl_report_[timestamp].json` - Session reports
- Screenshots on failures (when enabled)

### Monitoring Data Structure
```json
{
  "session_id": "stealth_session_1234567890",
  "start_time": "2025-11-26T20:42:28.244Z",
  "end_time": "2025-11-26T21:15:33.123Z",
  "total_urls": 5,
  "successful_extractions": 4,
  "total_requests": 127,
  "failures": 2,
  "captchas_encountered": 1,
  "captchas_solved": 1,
  "proxies_used": ["us-proxy-1", "us-proxy-2"],
  "stealth_metrics": {
    "browser_type": "chromium",
    "headless": false,
    "proxy_rotation": true,
    "behavior_simulation": true,
    "rate_limiting": true,
    "captcha_handling": true
  }
}
```

### Troubleshooting

#### Common Issues

1. **Browser Launch Failures**
   ```bash
   # Reinstall Playwright browsers
   playwright install chromium

   # Check system dependencies
   playwright install-deps
   ```

2. **Proxy Connection Issues**
   - Verify proxy credentials and format
   - Test proxies manually before use
   - Check geo-targeting settings

3. **CAPTCHA Solving Failures**
   - Verify API keys and balances
   - Check CAPTCHA service status
   - Adjust timeout settings

4. **Rate Limiting Issues**
   - Reduce `requests_per_minute` setting
   - Increase delays between requests
   - Check target site rate limit policies

#### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed monitoring
crawler.config.monitoring_config.update({
    'detailed_logging': True,
    'screenshot_on_failure': True,
    'performance_metrics': True
})
```

## Security Considerations

### ⚠️ Important Security Notes

1. **Legal Compliance**: Ensure compliance with target site's Terms of Service and applicable laws
2. **Rate Limiting**: Respect site rate limits to avoid IP bans
3. **Data Usage**: Only collect publicly available data
4. **Proxy Usage**: Use legitimate proxy services with proper authorization
5. **CAPTCHA Services**: Use reputable CAPTCHA solving services

### Best Practices

1. **Start Slow**: Begin with conservative settings and gradually increase
2. **Monitor Performance**: Regularly review logs and adjust configurations
3. **Rotate Resources**: Regularly update user agents, proxies, and fingerprints
4. **Error Handling**: Implement proper error handling and recovery mechanisms
5. **Session Management**: Use different sessions for different tasks

## API Reference

### MaxStealthCrawler Class

#### Methods

- `__init__(target_url, credentials=None)` - Initialize crawler
- `initialize()` - Set up browser and components
- `authenticate()` - Perform stealth authentication
- `navigate_to_page(url)` - Navigate with stealth techniques
- `extract_data(selectors)` - Extract data using CSS selectors
- `crawl_with_stealth(urls, selectors)` - Main crawling method
- `cleanup()` - Clean up resources

#### Properties

- `config` - StealthConfig instance
- `proxy_manager` - ProxyManager instance
- `behavior_simulator` - BehavioralSimulator instance
- `captcha_solver` - CAPTCHASolver instance
- `rate_limiter` - RateLimiter instance

## Contributing

This implementation follows the comprehensive stealth blueprint. For enhancements:

1. Test thoroughly with target sites
2. Maintain backward compatibility
3. Update documentation
4. Add comprehensive logging
5. Follow security best practices

## License

This implementation is provided for educational and research purposes. Ensure compliance with applicable laws and terms of service.

---

**Note**: This crawler implements state-of-the-art anti-detection techniques. Success rates depend on target site defenses and proper configuration. Regular updates may be needed to maintain effectiveness against evolving anti-bot measures.
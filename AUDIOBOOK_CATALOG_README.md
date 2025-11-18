# Audiobook Catalog Crawler

Interactive crawler and query system for the audiobook catalog website at https://mango-mushroom-0d3dde80f.azurestaticapps.net/

## Features

- **Browser-based crawling** with JavaScript support for React/SPA sites
- **Automatic filter extraction** - Discovers genres and timespans from the website
- **Interactive CLI** - Easy genre/timespan selection and querying
- **qBittorrent integration** - Add audiobooks directly to your download queue
- **Screenshot debugging** - Visual confirmation of crawler behavior
- **Result caching** - Fast subsequent queries

## Installation

### 1. Install Dependencies

```bash
# Make sure you have the MAM crawler dependencies already installed
pip install crawl4ai qbittorrent-api beautifulsoup4 lxml
```

### 2. Configure qBittorrent (Optional)

Add to your `.env` file:

```bash
# qBittorrent Web UI settings
QB_HOST=localhost
QB_PORT=8080
QB_USERNAME=admin
QB_PASSWORD=adminadmin
```

**Enable qBittorrent Web UI:**
1. Open qBittorrent
2. Go to Tools → Options → Web UI
3. Check "Web User Interface (Remote control)"
4. Set username and password
5. Note the port number (default: 8080)

## Usage

### Step 1: Discover Site Structure

First, run the discovery process to map genres and timespans:

```bash
python audiobook_catalog_crawler.py
```

This will:
- Navigate to the audiobooks section
- Extract available genres and timespans
- Save filters to `catalog_cache/genres.json` and `timespans.json`
- Take screenshots for debugging (`catalog_cache/audiobooks_page.png`)

### Step 2: Interactive Query

Run the interactive query interface:

```bash
python audiobook_query.py
```

**Interactive Menu:**
```
1. Show genres       - Display all available genres
2. Show timespans    - Display all available timespans
3. Query audiobooks  - Search by genre and timespan
4. Refresh filters   - Re-discover genres/timespans from website
5. Exit
```

**Query Workflow:**
1. Select "3. Query audiobooks"
2. View genres and enter a number (e.g., `3` for Mystery)
3. View timespans and enter a number (e.g., `2` for 2020-2023)
4. View results
5. Optionally add an audiobook to qBittorrent by entering its number

### Step 3: Command-Line Mode

For automation or scripting:

```bash
# Refresh filters from website
python audiobook_query.py refresh

# Show available genres
python audiobook_query.py genres

# Show available timespans
python audiobook_query.py timespans

# Query directly (genre #2, timespan #3)
python audiobook_query.py query 2 3
```

## File Structure

```
MAMcrawler/
├── audiobook_catalog_crawler.py   # Core crawler logic
├── audiobook_query.py              # Interactive query interface
├── catalog_cache/                  # Cached data and screenshots
│   ├── genres.json                 # Available genres
│   ├── timespans.json              # Available timespans
│   ├── audiobooks_page.png         # Screenshot of audiobooks page
│   ├── results_*.png               # Query result screenshots
│   ├── raw_results.html            # Raw HTML for debugging
│   └── raw_results.md              # Markdown version
└── audiobook_catalog.log           # Crawler logs
```

## How It Works

### 1. Browser Automation

Uses Crawl4AI with headless Chrome to:
- Execute JavaScript (required for React apps)
- Simulate user interactions (clicks, form submissions)
- Wait for dynamic content to load
- Take screenshots for debugging

### 2. Filter Extraction

Automatically discovers filters by:
- Looking for `<select>` dropdowns
- Searching for genre/timespan-related elements
- Extracting option values and labels
- Caching results for fast subsequent queries

### 3. Query Process

When you query by genre/timespan:
1. Navigates to the audiobooks section
2. Selects the genre from dropdown (or equivalent)
3. Selects the timespan from dropdown
4. Clicks search/submit button
5. Waits for results to load
6. Extracts audiobook data from results page
7. Displays results in formatted output

### 4. Data Extraction

Attempts multiple extraction strategies:
- **Table rows** - Common for data listings
- **List items** - For card/tile layouts
- **Fallback** - Saves raw HTML/Markdown for manual inspection

### 5. qBittorrent Integration

When you select an audiobook:
- Extracts torrent/magnet link
- Connects to qBittorrent Web UI
- Adds torrent to download queue
- Confirms addition

## Troubleshooting

### No Filters Found

If genres/timespans are empty:

1. **Check the screenshot**:
   ```bash
   # Open catalog_cache/audiobooks_page.png
   # Verify you're on the correct page
   ```

2. **Review raw HTML**:
   ```bash
   # Check catalog_cache/raw_results.html
   # Look for dropdown menus, filters, or selection elements
   ```

3. **Adjust extraction logic**:
   - The site structure may differ from expected
   - Edit `audiobook_catalog_crawler.py` → `extract_filters()` method
   - Update CSS selectors to match actual site structure

### No Results Found

If query returns empty results:

1. **Check query screenshot**:
   ```bash
   # Open catalog_cache/results_<genre>_<timespan>.png
   # Verify filters were applied correctly
   ```

2. **Review extraction logic**:
   - Edit `_extract_audiobooks_from_html()` method
   - Add CSS selectors matching the site's result structure

3. **Check raw output**:
   - Examine `catalog_cache/raw_results.html`
   - Identify the HTML structure of audiobook results

### qBittorrent Connection Failed

If can't connect to qBittorrent:

1. **Enable Web UI**:
   - Open qBittorrent → Tools → Options → Web UI
   - Enable "Web User Interface"

2. **Check firewall**:
   ```bash
   # Test if qBittorrent is accessible
   curl http://localhost:8080
   ```

3. **Verify credentials**:
   - Check `.env` file has correct QB_USERNAME and QB_PASSWORD
   - Match the credentials in qBittorrent Web UI settings

## Advanced Customization

### Modify Crawling Behavior

Edit `audiobook_catalog_crawler.py`:

```python
# Change viewport size
def create_browser_config(self) -> BrowserConfig:
    return BrowserConfig(
        viewport_width=1366,  # Your preferred width
        viewport_height=768    # Your preferred height
    )

# Adjust wait times
js_navigate = """
    await new Promise(resolve => setTimeout(resolve, 5000));  # Wait longer
"""
```

### Custom Extraction Logic

Add your own extraction patterns:

```python
# In _extract_audiobooks_from_html()
for item in soup.find_all('div', class_='your-custom-class'):
    audiobook = {
        'title': item.select_one('.title').text,
        'link': item.select_one('a')['href']
    }
    audiobooks.append(audiobook)
```

### Batch Downloads

Automate multiple downloads:

```python
# Query multiple genre/timespan combinations
results = []
for genre_idx in range(1, 5):
    for timespan_idx in range(1, 3):
        books = await interface.query_audiobooks(genre_idx, timespan_idx)
        results.extend(books)

# Add all to qBittorrent
for book in results:
    await interface.add_to_qbittorrent(book)
```

## Integration with Existing MAM Crawler

This audiobook catalog crawler is **separate** from the MAM crawler:

- **MAM Crawler** → For MyAnonamouse.net (private tracker)
- **Audiobook Catalog Crawler** → For Azure audiobook catalog (different site)

Both use similar technologies (Crawl4AI, browser automation) but target different websites.

## Ethical Considerations

- **Respect rate limits** - Don't spam the website
- **Cache results** - Avoid unnecessary repeat queries
- **Terms of service** - Ensure you're allowed to crawl the site
- **Personal use** - Don't redistribute scraped data

## Next Steps

1. **Run discovery** to map the site
2. **Review screenshots** to confirm proper navigation
3. **Test queries** with different genre/timespan combinations
4. **Integrate with qBittorrent** for automatic downloads
5. **Customize extraction** based on actual site structure

## Support

If you encounter issues:

1. Check the logs: `audiobook_catalog.log`
2. Review screenshots in `catalog_cache/`
3. Inspect raw HTML output
4. Adjust CSS selectors based on actual site structure

## Future Enhancements

- [ ] Automatic genre/timespan permutation queries
- [ ] Result filtering and sorting
- [ ] Download queue management
- [ ] Integration with other download managers
- [ ] Web UI for easier interaction
- [ ] Scheduled automatic queries

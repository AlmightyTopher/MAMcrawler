# Master Audiobook Management System

## Overview

The Master Audiobook Management System is a comprehensive solution that integrates audiobook metadata management, missing book detection, and on-demand search capabilities. This system provides:

1. **Full Metadata Updates** - Updates all books with detailed metadata across your Audiobookshelf library
2. **Missing Book Detection** - Prioritizes finding missing books by series first, then by author
3. **Top 10 Audiobook Search** - On-demand audiobook search using stealth crawling
4. **Automated Scheduling** - Run any operation whenever needed

## Quick Start

### Basic Commands

```bash
# Check system status
python master_audiobook_manager.py --status

# Update all book metadata
python master_audiobook_manager.py --update-metadata

# Detect missing books
python master_audiobook_manager.py --missing-books

# Run top 10 audiobook search
python master_audiobook_manager.py --top-search

# Run complete synchronization (all operations)
python master_audiobook_manager.py --full-sync
```

## Features Detailed

### 1. Metadata Updates (`--update-metadata`)

**What it does:**
- Connects to your Audiobookshelf instance
- Fetches all books from your library
- Enriches metadata using Google Books API
- Updates series information and missing fields
- Generates detailed metadata analysis reports

**Priority order for metadata enhancement:**
1. Series information (series name, book number)
2. Author names and complete author data
3. ISBN numbers for identification
4. Genres and categories
5. Publication year and publisher
6. Book descriptions and additional metadata

**Output:**
- Updated Audiobookshelf library with enhanced metadata
- `metadata_analysis_[timestamp].md` report showing completeness statistics
- Console logs with detailed progress information

### 2. Missing Book Detection (`--missing-books`)

**What it does:**
- Analyzes your current Audiobookshelf library
- Identifies missing books with prioritized approach

**Priority Levels:**
1. **Series Priority** (First priority)
   - Finds gaps in book series you're collecting
   - Identifies missing books within known series
   - Shows exact book numbers missing

2. **Author Priority** (Second priority)
   - Identifies authors with multiple books where you might be missing others
   - Flags high-volume authors who likely have more content

**Output:**
- `missing_books_[timestamp].md` report with:
  - Series with missing books (shows exact numbers)
  - Authors with likely missing books
  - Detailed statistics and recommendations

### 3. Top 10 Search (`--top-search`)

**What it does:**
- Uses the stealth Audiobookshelf crawler to search MyAnonamouse
- Runs searches for "Audiobookshelf", "ABS", and related terms
- Collects and ranks results by relevance
- Provides top 10 most recent/valuable finds

**Search Terms Used:**
- "Audiobookshelf"
- "audiobookshelf" 
- "audio book shelf"
- "ABS"

**Output:**
- `top_10_search_[timestamp].md` report
- Raw results in `audiobookshelf_output/` directory
- Summary statistics and recommendations

### 4. Full Synchronization (`--full-sync`)

**What it does:**
- Runs all operations in sequence:
  1. Metadata updates
  2. Missing book detection  
  3. Top 10 search
- Generates comprehensive reports
- Provides complete library analysis

## Configuration

### Environment Variables Required

Create or update your `.env` file with these variables:

```bash
# Audiobookshelf Configuration
ABS_URL=http://localhost:13378
ABS_TOKEN=your_audiobookshelf_token_here

# MyAnonamouse Login (for stealth crawler)
MAM_USERNAME=your_mam_username
MAM_PASSWORD=your_mam_password

# Optional: qBittorrent Configuration (for auto-download)
QB_HOST=localhost
QB_PORT=8080
QB_USERNAME=admin
QB_PASSWORD=adminadmin
```

### Getting Your Audiobookshelf Token

1. Open your Audiobookshelf web interface
2. Go to Settings → Account
3. Generate a new API token
4. Copy the token and add it to your `.env` file as `ABS_TOKEN`

## Output Directory Structure

The system creates organized output directories:

```
📁 Project Root/
├── 📁 metadata_analysis/          # Metadata analysis reports
├── 📁 missing_books/              # Missing book detection reports  
├── 📁 search_results/             # Top 10 search results
├── 📁 reports/                    # Comprehensive reports
├── 📁 audiobookshelf_output/      # Raw crawler results
└── 📄 master_manager_*.log        # Operation logs
```

## Reports Generated

### Metadata Analysis Report
- Overall library statistics
- Metadata completeness percentages
- Library-by-library breakdown
- Books missing critical metadata

### Missing Books Report
- Series with missing books (with exact numbers)
- Author analysis for high-volume authors
- Prioritized recommendations
- Actionable next steps

### Top 10 Search Report
- Most recent audiobook finds
- Relevance-ranked results
- Direct download links when available
- Category and size information

## Use Cases

### 1. Library Maintenance
```bash
# Run monthly to keep metadata fresh
python master_audiobook_manager.py --update-metadata
```

### 2. Collection Completion
```bash
# Find missing books in series you're collecting
python master_audiobook_manager.py --missing-books
```

### 3. Discovery
```bash
# Find new audiobooks weekly
python master_audiobook_manager.py --top-search
```

### 4. Comprehensive Analysis
```bash
# Full library audit and update
python master_audiobook_manager.py --full-sync
```

## Scheduling and Automation

### Windows Task Scheduler
Create scheduled tasks to run automatically:

1. **Weekly Metadata Update**
   ```bash
   Program: python
   Arguments: master_audiobook_manager.py --update-metadata
   Schedule: Every Monday at 2 AM
   ```

2. **Bi-weekly Missing Book Detection**
   ```bash
   Program: python
   Arguments: master_audiobook_manager.py --missing-books
   Schedule: Every other Sunday at 3 AM
   ```

3. **Daily Discovery**
   ```bash
   Program: python
   Arguments: master_audiobook_manager.py --top-search
   Schedule: Every day at 1 AM
   ```

### Manual Execution
Simply run commands when you need them:

```bash
# When you notice missing metadata
python master_audiobook_manager.py --update-metadata

# When you want to complete a series
python master_audiobook_manager.py --missing-books

# When looking for new content
python master_audiobook_manager.py --top-search

# Periodic comprehensive maintenance
python master_audiobook_manager.py --full-sync
```

## Error Handling

The system includes comprehensive error handling:

- **Connection Issues**: Gracefully handles Audiobookshelf connection failures
- **API Limits**: Respects Google Books API rate limits with delays
- **Crawler Issues**: Continues operation if individual searches fail
- **Missing Data**: Reports incomplete results rather than crashing

## Logs and Debugging

All operations generate detailed logs:

- **Console Output**: Real-time progress and status
- **Log Files**: Timestamped logs for each operation
- **Error Tracking**: Specific error logging for troubleshooting
- **Statistics**: Comprehensive operation statistics

## Integration with Existing Tools

The system integrates seamlessly with existing audiobook tools:

- **Audiobookshelf**: Direct API integration for updates
- **Stealth Crawler**: Reuses proven MyAnonamouse crawling technology
- **Unified Metadata Aggregator**: Leverages existing metadata enrichment
- **qBittorrent**: Compatible with automated downloading workflows

## Best Practices

1. **Regular Updates**: Run metadata updates monthly to maintain data quality
2. **Series Focus**: Use missing book detection to complete series you're collecting
3. **Discovery Schedule**: Regular top 10 searches for new content discovery
4. **Full Syncs**: Periodic comprehensive analysis for complete library health
5. **Backup**: Keep reports for historical analysis and backup

## Troubleshooting

### Common Issues

1. **ABS_TOKEN not set**
   - Generate new token in Audiobookshelf Settings → Account
   - Add to `.env` file

2. **Connection refused to Audiobookshelf**
   - Ensure Audiobookshelf is running
   - Check `ABS_URL` in `.env` file
   - Verify network connectivity

3. **No books found in library**
   - Verify `ABS_TOKEN` has proper permissions
   - Check that library has audiobooks
   - Ensure API endpoint is accessible

4. **Stealth crawler fails**
   - Verify MAM credentials in `.env` file
   - Check MyAnonamouse is accessible
   - Review logs for specific error details

### Getting Help

- Check the generated log files for detailed error information
- Review the status output with `--status` flag
- Consult individual component documentation for specific issues

## Advanced Usage

### Custom Search Terms
The stealth crawler can be extended with additional search terms by modifying the `search_terms` list in `stealth_audiobookshelf_crawler.py`.

### Extended Metadata Fields
Additional metadata fields can be added to the `FIELDS` list in `unified_metadata_aggregator.py` for more comprehensive metadata enrichment.

### Report Customization
Report templates can be customized by modifying the report generation methods in the `MasterAudiobookManager` class.

---

**Version**: 1.0  
**Last Updated**: 2025-11-14  
**Compatibility**: Python 3.8+, Audiobookshelf API v1, Windows/macOS/Linux
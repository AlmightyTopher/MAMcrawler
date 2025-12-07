# MAMcrawler Quick Start Guide

Welcome to MAMcrawler! This guide will get you up and running with automated audiobook discovery, downloading, and library management in under 30 minutes.

## 🎯 What is MAMcrawler?

MAMcrawler is an automated audiobook management system that integrates:
- **MyAnonamouse (MAM)** - Private torrent tracker for audiobooks
- **AudiobookShelf** - Self-hosted audiobook server and player
- **qBittorrent** - Torrent client for downloads
- **Google Books API** - Metadata enrichment
- **Goodreads** - Additional metadata sources

It automatically discovers new audiobooks, downloads them, and organizes your library with complete metadata.

## 📋 Prerequisites

### Required Software
- **Python 3.8+** - Core runtime
- **qBittorrent** - Torrent client (with Web UI enabled)
- **AudiobookShelf** - Audiobook server
- **Git** - For cloning/updating

### System Requirements
- **OS**: Windows 10/11, Linux, or macOS
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 50GB+ free space for audiobooks
- **Network**: Stable internet connection

### Accounts Required
- **MyAnonamouse** account with download permissions
- **Google Books API** key (free)
- **AudiobookShelf** instance running

## 🚀 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-repo/MAMcrawler.git
cd MAMcrawler
```

### Step 2: Set Up Python Environment

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure Environment

Copy the example configuration:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
# Required: MyAnonamouse credentials
MAM_USERNAME=your_mam_username
MAM_PASSWORD=your_mam_password

# Required: AudiobookShelf
ABS_URL=http://localhost:13378
ABS_TOKEN=your_abs_api_token

# Required: qBittorrent Web UI
QBITTORRENT_URL=http://localhost:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=your_password

# Required: Google Books API
GOOGLE_BOOKS_API_KEY=your_google_api_key

# Optional: Download directory
DOWNLOAD_DIR=/path/to/downloads
```

## 🔧 Service Setup

### qBittorrent Configuration

1. **Install qBittorrent** from [qbittorrent.org](https://www.qbittorrent.org/)
2. **Enable Web UI**:
   - Open qBittorrent → Tools → Preferences → Web UI
   - Check "Enable Web UI"
   - Set username/password
   - Note the port (default: 8080)
3. **Configure Downloads**:
   - Set default download location
   - Enable "Run external program on torrent completion" if desired

### AudiobookShelf Setup

1. **Install AudiobookShelf**:
   ```bash
   # Docker (recommended)
   docker run -d \
     --name audiobookshelf \
     -p 13378:80 \
     -v /path/to/audiobooks:/audiobooks \
     -v /path/to/config:/config \
     -v /path/to/metadata:/metadata \
     ghcr.io/advplyr/audiobookshelf:latest
   ```

2. **Initial Configuration**:
   - Visit http://localhost:13378
   - Create admin account
   - Add your audiobook library folder
   - Generate API token (Settings → API)

### Google Books API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable "Books API"
4. Create credentials (API Key)
5. Copy the key to your `.env` file

## 🏃‍♂️ First Run

### Test Configuration

Verify your setup:
```bash
python -c "import config; print('Configuration loaded successfully')"
```

### Run a Simple Test

Execute a basic workflow test:
```bash
python execute_full_workflow.py --test
```

This will:
- Connect to all services
- Verify credentials
- Run a minimal workflow
- Report any configuration issues

### Full First Workflow

Run the complete automated workflow:
```bash
python execute_full_workflow.py
```

**What happens:**
1. **Library Scan** - Counts your existing audiobooks
2. **Genre Discovery** - Finds sci-fi and fantasy audiobooks
3. **Torrent Search** - Locates torrents on MyAnonamouse
4. **Download Queue** - Adds torrents to qBittorrent
5. **Download Monitor** - Waits for completion
6. **Library Import** - Adds books to AudiobookShelf
7. **Metadata Enhancement** - Improves book information
8. **Backup** - Creates safety backup

**Timeline:** 2-24 hours (most time is downloading)

## 📊 Monitoring Progress

### Check Workflow Status

Monitor the running workflow:
```bash
tail -f workflow.log
```

### Web Interfaces

- **AudiobookShelf**: http://localhost:13378
- **qBittorrent**: http://localhost:8080
- **Workflow Reports**: Check `workflow_final_report.json`

### Expected Results

After completion:
- **AudiobookShelf**: 10-20 new audiobooks added
- **qBittorrent**: New torrents seeding
- **Disk**: New audiobook files with metadata
- **Reports**: Complete workflow summary

## 🔧 Basic Usage

### Daily Operations

**Check System Health:**
```bash
python monitor_qbittorrent_health.py
```

**Run Automated Discovery:**
```bash
python execute_full_workflow.py --quick
```

### Manual Operations

**Search for Specific Books:**
```bash
python mam_crawler.py --author "Brandon Sanderson" --limit 5
```

**Update Metadata:**
```bash
python audiobook_metadata_corrector.py --all
```

**Check Library Gaps:**
```bash
python find_missing_books.py
```

## 🆘 Troubleshooting

### Common Issues

**"Connection refused" errors:**
- Verify services are running
- Check URLs in `.env`
- Test connectivity: `curl http://localhost:13378`

**Authentication failures:**
- Verify credentials in `.env`
- Check API tokens are valid
- Ensure accounts have proper permissions

**Download failures:**
- Check qBittorrent Web UI access
- Verify download directory permissions
- Confirm sufficient disk space

### Getting Help

1. **Check Logs**: `tail -f workflow.log`
2. **Run Diagnostics**: `python diagnostic_system.py`
3. **Documentation**: See [Troubleshooting Guide](../troubleshooting/)
4. **Community**: Check GitHub issues

## 🎯 Next Steps

### After First Successful Run

1. **Customize Settings** - Adjust search preferences
2. **Set Up Monitoring** - Configure alerts and notifications
3. **Schedule Automation** - Set up regular runs
4. **Explore Advanced Features** - Try custom workflows

### Advanced Configuration

- **VPN Setup** - For enhanced privacy
- **Multiple Libraries** - Manage different collections
- **Custom Metadata Rules** - Tailor enrichment
- **Backup Strategies** - Implement redundancy

## 📚 Further Reading

- **[User Guides](../guides/)** - Detailed feature documentation
- **[API Reference](../api/)** - Technical integration docs
- **[Development](../development/)** - Contributing and extending
- **[Deployment](../deployment/)** - Production setup guides

---

**Ready to get started?** Run `python execute_full_workflow.py --test` to verify your setup!

*Last updated: November 30, 2025*
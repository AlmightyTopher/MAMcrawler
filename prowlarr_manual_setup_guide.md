# Prowlarr Audiobook Indexer Setup Guide

## Issue Identified
Your Prowlarr installation only has the MyAnonamouse (MAM) indexer configured. While MAM has extensive audiobook categories, searches are returning 0 results. This suggests either:
- MAM indexer configuration issues
- MAM site search limitations
- Need for additional public indexers

## Manual Setup Instructions

### Step 1: Access Prowlarr Web Interface
1. Open your browser and go to: `http://localhost:9696`
2. Log in with your credentials

### Step 2: Add Public Audiobook Indexers

#### Add 1337x Indexer
1. Click **"Indexers"** in the left sidebar
2. Click **"Add Indexer"** (green + button)
3. Search for and select **"1337x"**
4. Configure:
   - **Name**: `1337x`
   - **Enable RSS**: ✅
   - **Enable Automatic Search**: ✅
   - **Enable Interactive Search**: ✅
   - **URL**: `https://1337x.to`
   - **API Path**: `/torznab-api`
   - **API Key**: Leave empty (not required)
   - **Categories**: Select `Books` and `AudioBooks`
   - **Minimum Seeders**: `1`
5. Click **"Test"** to verify connection
6. Click **"Save"**

#### Add RARBG Indexer
1. Click **"Add Indexer"** again
2. Search for and select **"RARBG"**
3. Configure:
   - **Name**: `RARBG`
   - **Enable RSS**: ✅
   - **Enable Automatic Search**: ✅
   - **Enable Interactive Search**: ✅
   - **URL**: `https://rarbg.to`
   - **Categories**: Select `Books` and `AudioBooks`
   - **Minimum Seeders**: `1`
4. Click **"Test"** to verify connection
5. Click **"Save"**

#### Add The Pirate Bay Indexer
1. Click **"Add Indexer"** again
2. Search for and select **"The Pirate Bay"**
3. Configure:
   - **Name**: `The Pirate Bay`
   - **Enable RSS**: ✅
   - **Enable Automatic Search**: ✅
   - **Enable Interactive Search**: ✅
   - **Site URL**: `https://thepiratebay.org`
   - **Categories**: Select `Books` and `AudioBooks`
   - **Minimum Seeders**: `1`
4. Click **"Test"** to verify connection
5. Click **"Save"**

#### Add TorrentDownloads Indexer
1. Click **"Add Indexer"** again
2. Search for and select **"TorrentDownloads"**
3. Configure:
   - **Name**: `TorrentDownloads`
   - **Enable RSS**: ✅
   - **Enable Automatic Search**: ✅
   - **Enable Interactive Search**: ✅
   - **URL**: `https://www.torrentdownloads.me`
   - **API Path**: `/torznab-api`
   - **API Key**: Leave empty (not required)
   - **Categories**: Select `Books` and `AudioBooks`
   - **Minimum Seeders**: `1`
4. Click **"Test"** to verify connection
5. Click **"Save"**

### Step 3: Configure MyAnonamouse for Audiobooks
1. In the **"Indexers"** section, click on **"MyAnonamouse"**
2. Ensure these settings:
   - **Enable RSS**: ✅
   - **Enable Automatic Search**: ✅
   - **Enable Interactive Search**: ✅
3. Click **"Test"** to verify MAM connection
4. Click **"Save"**

### Step 4: Test the Setup
1. Go to **"Search"** in the left sidebar
2. Try searching for: `"The Name of the Wind audiobook"`
3. You should now see results from multiple indexers
4. Try searching for: `"Dune audiobook"`

### Step 5: Run the Automated Download Script
Once indexers are working and returning results:

```bash
venv\Scripts\python.exe search_prowlarr_curated_audiobooks_v2.py
```

## Troubleshooting

### If Indexers Fail Tests
- **Network Issues**: Some indexers may be blocked by your ISP or region
- **VPN Required**: Consider using a VPN for geo-blocked indexers
- **Rate Limiting**: Some indexers have rate limits - wait and retry

### If Still No Results
- Check that audiobook categories are enabled for each indexer
- Try different search terms
- Verify indexer URLs are correct and accessible

### MAM-Specific Issues
- MAM may require specific search syntax
- Check your MAM account has sufficient privileges
- Verify MAM session is still valid

## Alternative: Direct Torrent Search
If Prowlarr setup proves difficult, you can manually search and download from:
- 1337x.to
- thepiratebay.org
- rarbg.to
- torrentdownloads.me

Search for: `"[book title] by [author] audiobook"`

## Next Steps After Setup
1. Run the automated search script
2. Monitor qBittorrent downloads
3. Move completed audiobooks to Audiobookshelf
4. Scan library in Audiobookshelf

This manual setup should resolve the "0 results" issue and enable automated audiobook downloading.
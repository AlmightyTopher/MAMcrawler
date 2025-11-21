# Repository Improvements Implementation Plan

## Overview
This document outlines the specific improvements to be implemented from reviewing the Audiobookshelf and qBittorrent repositories. Each improvement includes exact change details and complete rollback procedures.

## Phase 1: Audiobookshelf Improvements

### 1. Collections Management Enhancement
**Current State**: Basic library operations only
**Target**: Full collections CRUD + book management

**Changes to implement:**
- Add `create_collection()` method to AudiobookshelfClient
- Add `get_collections()` method
- Add `update_collection()` method
- Add `delete_collection()` method
- Add `add_books_to_collection()` method
- Add `remove_books_from_collection()` method
- Add `batch_add_to_collection()` method
- Add `batch_remove_from_collection()` method

**Files to modify:**
- `backend/integrations/abs_client.py` - Add new methods

**Rollback procedure:**
```bash
# Remove the new collection methods from abs_client.py
# Lines to remove: [list exact line numbers after implementation]
git checkout HEAD -- backend/integrations/abs_client.py
```

### 2. Playlists Management Enhancement
**Current State**: No playlist support
**Target**: Full playlist CRUD operations

**Changes to implement:**
- Add `create_playlist()` method
- Add `get_playlists()` method
- Add `update_playlist()` method
- Add `delete_playlist()` method
- Add `add_item_to_playlist()` method
- Add `remove_item_from_playlist()` method
- Add `batch_add_to_playlist()` method
- Add `batch_remove_from_playlist()` method
- Add `create_playlist_from_collection()` method

**Files to modify:**
- `backend/integrations/abs_client.py` - Add playlist methods

**Rollback procedure:**
```bash
# Remove playlist methods from abs_client.py
git checkout HEAD -- backend/integrations/abs_client.py
```

### 3. Progress Tracking Enhancement
**Current State**: No progress tracking
**Target**: Full progress and bookmark management

**Changes to implement:**
- Add `get_media_progress()` method
- Add `update_media_progress()` method
- Add `batch_update_progress()` method
- Add `remove_media_progress()` method
- Add `create_bookmark()` method
- Add `update_bookmark()` method
- Add `remove_bookmark()` method
- Add `get_listening_sessions()` method

**Files to modify:**
- `backend/integrations/abs_client.py` - Add progress methods

**Rollback procedure:**
```bash
# Remove progress tracking methods from abs_client.py
git checkout HEAD -- backend/integrations/abs_client.py
```

### 4. User Management Enhancement
**Current State**: No user management
**Target**: Full user CRUD operations

**Changes to implement:**
- Add `create_user()` method
- Add `get_users()` method
- Add `get_user_by_id()` method
- Add `update_user()` method
- Add `delete_user()` method
- Add `get_online_users()` method
- Add `get_user_listening_sessions()` method
- Add `get_user_listening_stats()` method

**Files to modify:**
- `backend/integrations/abs_client.py` - Add user management methods

**Rollback procedure:**
```bash
# Remove user management methods from abs_client.py
git checkout HEAD -- backend/integrations/abs_client.py
```

### 5. Backup Management Enhancement
**Current State**: No backup support
**Target**: Full backup operations

**Changes to implement:**
- Add `get_backups()` method
- Add `create_backup()` method
- Add `delete_backup()` method
- Add `download_backup()` method
- Add `apply_backup()` method
- Add `upload_backup()` method
- Add `update_backup_path()` method

**Files to modify:**
- `backend/integrations/abs_client.py` - Add backup methods

**Rollback procedure:**
```bash
# Remove backup methods from abs_client.py
git checkout HEAD -- backend/integrations/abs_client.py
```

### 6. RSS Feed Management Enhancement
**Current State**: No RSS support
**Target**: RSS feed operations for items/collections/series

**Changes to implement:**
- Add `get_rss_feeds()` method
- Add `open_rss_feed_for_item()` method
- Add `open_rss_feed_for_collection()` method
- Add `open_rss_feed_for_series()` method
- Add `close_rss_feed()` method

**Files to modify:**
- `backend/integrations/abs_client.py` - Add RSS methods

**Rollback procedure:**
```bash
# Remove RSS methods from abs_client.py
git checkout HEAD -- backend/integrations/abs_client.py
```

### 7. API Key Management Enhancement
**Current State**: No API key management
**Target**: Full API key CRUD

**Changes to implement:**
- Add `get_api_keys()` method
- Add `create_api_key()` method
- Add `update_api_key()` method
- Add `delete_api_key()` method

**Files to modify:**
- `backend/integrations/abs_client.py` - Add API key methods

**Rollback procedure:**
```bash
# Remove API key methods from abs_client.py
git checkout HEAD -- backend/integrations/abs_client.py
```

### 8. Notifications Management Enhancement
**Current State**: No notification support
**Target**: Notification system management

**Changes to implement:**
- Add `get_notifications()` method
- Add `update_notifications()` method
- Add `get_notification_data()` method
- Add `test_notifications()` method
- Add `create_notification()` method
- Add `delete_notification()` method
- Add `update_notification()` method
- Add `test_specific_notification()` method

**Files to modify:**
- `backend/integrations/abs_client.py` - Add notification methods

**Rollback procedure:**
```bash
# Remove notification methods from abs_client.py
git checkout HEAD -- backend/integrations/abs_client.py
```

### 9. Email Management Enhancement
**Current State**: No email support
**Target**: Email settings and e-reader management

**Changes to implement:**
- Add `get_email_settings()` method
- Add `update_email_settings()` method
- Add `test_email()` method
- Add `update_ereader_devices()` method
- Add `send_ebook_to_device()` method

**Files to modify:**
- `backend/integrations/abs_client.py` - Add email methods

**Rollback procedure:**
```bash
# Remove email methods from abs_client.py
git checkout HEAD -- backend/integrations/abs_client.py
```

## Phase 2: qBittorrent Improvements

### 1. RSS Management Enhancement
**Current State**: No RSS support
**Target**: Full RSS feed and auto-download management

**Changes to implement:**
- Add `add_rss_folder()` method
- Add `add_rss_feed()` method
- Add `set_rss_feed_url()` method
- Add `remove_rss_item()` method
- Add `move_rss_item()` method
- Add `get_rss_items()` method
- Add `mark_rss_as_read()` method
- Add `refresh_rss_item()` method
- Add `set_rss_rule()` method
- Add `rename_rss_rule()` method
- Add `remove_rss_rule()` method
- Add `get_rss_rules()` method
- Add `get_matching_articles()` method

**Files to modify:**
- `backend/integrations/qbittorrent_client.py` - Add RSS methods

**Rollback procedure:**
```bash
# Remove RSS methods from qbittorrent_client.py
git checkout HEAD -- backend/integrations/qbittorrent_client.py
```

### 2. Bandwidth Control Enhancement
**Current State**: Basic speed limits
**Target**: Full bandwidth management

**Changes to implement:**
- Add `get_transfer_info()` method (detailed transfer stats)
- Add `get_upload_limit()` method
- Add `get_download_limit()` method
- Add `set_upload_limit()` method
- Add `set_download_limit()` method
- Add `toggle_speed_limits_mode()` method
- Add `get_speed_limits_mode()` method
- Add `set_speed_limits_mode()` method
- Add `ban_peers()` method

**Files to modify:**
- `backend/integrations/qbittorrent_client.py` - Add bandwidth control methods

**Rollback procedure:**
```bash
# Remove bandwidth control methods from qbittorrent_client.py
git checkout HEAD -- backend/integrations/qbittorrent_client.py
```

### 3. Search Functionality Enhancement
**Current State**: No search support
**Target**: Torrent search capabilities

**Changes to implement:**
- Add `search_torrents()` method
- Add `get_search_plugins()` method
- Add `install_search_plugin()` method
- Add `uninstall_search_plugin()` method
- Add `enable_search_plugin()` method
- Add `disable_search_plugin()` method
- Add `update_search_plugins()` method

**Files to modify:**
- `backend/integrations/qbittorrent_client.py` - Add search methods

**Rollback procedure:**
```bash
# Remove search methods from qbittorrent_client.py
git checkout HEAD -- backend/integrations/qbittorrent_client.py
```

## Testing Strategy

### After Each Change:
1. Run existing tests to ensure no regression
2. Test new functionality with mock data
3. Verify API calls work with real server (if available)
4. Check error handling

### Comprehensive Testing:
1. Test all new methods with valid inputs
2. Test error conditions and edge cases
3. Verify backward compatibility
4. Performance testing for new features

## Rollback Strategy

### Complete Rollback:
```bash
# Revert all changes
git checkout HEAD -- backend/integrations/abs_client.py
git checkout HEAD -- backend/integrations/qbittorrent_client.py
```

### Selective Rollback:
Each section above includes specific rollback commands for individual features.

## Success Criteria

### Audiobookshelf:
- All 67 API endpoints from official server are accessible
- Collections, playlists, progress tracking fully functional
- User management, backups, RSS feeds working
- API keys, notifications, email management operational

### qBittorrent:
- RSS feeds and auto-download rules functional
- Bandwidth controls working
- Search functionality operational
- All transfer controls available

## Risk Assessment

### Low Risk:
- Adding new methods without changing existing ones
- Backward compatible changes

### Medium Risk:
- Changes to existing method signatures (avoided)
- New dependencies (none planned)

### High Risk:
- Breaking changes to existing functionality (testing will prevent)

## Timeline

### Phase 1 (Audiobookshelf): 2-3 days
- Day 1: Collections + Playlists
- Day 2: Progress + User Management
- Day 3: Backup + RSS + API Keys + Notifications + Email

### Phase 2 (qBittorrent): 1-2 days
- Day 1: RSS Management
- Day 2: Bandwidth Controls + Search

### Testing: 1 day
- Comprehensive testing of all new features
- Regression testing
- Documentation updates

## Documentation Updates

After implementation:
1. Update `API_DOCUMENTATION.md` with new endpoints
2. Update method docstrings
3. Add examples for new features
4. Update README with new capabilities

## Final Validation

Run comprehensive test suite:
```bash
python -m pytest tests/ -v
python verify_implementation.py
```

All tests must pass before considering implementation complete.
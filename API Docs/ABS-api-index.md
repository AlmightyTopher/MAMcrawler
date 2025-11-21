# Project API Index

## 1. HTTP/REST/RPC Endpoints
`
### Auth Routes (audiobookshelf/server/Auth.js)
- POST /login (line 320) - Local strategy login
- POST /auth/refresh (line 329) - Refresh token
- GET /auth/openid (line 360) - OpenID login redirect
- GET /auth/openid/mobile-redirect (line 378) - Mobile redirect
- GET /auth/openid/callback (line 381) - OpenID callback
- GET /auth/openid/config (line 456) - OpenID config
- POST /logout (line 475) - Logout

### Server Routes (audiobookshelf/server/Server.js)
- GET /feed/:slug (line 326) - RSS Feed
- GET /feed/:slug/cover* (line 330) - RSS Feed cover
- GET /feed/:slug/item/:episodeId/* (line 334) - RSS Feed episode
- POST /init (line 341) - Initialize server
- GET /status (line 348) - Server status
- GET /ping (line 365) - Ping
- GET /healthcheck (line 369) - Health check
- GET / (dynamic routes for SPA) (line 400)

### API Routes (audiobookshelf/server/routers/ApiRouter.js)

#### Libraries
- GET /libraries (line 70) - Get all libraries
- POST /libraries (line 69) - Create library
- GET /libraries/:id (line 71) - Get library by ID
- PATCH /libraries/:id (line 72) - Update library
- DELETE /libraries/:id (line 73) - Delete library
- GET /libraries/:id/items (line 75) - Get library items
- DELETE /libraries/:id/issues (line 76) - Remove items with issues
- GET /libraries/:id/episode-downloads (line 77) - Get episode downloads
- GET /libraries/:id/series (line 78) - Get series
- GET /libraries/:id/series/:seriesId (line 79) - Get series by ID
- GET /libraries/:id/collections (line 80) - Get collections
- GET /libraries/:id/playlists (line 81) - Get playlists
- GET /libraries/:id/personalized (line 82) - Get personalized shelves
- GET /libraries/:id/filterdata (line 83) - Get filter data
- GET /libraries/:id/search (line 84) - Search library
- GET /libraries/:id/stats (line 85) - Get library stats
- GET /libraries/:id/authors (line 86) - Get authors
- GET /libraries/:id/narrators (line 87) - Get narrators
- PATCH /libraries/:id/narrators/:narratorId (line 88) - Update narrator
- DELETE /libraries/:id/narrators/:narratorId (line 89) - Remove narrator
- GET /libraries/:id/matchall (line 90) - Match all
- POST /libraries/:id/scan (line 91) - Scan library
- GET /libraries/:id/recent-episodes (line 92) - Get recent episodes
- GET /libraries/:id/opml (line 93) - Get OPML
- POST /libraries/order (line 94) - Reorder libraries
- POST /libraries/:id/remove-metadata (line 95) - Remove metadata
- GET /libraries/:id/podcast-titles (line 96) - Get podcast titles
- GET /libraries/:id/download (line 97) - Download multiple

#### Items
- POST /items/batch/delete (line 102) - Batch delete items
- POST /items/batch/update (line 103) - Batch update items
- POST /items/batch/get (line 104) - Batch get items
- POST /items/batch/quickmatch (line 105) - Batch quick match
- POST /items/batch/scan (line 106) - Batch scan
- GET /items/:id (line 108) - Get item by ID
- DELETE /items/:id (line 109) - Delete item
- GET /items/:id/download (line 110) - Download item
- PATCH /items/:id/media (line 111) - Update media
- GET /items/:id/cover (line 112) - Get cover
- POST /items/:id/cover (line 113) - Upload cover
- PATCH /items/:id/cover (line 114) - Update cover
- DELETE /items/:id/cover (line 115) - Remove cover
- POST /items/:id/match (line 116) - Match item
- POST /items/:id/play (line 117) - Start playback session
- POST /items/:id/play/:episodeId (line 118) - Start episode playback
- PATCH /items/:id/tracks (line 119) - Update tracks
- POST /items/:id/scan (line 120) - Scan item
- GET /items/:id/metadata-object (line 121) - Get metadata object
- POST /items/:id/chapters (line 122) - Update chapters
- GET /items/:id/ffprobe/:fileid (line 123) - Get FFprobe data
- GET /items/:id/file/:fileid (line 124) - Get library file
- DELETE /items/:id/file/:fileid (line 125) - Delete library file
- GET /items/:id/file/:fileid/download (line 126) - Download library file
- GET /items/:id/ebook/:fileid? (line 127) - Get ebook file
- PATCH /items/:id/ebook/:fileid/status (line 128) - Update ebook status

#### Users
- POST /users (line 133) - Create user
- GET /users (line 134) - Get all users
- GET /users/online (line 135) - Get online users
- GET /users/:id (line 136) - Get user by ID
- PATCH /users/:id (line 137) - Update user
- DELETE /users/:id (line 138) - Delete user
- PATCH /users/:id/openid-unlink (line 139) - Unlink OpenID
- GET /users/:id/listening-sessions (line 140) - Get listening sessions
- GET /users/:id/listening-stats (line 141) - Get listening stats

#### Collections
- POST /collections (line 146) - Create collection
- GET /collections (line 147) - Get all collections
- GET /collections/:id (line 148) - Get collection by ID
- PATCH /collections/:id (line 149) - Update collection
- DELETE /collections/:id (line 150) - Delete collection
- POST /collections/:id/book (line 151) - Add book to collection
- DELETE /collections/:id/book/:bookId (line 152) - Remove book from collection
- POST /collections/:id/batch/add (line 153) - Batch add
- POST /collections/:id/batch/remove (line 154) - Batch remove

#### Playlists
- POST /playlists (line 159) - Create playlist
- GET /playlists (line 160) - Get user playlists
- GET /playlists/:id (line 161) - Get playlist by ID
- PATCH /playlists/:id (line 162) - Update playlist
- DELETE /playlists/:id (line 163) - Delete playlist
- POST /playlists/:id/item (line 164) - Add item to playlist
- DELETE /playlists/:id/item/:libraryItemId/:episodeId? (line 165) - Remove item from playlist
- POST /playlists/:id/batch/add (line 166) - Batch add items
- POST /playlists/:id/batch/remove (line 167) - Batch remove items
- POST /playlists/collection/:collectionId (line 168) - Create from collection

#### Me (Current User)
- GET /me (line 173) - Get current user
- GET /me/listening-sessions (line 174) - Get listening sessions
- GET /me/item/listening-sessions/:libraryItemId/:episodeId? (line 175) - Get item listening sessions
- GET /me/listening-stats (line 176) - Get listening stats
- GET /me/progress/:id/remove-from-continue-listening (line 177) - Remove from continue listening
- GET /me/progress/:id/:episodeId? (line 178) - Get media progress
- PATCH /me/progress/batch/update (line 179) - Batch update progress
- PATCH /me/progress/:libraryItemId/:episodeId? (line 180) - Update progress
- DELETE /me/progress/:id (line 181) - Remove progress
- POST /me/item/:id/bookmark (line 182) - Create bookmark
- PATCH /me/item/:id/bookmark (line 183) - Update bookmark
- DELETE /me/item/:id/bookmark/:time (line 184) - Remove bookmark
- PATCH /me/password (line 185) - Update password
- GET /me/items-in-progress (line 186) - Get items in progress
- GET /me/series/:id/remove-from-continue-listening (line 187) - Remove series from continue
- GET /me/series/:id/readd-to-continue-listening (line 188) - Readd series to continue
- GET /me/stats/year/:year (line 189) - Get stats for year
- POST /me/ereader-devices (line 190) - Update ereader devices

#### Backups
- GET /backups (line 195) - Get all backups
- POST /backups (line 196) - Create backup
- DELETE /backups/:id (line 197) - Delete backup
- GET /backups/:id/download (line 198) - Download backup
- GET /backups/:id/apply (line 199) - Apply backup
- POST /backups/upload (line 200) - Upload backup
- PATCH /backups/path (line 201) - Update backup path

#### File System
- GET /filesystem (line 206) - Get paths
- POST /filesystem/pathexists (line 207) - Check path exists

#### Authors
- GET /authors/:id (line 212) - Get author by ID
- PATCH /authors/:id (line 213) - Update author
- DELETE /authors/:id (line 214) - Delete author
- POST /authors/:id/match (line 215) - Match author
- GET /authors/:id/image (line 216) - Get author image
- POST /authors/:id/image (line 217) - Upload author image
- DELETE /authors/:id/image (line 218) - Delete author image

#### Series
- GET /series/:id (line 223) - Get series by ID
- PATCH /series/:id (line 224) - Update series

#### Sessions
- GET /sessions (line 229) - Get all sessions
- DELETE /sessions/:id (line 230) - Delete session
- GET /sessions/open (line 231) - Get open sessions
- POST /sessions/batch/delete (line 232) - Batch delete sessions
- POST /session/local (line 233) - Sync local
- POST /session/local-all (line 234) - Sync local sessions
- GET /session/:id (line 236) - Get open session
- POST /session/:id/sync (line 237) - Sync session
- POST /session/:id/close (line 238) - Close session

#### Podcasts
- POST /podcasts (line 243) - Create podcast
- POST /podcasts/feed (line 244) - Get podcast feed
- POST /podcasts/opml/parse (line 245) - Parse OPML
- POST /podcasts/opml/create (line 246) - Create from OPML
- GET /podcasts/:id/checknew (line 247) - Check new episodes
- GET /podcasts/:id/downloads (line 248) - Get episode downloads
- GET /podcasts/:id/clear-queue (line 249) - Clear download queue
- GET /podcasts/:id/search-episode (line 250) - Search episode
- POST /podcasts/:id/download-episodes (line 251) - Download episodes
- POST /podcasts/:id/match-episodes (line 252) - Match episodes
- GET /podcasts/:id/episode/:episodeId (line 253) - Get episode
- PATCH /podcasts/:id/episode/:episodeId (line 254) - Update episode
- DELETE /podcasts/:id/episode/:episodeId (line 255) - Remove episode

#### Notifications
- GET /notifications (line 260) - Get notifications
- PATCH /notifications (line 261) - Update notifications
- GET /notificationdata (line 262) - Get notification data
- GET /notifications/test (line 263) - Fire test event
- POST /notifications (line 264) - Create notification
- DELETE /notifications/:id (line 265) - Delete notification
- PATCH /notifications/:id (line 266) - Update notification
- GET /notifications/:id/test (line 267) - Send notification test

#### Emails
- GET /emails/settings (line 272) - Get email settings
- PATCH /emails/settings (line 273) - Update email settings
- POST /emails/test (line 274) - Send test email
- POST /emails/ereader-devices (line 275) - Update ereader devices
- POST /emails/send-ebook-to-device (line 276) - Send ebook to device

#### Search
- GET /search/covers (line 281) - Search covers
- GET /search/books (line 282) - Search books
- GET /search/podcast (line 283) - Search podcasts
- GET /search/authors (line 284) - Search authors
- GET /search/chapters (line 285) - Search chapters
- GET /search/providers (line 286) - Get all providers

#### Cache
- POST /cache/purge (line 291) - Purge cache
- POST /cache/items/purge (line 292) - Purge items cache

#### Tools
- POST /tools/item/:id/encode-m4b (line 297) - Encode M4B
- DELETE /tools/item/:id/encode-m4b (line 298) - Cancel M4B encode
- POST /tools/item/:id/embed-metadata (line 299) - Embed metadata
- POST /tools/batch/embed-metadata (line 300) - Batch embed metadata

#### RSS Feeds
- GET /feeds (line 305) - Get all feeds
- POST /feeds/item/:itemId/open (line 306) - Open RSS feed for item
- POST /feeds/collection/:collectionId/open (line 307) - Open RSS feed for collection
- POST /feeds/series/:seriesId/open (line 308) - Open RSS feed for series
- POST /feeds/:id/close (line 309) - Close RSS feed

#### Custom Metadata Providers
- GET /custom-metadata-providers (line 314) - Get all providers
- POST /custom-metadata-providers (line 315) - Create provider
- DELETE /custom-metadata-providers/:id (line 316) - Delete provider

#### Share
- POST /share/mediaitem (line 321) - Create media item share
- DELETE /share/mediaitem/:id (line 322) - Delete media item share

#### Stats
- GET /stats/year/:year (line 327) - Get admin stats for year
- GET /stats/server (line 328) - Get server stats

#### API Keys
- GET /api-keys (line 333) - Get all API keys
- POST /api-keys (line 334) - Create API key
- PATCH /api-keys/:id (line 335) - Update API key
- DELETE /api-keys/:id (line 336) - Delete API key

#### Misc
- POST /upload (line 341) - Handle upload
- GET /tasks (line 342) - Get tasks
- PATCH /settings (line 343) - Update server settings
- PATCH /sorting-prefixes (line 344) - Update sorting prefixes
- POST /authorize (line 345) - Authorize
- GET /tags (line 346) - Get all tags
- POST /tags/rename (line 347) - Rename tag
- DELETE /tags/:tag (line 348) - Delete tag
- GET /genres (line 349) - Get all genres
- POST /genres/rename (line 350) - Rename genre
- DELETE /genres/:genre (line 351) - Delete genre
- POST /validate-cron (line 352) - Validate cron expression
- GET /auth-settings (line 353) - Get auth settings
- PATCH /auth-settings (line 354) - Update auth settings
- POST /watcher/update (line 355) - Update watched path
- GET /logger-data (line 356) - Get logger data

### Public Routes (audiobookshelf/server/routers/PublicRouter.js)
- GET /share/:slug (line 16) - Get media item share
- GET /share/:slug/track/:index (line 17) - Get media item share audio track
- GET /share/:slug/cover (line 18) - Get media item share cover
- GET /share/:slug/download (line 19) - Download media item share
- PATCH /share/:slug/progress (line 20) - Update media item share progress
- GET /session/:id/track/:index (line 21) - Get track

### HLS Routes (audiobookshelf/server/routers/HlsRouter.js)
- GET /:stream/:file (line 21) - Stream file

## 2. Internal Module Interfaces

### Managers
- CacheManager (audiobookshelf/server/managers/CacheManager.js)
- RssFeedManager (audiobookshelf/server/managers/RssFeedManager.js)
- PlaybackSessionManager (audiobookshelf/server/managers/PlaybackSessionManager.js)
- AbMergeManager (audiobookshelf/server/managers/AbMergeManager.js)
- BackupManager (audiobookshelf/server/managers/BackupManager.js)
- PodcastManager (audiobookshelf/server/managers/PodcastManager.js)
- AudioMetadataManager (audiobookshelf/server/managers/AudioMetadataManager.js)
- CronManager (audiobookshelf/server/managers/CronManager.js)
- EmailManager (audiobookshelf/server/managers/EmailManager.js)
- CoverSearchManager (audiobookshelf/server/managers/CoverSearchManager.js)
- CoverManager (audiobookshelf/server/managers/CoverManager.js)
- BinaryManager (audiobookshelf/server/managers/BinaryManager.js)
- MigrationManager (audiobookshelf/server/managers/MigrationManager.js)
- LogManager (audiobookshelf/server/managers/LogManager.js)
- TaskManager (audiobookshelf/server/managers/TaskManager.js)
- ShareManager (audiobookshelf/server/managers/ShareManager.js)
- NotificationManager (audiobookshelf/server/managers/NotificationManager.js)
- ApiCacheManager (audiobookshelf/server/managers/ApiCacheManager.js)

### Controllers
- LibraryController (audiobookshelf/server/controllers/LibraryController.js)
- UserController (audiobookshelf/server/controllers/UserController.js)
- CollectionController (audiobookshelf/server/controllers/CollectionController.js)
- PlaylistController (audiobookshelf/server/controllers/PlaylistController.js)
- MeController (audiobookshelf/server/controllers/MeController.js)
- BackupController (audiobookshelf/server/controllers/BackupController.js)
- LibraryItemController (audiobookshelf/server/controllers/LibraryItemController.js)
- SeriesController (audiobookshelf/server/controllers/SeriesController.js)
- FileSystemController (audiobookshelf/server/controllers/FileSystemController.js)
- AuthorController (audiobookshelf/server/controllers/AuthorController.js)
- SessionController (audiobookshelf/server/controllers/SessionController.js)
- PodcastController (audiobookshelf/server/controllers/PodcastController.js)
- NotificationController (audiobookshelf/server/controllers/NotificationController.js)
- EmailController (audiobookshelf/server/controllers/EmailController.js)
- SearchController (audiobookshelf/server/controllers/SearchController.js)
- CacheController (audiobookshelf/server/controllers/CacheController.js)
- ToolsController (audiobookshelf/server/controllers/ToolsController.js)
- RSSFeedController (audiobookshelf/server/controllers/RSSFeedController.js)
- CustomMetadataProviderController (audiobookshelf/server/controllers/CustomMetadataProviderController.js)
- MiscController (audiobookshelf/server/controllers/MiscController.js)
- ShareController (audiobookshelf/server/controllers/ShareController.js)
- StatsController (audiobookshelf/server/controllers/StatsController.js)
- ApiKeyController (audiobookshelf/server/controllers/ApiKeyController.js)

### Models
- User (audiobookshelf/server/models/User.js)
- Setting (audiobookshelf/server/models/Setting.js)
- Session (audiobookshelf/server/models/Session.js)
- Series (audiobookshelf/server/models/Series.js)
- PodcastEpisode (audiobookshelf/server/models/PodcastEpisode.js)
- Podcast (audiobookshelf/server/models/Podcast.js)
- PlaylistMediaItem (audiobookshelf/server/models/PlaylistMediaItem.js)
- Playlist (audiobookshelf/server/models/Playlist.js)
- PlaybackSession (audiobookshelf/server/models/PlaybackSession.js)
- MediaProgress (audiobookshelf/server/models/MediaProgress.js)
- MediaItemShare (audiobookshelf/server/models/MediaItemShare.js)
- LibraryItem (audiobookshelf/server/models/LibraryItem.js)
- LibraryFolder (audiobookshelf/server/models/LibraryFolder.js)
- Library (audiobookshelf/server/models/Library.js)
- FeedEpisode (audiobookshelf/server/models/FeedEpisode.js)
- Feed (audiobookshelf/server/models/Feed.js)
- Device (audiobookshelf/server/models/Device.js)
- CustomMetadataProvider (audiobookshelf/server/models/CustomMetadataProvider.js)
- CollectionBook (audiobookshelf/server/models/CollectionBook.js)
- Collection (audiobookshelf/server/models/Collection.js)
- BookSeries (audiobookshelf/server/models/BookSeries.js)
- BookAuthor (audiobookshelf/server/models/BookAuthor.js)
- Book (audiobookshelf/server/models/Book.js)
- Author (audiobookshelf/server/models/Author.js)
- ApiKey (audiobookshelf/server/models/ApiKey.js)

### Objects
- Backup (audiobookshelf/server/objects/Backup.js)
- DailyLog (audiobookshelf/server/objects/DailyLog.js)
- DeviceInfo (audiobookshelf/server/objects/DeviceInfo.js)
- Notification (audiobookshelf/server/objects/Notification.js)
- PlaybackSession (audiobookshelf/server/objects/PlaybackSession.js)
- PodcastEpisodeDownload (audiobookshelf/server/objects/PodcastEpisodeDownload.js)
- Stream (audiobookshelf/server/objects/Stream.js)
- Task (audiobookshelf/server/objects/Task.js)
- TrackProgressMonitor (audiobookshelf/server/objects/TrackProgressMonitor.js)
- AudioFile (audiobookshelf/server/objects/files/AudioFile.js)
- AudioTrack (audiobookshelf/server/objects/files/AudioTrack.js)
- EBookFile (audiobookshelf/server/objects/files/EBookFile.js)
- LibraryFile (audiobookshelf/server/objects/files/LibraryFile.js)
- AudioMetaTags (audiobookshelf/server/objects/metadata/AudioMetaTags.js)
- FileMetadata (audiobookshelf/server/objects/metadata/FileMetadata.js)
- EmailSettings (audiobookshelf/server/objects/settings/EmailSettings.js)
- NotificationSettings (audiobookshelf/server/objects/settings/NotificationSettings.js)
- ServerSettings (audiobookshelf/server/objects/settings/ServerSettings.js)

### Utils
- zipDirectoryPipe (audiobookshelf/server/utils/zipHelpers.js)
- zipDirectoriesPipe (audiobookshelf/server/utils/zipHelpers.js)
- handleDownloadError (audiobookshelf/server/utils/zipHelpers.js)
- stringifySequelizeQuery (audiobookshelf/server/utils/stringifySequelizeQuery.js)
- checkFilepathIsAudioFile (audiobookshelf/server/utils/scandir.js)
- groupFileItemsIntoLibraryItemDirs (audiobookshelf/server/utils/scandir.js)
- buildLibraryFile (audiobookshelf/server/utils/scandir.js)
- getBookDataFromDir (audiobookshelf/server/utils/scandir.js)
- getDataFromMediaDir (audiobookshelf/server/utils/scandir.js)
- new RateLimiterFactory() (audiobookshelf/server/utils/rateLimiterFactory.js)
- parsePodcastRssFeedXml (audiobookshelf/server/utils/podcastUtils.js)
- getPodcastFeed (audiobookshelf/server/utils/podcastUtils.js)
- findMatchingEpisodes (audiobookshelf/server/utils/podcastUtils.js)
- findMatchingEpisodesInFeed (audiobookshelf/server/utils/podcastUtils.js)
- profile (audiobookshelf/server/utils/profiler.js)
- probe (audiobookshelf/server/utils/prober.js)
- rawProbe (audiobookshelf/server/utils/prober.js)
- parseSeriesString (audiobookshelf/server/utils/parsers/parseSeriesString.js)
- parseOverdriveMediaMarkersAsChapters (audiobookshelf/server/utils/parsers/parseOverdriveMediaMarkers.js)
- parseOpfMetadataJson (audiobookshelf/server/utils/parsers/parseOpfMetadata.js)
- parseOpfMetadataXML (audiobookshelf/server/utils/parsers/parseOpfMetadata.js)
- parseNfoMetadata (audiobookshelf/server/utils/parsers/parseNfoMetadata.js)
- nameToLastFirst (audiobookshelf/server/utils/parsers/parseNameString.js)
- parse (audiobookshelf/server/utils/parsers/parseNameString.js)
- parseFullName (audiobookshelf/server/utils/parsers/parseFullName.js)
- extractCoverImage (audiobookshelf/server/utils/parsers/parseEpubMetadata.js)
- parse (audiobookshelf/server/utils/parsers/parseEpubMetadata.js)
- parse (audiobookshelf/server/utils/parsers/parseEbookMetadata.js)
- extractCoverImage (audiobookshelf/server/utils/parsers/parseEbookMetadata.js)
- extractCoverImage (audiobookshelf/server/utils/parsers/parseComicMetadata.js)
- parse (audiobookshelf/server/utils/parsers/parseComicMetadata.js)
- parse (audiobookshelf/server/utils/parsers/parseComicInfoMetadata.js)
- notificationData (audiobookshelf/server/utils/notifications.js)
- loadOldData (audiobookshelf/server/utils/migrations/oldDbFiles.js)
- zipWrapOldDb (audiobookshelf/server/utils/migrations/oldDbFiles.js)
- checkHasOldDb (audiobookshelf/server/utils/migrations/oldDbFiles.js)
- checkHasOldDbZip (audiobookshelf/server/utils/migrations/oldDbFiles.js)
- checkExtractItemsUsersAndLibraries (audiobookshelf/server/utils/migrations/oldDbFiles.js)
- removeOldItemsUsersAndLibrariesFolders (audiobookshelf/server/utils/migrations/oldDbFiles.js)
- migrate (audiobookshelf/server/utils/migrations/dbMigration.js)
- checkShouldMigrate (audiobookshelf/server/utils/migrations/dbMigration.js)
- migrationPatch (audiobookshelf/server/utils/migrations/dbMigration.js)
- migrationPatch2 (audiobookshelf/server/utils/migrations/dbMigration.js)
- LongTimeout (audiobookshelf/server/utils/longTimeout.js)
- globals (audiobookshelf/server/utils/globals.js)
- generate (audiobookshelf/server/utils/generators/opmlGenerator.js)
- generatePlaylist (audiobookshelf/server/utils/generators/hlsPlaylistGenerator.js)
- parseJson (audiobookshelf/server/utils/generators/abmetadataGenerator.js)
- levenshteinDistance (audiobookshelf/server/utils/index.js)
- levenshteinSimilarity (audiobookshelf/server/utils/index.js)
- isObject (audiobookshelf/server/utils/index.js)
- comparePaths (audiobookshelf/server/utils/index.js)
- isNullOrNaN (audiobookshelf/server/utils/index.js)
- xmlToJSON (audiobookshelf/server/utils/index.js)
- getId (audiobookshelf/server/utils/index.js)
- elapsedPretty (audiobookshelf/server/utils/index.js)
- secondsToTimestamp (audiobookshelf/server/utils/index.js)
- reqSupportsWebp (audiobookshelf/server/utils/index.js)
- areEquivalent (audiobookshelf/server/utils/index.js)
- copyValue (audiobookshelf/server/utils/index.js)
- toNumber (audiobookshelf/server/utils/index.js)
- cleanStringForSearch (audiobookshelf/server/utils/index.js)
- getTitleIgnorePrefix (audiobookshelf/server/utils/index.js)
- getTitlePrefixAtEnd (audiobookshelf/server/utils/index.js)
- escapeRegExp (audiobookshelf/server/utils/index.js)
- validateUrl (audiobookshelf/server/utils/index.js)
- isUUID (audiobookshelf/server/utils/index.js)
- isValidASIN (audiobookshelf/server/utils/index.js)
- timestampToSeconds (audiobookshelf/server/utils/index.js)
- ValidationError (audiobookshelf/server/utils/index.js)
- NotFoundError (audiobookshelf/server/utils/index.js)
- getQueryParamAsString (audiobookshelf/server/utils/index.js)
- filePathToPOSIX (audiobookshelf/server/utils/fileUtils.js)
- isSameOrSubPath (audiobookshelf/server/utils/fileUtils.js)
- getFileTimestampsWithIno (audiobookshelf/server/utils/fileUtils.js)
- getFileSize (audiobookshelf/server/utils/fileUtils.js)
- getFileMTimeMs (audiobookshelf/server/utils/fileUtils.js)
- checkPathIsFile (audiobookshelf/server/utils/fileUtils.js)
- getIno (audiobookshelf/server/utils/fileUtils.js)
- readTextFile (audiobookshelf/server/utils/fileUtils.js)
- shouldIgnoreFile (audiobookshelf/server/utils/fileUtils.js)
- recurseFiles (audiobookshelf/server/utils/fileUtils.js)
- getFilePathItemFromFileUpdate (audiobookshelf/server/utils/fileUtils.js)
- downloadFile (audiobookshelf/server/utils/fileUtils.js)
- downloadImageFile (audiobookshelf/server/utils/fileUtils.js)
- sanitizeFilename (audiobookshelf/server/utils/fileUtils.js)
- getAudioMimeTypeFromExtname (audiobookshelf/server/utils/fileUtils.js)
- removeFile (audiobookshelf/server/utils/fileUtils.js)
- encodeUriPath (audiobookshelf/server/utils/fileUtils.js)
- isWritable (audiobookshelf/server/utils/fileUtils.js)
- getWindowsDrives (audiobookshelf/server/utils/fileUtils.js)
- getDirectoriesInPath (audiobookshelf/server/utils/fileUtils.js)
- copyToExisting (audiobookshelf/server/utils/fileUtils.js)
- ffmpegHelpers (audiobookshelf/server/utils/ffmpegHelpers.js)
- ScanResult (audiobookshelf/server/utils/constants.js)
- BookCoverAspectRatio (audiobookshelf/server/utils/constants.js)
- BookshelfView (audiobookshelf/server/utils/constants.js)
- LogLevel (audiobookshelf/server/utils/constants.js)
- PlayMethod (audiobookshelf/server/utils/constants.js)
- AudioMimeType (audiobookshelf/server/utils/constants.js)
- createComicBookExtractor (audiobookshelf/server/utils/comicBookExtractors.js)
- areEquivalent (audiobookshelf/server/utils/areEquivalent.js)
- htmlSanitizer (audiobookshelf/server/utils/htmlSanitizer.js)
- entities (audiobookshelf/server/utils/htmlEntities.js)
- libraryHelpers (audiobookshelf/server/utils/libraryHelpers.js)

### Scanners
- new FolderWatcher() (audiobookshelf/server/Watcher.js)
- new Scanner() (audiobookshelf/server/scanner/Scanner.js)
- ScanLogger (audiobookshelf/server/scanner/ScanLogger.js)
- new PodcastScanner() (audiobookshelf/server/scanner/PodcastScanner.js)
- new OpfFileScanner() (audiobookshelf/server/scanner/OpfFileScanner.js)
- new NfoFileScanner() (audiobookshelf/server/scanner/NfoFileScanner.js)
- MediaProbeData (audiobookshelf/server/scanner/MediaProbeData.js)
- new LibraryScanner() (audiobookshelf/server/scanner/LibraryScanner.js)
- LibraryScan (audiobookshelf/server/scanner/LibraryScan.js)
- new LibraryItemScanner() (audiobookshelf/server/scanner/LibraryItemScanner.js)
- LibraryItemScanData (audiobookshelf/server/scanner/LibraryItemScanData.js)
- new BookScanner() (audiobookshelf/server/scanner/BookScanner.js)
- new AudioFileScanner() (audiobookshelf/server/scanner/AudioFileScanner.js)
- new AbsMetadataFileScanner() (audiobookshelf/server/scanner/AbsMetadataFileScanner.js)

### Providers
- OpenLibrary (audiobookshelf/server/providers/OpenLibrary.js)
- MusicBrainz (audiobookshelf/server/providers/MusicBrainz.js)
- iTunes (audiobookshelf/server/providers/iTunes.js)
- GoogleBooks (audiobookshelf/server/providers/GoogleBooks.js)
- FantLab (audiobookshelf/server/providers/FantLab.js)
- CustomProviderAdapter (audiobookshelf/server/providers/CustomProviderAdapter.js)
- Audnexus (audiobookshelf/server/providers/Audnexus.js)
- AudiobookCovers (audiobookshelf/server/providers/AudiobookCovers.js)
- Audible (audiobookshelf/server/providers/Audible.js)

### Finders
- new PodcastFinder() (audiobookshelf/server/finders/PodcastFinder.js)

## 3. CLI Access Points

- config (-c) String: Config file path
- metadata (-m) String: Metadata file path
- port (-p) String: Server port
- host (-h) String: Server host
- source (-s) String: Source type
- dev (-d) Boolean: Run in development mode
- prod-with-dev-env (-r) Boolean: Run in production with dev env

## 4. Event System

### Socket Events (audiobookshelf/server/SocketAuthority.js)
- pong (line 233)
- auth_failed (line 258, 265, 270)
- init (line 305)
- log (audiobookshelf/server/Logger.js line 85)
- item_removed (audiobookshelf/server/ApiRouter.js line 397)
- series_removed (audiobookshelf/server/ApiRouter.js line 446)
- author_removed (audiobookshelf/server/ApiRouter.js line 509)
- cover_search_error (line 322, 333, 370)
- cover_search_result (line 344)
- cover_search_complete (line 355)
- cover_search_provider_error (line 360)
- cover_search_cancelled (line 393)

### Watcher Events (audiobookshelf/server/Watcher.js)
- scanFilesChanged (line 336)

### Stream Events (audiobookshelf/server/objects/Stream.js)
- closed (line 378)

## 5. External Integrations

- Axios for HTTP requests (package.json)
- Nodemailer for email (package.json)
- OpenID Client for auth (package.json)
- Sequelize for database (package.json)
- Socket.io for websockets (package.json)
- SQLite3 for database (package.json)
- XML2JS for XML parsing (package.json)
- FFmpeg for media processing (binary)
- Audible API (audiobookshelf/server/providers/Audible.js)
- Google Books API (audiobookshelf/server/providers/GoogleBooks.js)
- Open Library API (audiobookshelf/server/providers/OpenLibrary.js)
- MusicBrainz API (audiobookshelf/server/providers/MusicBrainz.js)
- iTunes API (audiobookshelf/server/providers/iTunes.js)
- Audnexus API (audiobookshelf/server/providers/Audnexus.js)
- FantLab API (audiobookshelf/server/providers/FantLab.js)
- Audiobook Covers API (audiobookshelf/server/providers/AudiobookCovers.js)

## 6. Config-Defined Interfaces

- Server settings (audiobookshelf/server/objects/settings/ServerSettings.js)
- Email settings (audiobookshelf/server/objects/settings/EmailSettings.js)
- Notification settings (audiobookshelf/server/objects/settings/NotificationSettings.js)
- Auth settings (audiobookshelf/server/controllers/MiscController.js getAuthSettings, updateAuthSettings)
- Sorting prefixes (audiobookshelf/server/controllers/MiscController.js updateSortingPrefixes)
- Watched paths (audiobookshelf/server/controllers/MiscController.js updateWatchedPath)

## 7. Auth Flows and Tokens

- Local passport strategy (audiobookshelf/server/Auth.js)
- JWT tokens (package.json passport-jwt)
- Refresh tokens (audiobookshelf/server/Auth.js)
- OpenID Connect (audiobookshelf/server/Auth.js)
- API keys (audiobookshelf/server/models/ApiKey.js)

## 8. Database Access Interfaces

- Sequelize models (audiobookshelf/server/models/)
- Database connection (audiobookshelf/server/Database.js)
- Query helpers (audiobookshelf/server/utils/queries/)

## 9. File System Interfaces

- File operations (audiobookshelf/server/utils/fileUtils.js)
- Directory scanning (audiobookshelf/server/utils/scandir.js)
- Archive handling (audiobookshelf/server/libs/libarchive/)
- Watcher for file changes (audiobookshelf/server/Watcher.js)
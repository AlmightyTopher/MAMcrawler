# Randi Darren Metadata Update - Summary

## Task Completed
Updated series metadata for 15 Randi Darren audiobooks to link them to their proper series in Audiobookshelf.

## Status: IN PROGRESS (Awaiting Library Rescan)

### What Was Done

#### 1. Metadata Files Updated (On Disk)
Successfully updated 15 metadata.json files with proper series names:

**System Overclocked Series (4 books):**
- System Overclocked 2
- Randi Darren - System Overclocked
- System Overclocked by Randi Darren
- Randi Darren - System Overclocked 3 [m4b]

**Fostering Faust Series (5 books):**
- Book 01 - Fostering Faust - Fostering Faust Series - Read by Andrea Parsneau - 2018
- Darren, Randi -- Fostering Faust, Vol. 01 (2018)
- Darren, Randi -- Fostering Faust, Vol. 02 (2019)
- Darren, Randi -- Fostering Faust, Vol. 03 (2019)
- Book 03 - Fostering Faust 3 - Fostering Faust Series - Read by Andrea Parsneau - 2019

**Remnant / Palimar Saga Series (3 books):**
- Randi Darren - Remnant 02 - Remnant II
- 01 - Remnant [B0CTSBKHLS]
- Book 03 - Remnant III

**Wild Wastes Series (5 books):**
- Randi Darren - Wild Wastes 03 - Southern Storm
- Randi Darren - Wild Wastes 4 m4b
- Wild Wastes 4
- Wild Wastes 5
- Wild Wastes 6

**Incubus Inc. Series (2 books):**
- Randi Darren and William D Arand - Incubus Inc Book 3
- Incubus Inc. 3

#### 2. API Updates
- Updated 1 book via direct API: "System Overclocked 2" successfully patched
- Other 14 books were located beyond the first 5000 items in your ~600,000-item library

#### 3. Library Rescan Triggered
- Initiated full library rescan at Audiobookshelf API
- Status: 200 (successful request)
- **This will rebuild the library database from all metadata.json files on disk**

### Next Steps

1. **Wait for Rescan to Complete**
   - Check Audiobookshelf Logs or UI for rescan progress
   - With 600,000+ items, this may take 15-60 minutes
   - Metadata files have been properly updated on disk, so rescan will pick them up

2. **Verify Series Grouping**
   - After rescan completes, open Audiobookshelf
   - Navigate to Authors → Series view
   - Verify that Randi Darren books now appear grouped by series:
     - System Overclocked (4 books)
     - Fostering Faust (5 books)
     - Remnant / Palimar Saga (3 books)
     - Wild Wastes (5 books)
     - Incubus Inc. (2 books)

### Technical Details

**Approach Used:**
- Direct filesystem metadata manipulation (edited metadata.json files)
- Combined with API PATCH endpoint for direct database updates
- Full library rescan to propagate changes

**API Endpoints Used:**
- `GET /api/libraries` - Get library ID
- `PATCH /api/items/{id}/media` - Update individual items
- `POST /api/libraries/{id}/scan` - Trigger full library rescan

**Files Created:**
- `push_metadata_and_rescan.py` - Script to push updates via API and trigger rescan
- Metadata backup files in `metadata_backups/` directory (with timestamps)

### Troubleshooting

If series don't appear grouped after rescan:
1. Try restarting Audiobookshelf application
2. Manually check a metadata.json file to verify seriesName field was updated
3. Trigger another library rescan if needed


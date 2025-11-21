# Phase 1 Download Plan - Execution Ready

**Status:** READY TO START
**Date:** November 21, 2025
**Phase Duration:** 1-2 weeks
**Total Books:** 42

---

## Phase 1 Overview

Phase 1 focuses on the **3 highest-priority series** with the most impact:

| Priority | Series | Missing | Current | Target |
|----------|--------|---------|---------|--------|
| 1 | Terry Pratchett - Discworld | 21 | 9/30 | 30/30 |
| 2 | Eric Ugland - The Good Guys | 11 | 4/15 | 15/15 |
| 3 | Aleron Kong - The Land | 10 | 0/10 | 10/10 |
| **TOTAL** | | **42** | **13/55** | **55/55** |

**Impact:** Completing Phase 1 will get you 3 complete series and increase overall completion from 40% to ~60%.

---

## Before You Start

### 1. Verify Access
- [ ] You can access MyAnonamouse.net (MAM)
- [ ] Prowlarr is working (or alternative torrent method)
- [ ] qBittorrent is running
- [ ] Audiobookshelf is accessible

### 2. Review Preferences
- [ ] Preferred narrator for Discworld (usually Stephen Briggs or Tony Robinson)
- [ ] Preferred bitrate (64k, 128k, or higher)
- [ ] Preferred format (M4B is best for Audiobookshelf)

### 3. Check Storage
- [ ] At least 30-50 GB free space for Phase 1 downloads
- [ ] qBittorrent configured with proper download folder

### 4. Set Expectations
- [ ] Not all books may be available on MAM immediately
- [ ] You may need to wait for seeders
- [ ] Quality varies - prioritize consistency with existing books
- [ ] Seeding time depends on ratio management

---

## Phase 1 Execution Strategy

### Week 1: Scout and Start

**Monday-Tuesday:**
1. Search for Priority 1 books (Discworld 3-8)
2. Download first 5 books to test workflow
3. Monitor downloads in qBittorrent
4. Verify they appear in Audiobookshelf

**Wednesday-Thursday:**
1. Continue Discworld (books 9-15)
2. Start scouting Eric Ugland - The Good Guys
3. Check qBittorrent ratio and adjust uploads

**Friday:**
1. Finish Discworld books 16-21
2. Start downloading The Good Guys books 1-5
3. Begin The Land series research

### Week 2: Complete Priority 1-3

**Monday-Tuesday:**
1. Complete The Good Guys (books 1-11)
2. Continue The Land books
3. Monitor ratio management

**Wednesday-Thursday:**
1. Complete The Land series (all 10 books)
2. Verify all downloads in Audiobookshelf
3. Check metadata accuracy

**Friday:**
1. Final verification of Phase 1
2. Re-run library analysis
3. Prepare for Phase 2

---

## Detailed Search Queries

### PRIORITY 1: Terry Pratchett - Discworld (21 books)

**Initial batch (Books 3-8):**
```
Terry Pratchett Equal Rites (Book 3)
Terry Pratchett Mort (Book 4)
Terry Pratchett Sourcery (Book 5)
Terry Pratchett Wyrd Sisters (Book 6)
Terry Pratchett Eric (Book 8)
Terry Pratchett Small Gods (Book 9)
```

**Narrator Tips:**
- Prefer Stephen Briggs narration (most consistent)
- Tony Robinson also good alternative
- Some special editions may have different narrators

**Quality Guidelines:**
- Bitrate: 64k+ M4B preferred
- File size: Typically 150-300 MB per book
- Check comments for quality feedback

**Search on MAM:**
1. Go to `/tor/search.php`
2. Search: "Terry Pratchett Discworld Book 3"
3. Filter: Audiobook category
4. Sort: Seeders (highest first)
5. Check quality in comments before downloading

### PRIORITY 2: Eric Ugland - The Good Guys (11 books)

**Initial batch (Books 1-6):**
```
Eric Ugland The Good Guys Book 1
Eric Ugland The Good Guys Book 2
Eric Ugland The Good Guys Book 4
Eric Ugland The Good Guys Book 5
Eric Ugland The Good Guys Book 6
```

**Notes:**
- Series starts with Book 1 (Good Guys)
- You already have books 3, 12, 14, 15
- Narrator is consistent throughout series
- LitRPG/Dark Fantasy content

**Quality Guidelines:**
- Bitrate: 128k preferred (larger files than Discworld)
- Format: M4B
- Each book: 8-12 hours

### PRIORITY 3: Aleron Kong - The Land (10 books)

**Series Order:**
1. The Land: Forging (Book 1)
2. The Land: Catacombs (Book 2)
3. The Land: Swarm (Book 3)
4. The Land: Alliances (Book 4)
5. The Land: Raiders (Book 5)
6+ Continue series...

**Search Tips:**
- May also be found under "Chaos Seeds" subtitle
- Complete series needs all 10 books for full experience
- Start from Book 1 - absolutely essential
- Narrator must be consistent

**Quality Guidelines:**
- Bitrate: 128k preferred
- Format: M4B
- Each book: 10-14 hours
- File size: 300-500 MB per book

---

## MAM Search Workflow

### Step 1: Open MAM
```
https://www.myanonamouse.net/tor/search.php
```

### Step 2: Search
- Search term: `[Author Name] [Series Name] Book [Number]`
- Example: `Terry Pratchett Discworld Book 3`
- Category: Audiobook
- Sort: Seeders (descending)

### Step 3: Evaluate
- [ ] Check narrator matches existing books
- [ ] Verify bitrate (64k+ minimum)
- [ ] Check comments for quality feedback
- [ ] Verify file format (M4B preferred)
- [ ] Check upload date (newer = better quality usually)

### Step 4: Download
Option A (Prowlarr):
1. Right-click torrent → "Add to Prowlarr"
2. Prowlarr adds to qBittorrent watch folder
3. qBittorrent picks up and starts download

Option B (Manual):
1. Download .torrent file
2. Open with qBittorrent
3. Select save location
4. Start download

### Step 5: Monitor
- Check qBittorrent status
- Verify upload ratio
- Monitor completion

---

## Ratio Management During Phase 1

### Target Ratios
- **Minimum:** 0.5 (avoid account suspension)
- **Target:** 1.0 (healthy)
- **Ideal:** 1.5+ (helps community)

### How to Maintain Ratio
1. **Upload Limits:** Don't set upload limit too low
2. **Seeding:** Keep torrents seeding 24/7 if possible
3. **Large Files:** Prioritize seeding larger audiobooks
4. **Monitor:** Check ratio frequently in qBittorrent

### If Ratio Drops
- Focus on books with many seeders (upload faster)
- Reduce number of simultaneous downloads
- Increase seeding time per book
- Use existing downloads that already have good ratio

---

## Storage Planning

### Phase 1 Estimates
- Discworld (21 books): ~3-6 GB
- The Good Guys (11 books): ~2-3 GB
- The Land (10 books): ~2-3 GB
- **Total Phase 1: ~8-12 GB**

### Check Available Space
```bash
# Windows
dir C:
# Shows free space

# Or right-click drive → Properties
```

### Ensure Sufficient Space
- Required: 15-20 GB minimum
- Recommended: 50+ GB for Phases 1-2

---

## Audiobookshelf Integration

### What Happens Automatically
1. Downloads complete in qBittorrent
2. Files save to configured folder
3. Audiobookshelf scans folder periodically
4. New books appear in library (within 1-24 hours)

### Manual Refresh (if needed)
1. Open Audiobookshelf admin panel
2. Go to: Settings → Libraries
3. Click library → Scan for New Files
4. Wait for scan to complete

### Verify Metadata
After books appear:
1. Check author names (should match)
2. Check series name (should match)
3. Check book numbers (sequential)
4. Listen to sample to verify narrator

---

## Troubleshooting

### Book Doesn't Appear in Audiobookshelf
1. Check file location - is it in the right folder?
2. Verify file format - is it .m4b or .mp3?
3. Force refresh: Go to library settings → Scan for New Files
4. Check Audiobookshelf logs for errors

### Narrator Doesn't Match
1. Check you downloaded the right edition
2. Some series have multiple narrations - choose consistently
3. Consider re-downloading if significantly different

### Ratio Dropping Too Fast
1. Slow down downloads (download 1-2 books at a time)
2. Focus on seeding existing books
3. Check upload limit in qBittorrent settings
4. Prioritize high-seed torrents

### Can't Find Book on MAM
1. Check alternate search terms (by title or number)
2. May not be on MAM - move to next book
3. Check Prowlarr for alternate sources
4. It may be uploaded later - check back in a few days

---

## Success Criteria for Phase 1

### Minimal Success
- [ ] Downloaded at least 1 Discworld book
- [ ] Book appears in Audiobookshelf
- [ ] Confirmed workflow is functioning

### Target Success
- [ ] Downloaded 30+ books (75% of Phase 1)
- [ ] Ratio maintained above 0.5
- [ ] All books verified in Audiobookshelf

### Complete Success
- [ ] All 42 Phase 1 books downloaded
- [ ] All appear in Audiobookshelf with correct metadata
- [ ] Ratio maintained at 1.0+
- [ ] Ready to move to Phase 2

---

## Phase 1 → Phase 2 Transition

**When to start Phase 2:**
- After at least 30 Phase 1 books downloaded
- When ratio is stable (1.0+)
- When confident with download workflow

**Phase 2 Series:**
1. Craig Alanson - Expeditionary Force (9 books)
2. Neven Iliev - Everybody Loves Large Chests (8 books)
3. James S. A. Corey - The Expanse (7 books)

---

## Quick Reference Checklist

### Before Starting
- [ ] MAM access confirmed
- [ ] qBittorrent working
- [ ] Audiobookshelf accessible
- [ ] 20+ GB free space available

### During Phase 1
- [ ] Search Priority 1 series first
- [ ] Monitor qBittorrent ratio
- [ ] Verify books in Audiobookshelf
- [ ] Update download_tracker.json weekly

### Weekly Tasks
- [ ] Check qBittorrent status
- [ ] Verify new books in Audiobookshelf
- [ ] Adjust upload/download speeds if needed
- [ ] Plan next week's searches

### When Phase 1 Complete
- [ ] Re-run library analysis: `python final_missing_books_analysis.py`
- [ ] Verify completion: All books should now be in library
- [ ] Document Phase 1 results
- [ ] Prepare Phase 2 (if continuing)

---

## Important Notes

1. **Not all books may be available** - If you can't find a book, move to the next one and come back later
2. **Quality varies** - Prefer consistency with books you already have
3. **Seeding is important** - Maintaining good ratio helps the community
4. **Metadata may need manual correction** - Audiobookshelf sometimes needs help with series names
5. **This is a marathon, not a sprint** - Take your time, verify quality

---

## Support Files

Available in this directory:
- `LIBRARY_ANALYSIS_SUMMARY.md` - Full analysis
- `MAM_SEARCH_GUIDE.md` - Detailed search strategies
- `phase1_search_queries.json` - Pre-generated MAM queries
- `download_tracker.json` - Progress tracking

---

**Status:** READY FOR PHASE 1 EXECUTION
**Next Step:** Open MAM and search for first batch of Discworld books
**Timeline:** 1-2 weeks to complete 42 books
**Good luck!**

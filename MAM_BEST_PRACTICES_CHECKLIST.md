# MyAnonamouse (MAM) Best Practices Checklist

**Compiled from official MAM guides - Last Updated: 2025-11-04**

This checklist consolidates best practices from all MAM guides to ensure optimal account health, ratio management, and community participation.

---

## 📋 Critical Requirements (Site Rules)

### ✓ Seeding Requirements
- [ ] **Seed ALL torrents for minimum 72 hours within 30 days** (mandatory)
- [ ] **Download complete torrents only** - partial downloads are NOT allowed
- [ ] **Never move files after download** - use client's built-in move function
- [ ] **Monitor H&R status** - check `/snatch_summary.php` regularly
- [ ] **Keep torrents active** - avoid "Not Seeding H&R" and "Pre H&R" in Inactive section
- [ ] **Maintain ratio above 1.0** to avoid seed-only status

### ✓ Client Requirements
- [ ] **Use approved clients only**: qBittorrent (v4.3.9+, v5.0.1+), Deluge, Transmission, rTorrent
- [ ] **Avoid μTorrent** - has privacy/security issues, no longer recommended
- [ ] **Keep client running 24/7** for continuous seeding and bonus point accumulation
- [ ] **Disable anonymous mode** in qBittorrent (causes client rejection)

---

## 🔧 Client Optimization Settings

### ✓ qBittorrent Configuration
- [ ] **Port Configuration**:
  - Use port range **40000-60000** (random selection within range)
  - **Verify port forwarding** at [canyouseeme.org](http://www.canyouseeme.org/)
  - **Avoid blocked ports**: 1-1024, 1214, 4662, 6346-6347, 6881-6889
  - Forward chosen ports in router/firewall

- [ ] **Upload/Download Limits**:
  - **Cap upload to 80% of total upload capacity** (use [speedtest.net](http://www.speedtest.net/))
  - Use [Torrent Optimizing Calculator](http://infinite-source.de/az/az-calc.html) for precise settings
  - **Minimum 5 KBps per upload slot** (excellent seeders have much more)

- [ ] **Connection Settings**:
  - **Increase maximum active torrents** (but don't overload - see seeding strategy)
  - **Verify green connection status** in qBittorrent
  - **Ensure connectable status** (yellow/green smiley on MAM)

- [ ] **BitTorrent Settings**:
  - **Disable Torrent Queuing** for unlimited seeding (if bandwidth allows)
  - Or enable smart queueing to manage bandwidth if on limited connection

### ✓ Connectivity Best Practices
- [ ] **Become connectable** (highly recommended for excellent seeding):
  - [Set static local IP](https://www.myanonamouse.net/guides/?gid=77872)
  - [Configure port forwarding](https://www.myanonamouse.net/guides/?gid=75694)
  - Benefits: Can connect to both connectable and unconnectable peers (~70% of users)
  - Unconnectable users can only connect to connectable peers (~30% of users)

### ✓ Advanced qBittorrent Optimization (from Forum Insights)

#### Port Forwarding & VPN Integration
- [ ] **VPN Port Forwarding** (if using VPN):
  - Enable port forwarding in VPN provider settings (ProtonVPN, PIA, Windscribe)
  - Use **45000-60000 port range** for optimal connectivity
  - Implement dynamic port update scripts when VPN changes ports
  - Consider Gluetun Docker container for automatic VPN port management

- [ ] **Windows 11 Firewall Configuration**:
  - Disable "lazy loading" in Windows Firewall advanced settings
  - Create inbound/outbound rules for ports 80 and 45000-60000
  - Allow qBittorrent through Windows Defender on both private and public networks

- [ ] **ASN-Locked Sessions** (for dynamic IPs):
  - Use ASN-locked sessions instead of IP-locked in MAM security preferences
  - More stable for VPN users with changing IPs
  - Prevents "Unrecognized Host/PassKey" errors after IP changes

#### Torrent Management Best Practices
- [ ] **Batch Operations**:
  - Add torrents in paused state first
  - Force recheck in batches to avoid overwhelming client
  - Always force recheck after adding existing torrents

- [ ] **Connection Limits** (for large collections):
  - Set global max connections to 1000+ for large torrent collections
  - Adjust per-torrent limits based on system resources
  - Monitor for connection timeout issues

- [ ] **Network Settings**:
  - Enable UPnP/NAT-PMP for automatic port forwarding on home networks
  - Configure alternative speed limits during peak hours
  - Optimize disk settings for SSDs vs HDDs

#### Docker & Advanced Setup (Optional)
- [ ] **Docker Compose Setup** (recommended for advanced users):
  - Use Gluetun container for VPN routing
  - Route qBittorrent through Gluetun with `network_mode: "service:gluetun"`
  - Implement healthchecks to monitor VPN connectivity
  - Use dynamic seedbox API container to auto-update MAM with changing IPs

- [ ] **Port Update Automation**:
  - Use `VPN_PORT_FORWARDING_UP_COMMAND` to auto-update qBittorrent ports
  - Schedule cron jobs to restart containers and update MAM cookies on VPN reconnect
  - Monitor Gluetun logs for healthcheck failures

#### Troubleshooting Common Issues
- [ ] **VPN-Related Problems**:
  - If using OpenVPN, add `+pmp` to username for port forwarding
  - Switch from IP-locked to ASN-locked sessions for dynamic IPs
  - Monitor VPN IP changes and auto-update MAM sessions
  - Use `myanonamouse/seedboxapi` Docker container for automatic IP updates

- [ ] **Connectivity Issues**:
  - Check for Hyper-V conflicts (disable if experiencing intermittent issues)
  - Restart qBittorrent when VPN reconnects to update IP/port info
  - Verify no port conflicts with other applications
  - Monitor Docker logs for VPN healthcheck failures

- [ ] **System Conflicts**:
  - Avoid μTorrent - has known conflicts and security issues
  - Ensure qBittorrent is up-to-date (prevent Windows 7 BSOD)
  - Use systemd service for headless Linux instances
  - Backup qBittorrent config directories regularly

#### Performance Tuning
- [ ] **Multiple Instances** (advanced):
  - Run separate qBittorrent instances for seeding vs downloading
  - Use different config directories for each instance
  - Better resource management for large collections

- [ ] **Disk I/O Optimization**:
  - Configure appropriate cache sizes for large collections
  - Optimize settings differently for SSDs vs HDDs
  - Monitor memory usage and adjust as needed
  - Ensure proper file permissions on Docker volumes

---

## 💰 Ratio & Bonus Point Optimization

### ✓ Download Strategy (Smart Ratio Management)
- [ ] **Prioritize VIP torrents** - always freeleech for VIP users (0 ratio impact)
- [ ] **Download Staff Freeleech picks** - 0 ratio impact
- [ ] **Use Freeleech wedges** on large non-freeleech torrents (you have 110 wedges)
- [ ] **Check duplicate detection** - avoid downloading books already in Audiobookshelf
- [ ] **Download during freeleech periods** - finish before period ends
- [ ] **Prefer recent releases** - better seeder availability

### ✓ Bonus Point Strategy
- [ ] **Current stats**: 99,999 points (CAPPED), earning 1,413 pts/hour
- [ ] **Trade excess bonus points** for upload credit:
  - 500 Bonus Points = 1 GB upload credit
  - Recommendation: Trade 50,000-90,000 points (you're capped)
- [ ] **Earn bonus points** by seeding past 72 hours (passive income)
- [ ] **Use FL wedges liberally** - you earn more than you use
- [ ] **Contribute to Millionaire's Vault** daily for extra FL wedges

### ✓ Ratio Maintenance
- [ ] **Current ratio**: 4.053602 (excellent - way above minimum)
- [ ] **Upload**: 1.833 TiB (bought with bonus points)
- [ ] **Download**: 463.03 GiB
- [ ] **Strategy**: Maintain ratio above 2.0 for comfort margin
- [ ] **Don't panic about upload speed** - bonus points cover ratio needs

---

## 🌱 Seeding Best Practices

### ✓ Good Seeder Criteria
- [ ] **Be connectable** - allows data transfer with non-connectable peers
- [ ] **Provide adequate upload speed** - minimum 5 KBps per slot
- [ ] **Manage active torrent count** - don't overload bandwidth
- [ ] **Optimize client settings** - balance speed, slots, and connections
- [ ] **Seed long-term** - maximize bonus point earnings

### ✓ Bandwidth Management
- [ ] **Don't overload connection** - too many torrents = timeout issues
- [ ] **Use queueing on limited bandwidth** (DSL, low-end cable, satellite)
- [ ] **Monitor tracker call times** - if struggling, reduce active torrents
- [ ] **Allow adequate bandwidth** for tracker communication
- [ ] **Prioritize quality over quantity** - better to seed fewer torrents well

### ✓ Long-Term Seeding
- [ ] **Seed popular torrents** - maximize upload opportunities
- [ ] **Keep rare/requested torrents** - help community availability
- [ ] **Monitor seeding efficiency** - check Real Upload vs time spent
- [ ] **Use automatic queueing** if at maximum capacity

---

## 🚨 Hit & Run (H&R) Avoidance

### ✓ Prevention
- [ ] **All torrents are potential H&R** for first 72 hours (normal)
- [ ] **Set calendar reminders** for 72-hour seeding milestones
- [ ] **Check snatch summary** weekly at `/snatch_summary.php`
- [ ] **Monitor "Inactive" section** - avoid red numbers above 0
- [ ] **Keep qBittorrent running** to avoid accidental H&R

### ✓ H&R Recovery
- [ ] **If you have H&R torrents**:
  - Click red banner "You have H&R torrents inactive"
  - View torrents with red seedtime (< 72 hours)
  - Re-add torrents to client if removed
  - Reconnect data to torrents if moved
- [ ] **Seedtime Fix option**: 1,000 points = add 72 hours to one torrent
- [ ] **Seed continuously until ALL H&R cleared** - download privileges auto-restore

### ✓ Seed-Only Status
- [ ] **Triggered by**: Multiple H&R torrents or ratio < 1.0
- [ ] **Restrictions**: No new downloads until resolved
- [ ] **Resolution**: Seed ALL H&R torrents to 72 hours + maintain ratio > 1.0
- [ ] **Warning badge removal**: 10,000 points (cosmetic only, doesn't restore downloads)

---

## 🎯 Automated Download System Rules

### ✓ Your Current Configuration
- [ ] **Schedule**: Every Friday at 2am
- [ ] **Genres**: Science Fiction and Fantasy ONLY (whitelist mode)
- [ ] **Top N per genre**: 10 NEW audiobooks (checking up to top 100)
- [ ] **Duplicate detection**: Enabled (checks Audiobookshelf - 1604 audiobooks)
- [ ] **Client**: qBittorrent auto-add (category: audiobooks-auto)

### ✓ Optimization Settings
- [ ] **Prefer VIP torrents**: Enabled (always freeleech for you)
- [ ] **Prefer Staff Freeleech**: Enabled (0 ratio impact)
- [ ] **Use FL wedges**: Enabled (auto-apply on non-freeleech torrents)
- [ ] **Timespan preference**: Recent (better seeder availability)
- [ ] **Min seeders**: 5+ (ensures good availability)

### ✓ Safety Checks
- [ ] **Skip duplicates**: Checks 1604 audiobooks in Audiobookshelf
- [ ] **Fuzzy title matching**: Handles variations in titles
- [ ] **Max check limit**: 100 (finds 10 new even with 90% duplicates)
- [ ] **Auto-categorization**: Keeps automated downloads organized
- [ ] **Detailed reporting**: Review what was downloaded/skipped

---

## 📊 Weekly Maintenance Checklist

### ✓ Every Week
- [ ] **Check snatch summary** for H&R warnings
- [ ] **Review batch report** (`batch_report_*.txt`) from Friday automation
- [ ] **Verify duplicate detection** working correctly
- [ ] **Check qBittorrent**:
  - Green connection status
  - No stalled torrents
  - No tracker errors
- [ ] **Monitor bonus points** - trade if approaching cap (99,999)
- [ ] **Review ratio** - should stay above 2.0 comfortably

### ✓ Every Month
- [ ] **Audit Audiobookshelf library** - ensure accurate duplicate detection
- [ ] **Review download patterns** - adjust genres if needed
- [ ] **Check seeding torrents** - remove very old with no activity
- [ ] **Verify automation schedule** - ensure Task Scheduler running
- [ ] **Update qBittorrent** if needed (check allowed versions in rules)

### ✓ Every Quarter
- [ ] **Port check** at canyouseeme.org (ensure still forwarded)
- [ ] **Speed test** at speedtest.net (recalculate upload cap if changed)
- [ ] **Review automation config** - add/remove genres as interests change
- [ ] **Backup important torrents** - protect rare/requested content

---

## 🚀 Advanced Optimization

### ✓ VIP Status Benefits
- [ ] **You have VIP status** - maximize it!
- [ ] **Download VIP torrents exclusively** when possible (always freeleech)
- [ ] **Renew VIP** with bonus points when needed (you have plenty)
- [ ] **Access VIP-only content** not available to regular users

### ✓ Community Participation
- [ ] **Follow forum rules**: No swearing, NSFW talk, politics
- [ ] **Don't mention other trackers**
- [ ] **Don't ask for/hint about needing points**
- [ ] **Use requests section** for missing books
- [ ] **Help new members** when possible
- [ ] **Report bugs/issues** to staff if found

### ✓ Security & Privacy
- [ ] **Use HTTPS** for all MAM connections (migration complete)
- [ ] **Don't share account credentials**
- [ ] **Keep API tokens secure** (ABS_TOKEN, MAM credentials)
- [ ] **Use VPN if desired** (but may affect connectability)
- [ ] **Monitor account security** - check login history

---

## 📈 Success Metrics

### ✓ Account Health Indicators
- **Ratio**: 4.053602 ✅ (Target: > 2.0)
- **Bonus Points**: 99,999 (CAPPED) ✅
- **Bonus Rate**: 1,413 pts/hour ✅
- **FL Wedges**: 110 ✅
- **H&R Count**: 0 ✅
- **Seedtime Satisfied**: 100% ✅
- **Connection**: Connectable ✅

### ✓ Automation Health
- **Duplicate Detection**: Working (1604 audiobooks tracked)
- **Weekly Downloads**: ~10-20 NEW audiobooks
- **Duplicate Skip Rate**: Should increase over time (good!)
- **Freeleech Usage**: Maximized (VIP + FL wedges)
- **Storage**: Organized in Audiobookshelf

---

## 🎓 Key Takeaways

**Golden Rules:**
1. **Seed for 72 hours minimum** - non-negotiable
2. **Use VIP torrents** - zero ratio impact
3. **Trade bonus points** - you're capped at 99,999
4. **Keep client connectable** - better upload opportunities
5. **Don't overload bandwidth** - quality over quantity
6. **Monitor H&R status** - avoid seed-only lockout
7. **Let automation run** - wake up to new audiobooks every Saturday

**Your Advantages:**
- ✅ VIP status (all VIP torrents freeleech)
- ✅ Excellent ratio (4.05)
- ✅ Capped bonus points (trade for upload)
- ✅ 110 FL wedges (use liberally)
- ✅ Automated duplicate detection (1604 audiobooks)
- ✅ Optimized download strategy (VIP + freeleech priority)

**Recommended Actions:**
1. Trade 50,000-90,000 bonus points for upload credit (you're capped)
2. Continue Friday automation (working perfectly)
3. Seed all automated downloads for 72+ hours
4. Review batch reports weekly
5. Keep qBittorrent running 24/7

---

## 📚 Reference Links

**MAM Guides:**
- [Beginner's Guide](https://www.myanonamouse.net/guides/?gid=37768)
- [Being a Good Seeder](https://www.myanonamouse.net/guides/?gid=38940)
- [Bonus Points Guide](https://www.myanonamouse.net/guides/?gid=48479)
- [VIP Guide](https://www.myanonamouse.net/guides/?gid=33794)
- [What is H&R](https://www.myanonamouse.net/guides/?gid=45578)
- [qBittorrent Settings](https://www.myanonamouse.net/guides/?gid=31646)
- [Torrenting Guide](https://www.myanonamouse.net/guides/?gid=30163)
- [Start Here!](https://www.myanonamouse.net/guides/?gid=72809)

**MAM Pages:**
- [Snatch Summary](https://www.myanonamouse.net/snatch_summary.php) - Check H&R status
- [Bonus Store](https://www.myanonamouse.net/store.php) - Trade points for upload
- [Freeleech](https://www.myanonamouse.net/freeleech.php) - Browse FL torrents
- [Millionaire's Vault](https://www.myanonamouse.net/millionaires/pot.php) - Earn FL wedges
- [Rules](https://www.myanonamouse.net/rules.php) - Site rules
- [FAQ](https://www.myanonamouse.net/faq.php) - Frequently asked questions

**External Tools:**
- [Can You See Me](http://www.canyouseeme.org/) - Port forwarding check
- [PortForward.com](http://www.portforward.com/) - Router configuration guides
- [SpeedTest.net](http://www.speedtest.net/) - Bandwidth testing
- [Torrent Optimizing Calculator](http://infinite-source.de/az/az-calc.html) - Client settings calculator

---

**Status**: ✅ **All critical requirements MET** - Account in excellent standing!

**Last Reviewed**: 2025-11-04
**Next Review**: 2025-12-04 (monthly)

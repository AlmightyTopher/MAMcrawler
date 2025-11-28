# audiobookshelf

**Source:** https://www.audiobookshelf.org/guides/migration-and-backups

**Crawled:** 2025-11-27 21:19:27

---

# Migration and Backups

This page discusses common migration problems for server2.2.xthrough2.8.xand how to restore from backups.

`2.2.x``2.8.x`# tagMigration Instructions

There are a lot of version numbers, so verify the version due to confusion with all of the 2's and 3's in version numbers.

## tagFrom version 2.2.x

If you are running version2.2.23or lower and want to upgrade, you may have some additional steps because2.3.xincludes a database migration.

`2.2.23``2.3.x`First, if you are not running2.2.23, you should first upgrade to this version to ensure everything is working correctly with your library before migrating.
Once you have verified you are on2.2.23, there are several different things which may have happened (especially if you had previously tried to upgrade).

`2.2.23``2.2.23`The2.3.xand2.4.xversions include a database migration.
The following graphic shows the steps the server does for the database migration (all within the/configdirectory).
You do not do any of these steps.

`2.3.x``2.4.x``/config`If you have previously tried to upgrade or run into a migration issue, look in your/configdirectory and check if the SQLite database exists.
If it does, that is why your server is still not starting/migrating your data.
You can either rename this database file or delete it.
If you haveoldDb.zip, you should also rename that (but don't delete it until you have verified the migration went well in case there's data there you don't have).
Once you have removed the SQLite database file, you can upgrade to2.3.3,2.4.1, orlatestto get the last official release.DO NOTupgrade to2.3.0,2.3.1, or2.3.2as migration issues were fixed in2.3.3.
You can go directly to2.4.1and do not need to first migrate to2.3.3.

`/config``oldDb.zip``2.3.3``2.4.1``latest``2.3.0``2.3.1``2.3.2``2.3.3``2.4.1``2.3.3`If your server is failing to start after the migration, ensure your/configdirectory is on the same machine that is running the ABS server.
The new SQLite database needs to be on the same machine and cannot be stored on a remote location (such as if you're running the ABS server on your desktop but all of the data for the server is stored on a NAS).
If you are doing this, you will need to make a local directory and move your/configthere.
The/metadataand all media files can remain on another machine.

`/config``/config``/metadata`## tagFrom version 2.3.3

If you are on version2.3.3, you should upgrade to2.4.1, skipping2.3.4and2.3.5.
There were some issues with2.3.4and2.3.5which were immidately fixed in2.4.1, but due to version numbering these releases still exist.
Some servers have updated automatically due to Watchtower or other tools automatically updating the Docker image as soon as they were released, so these servers should be updated to2.4.1since we already know those versions don't work.
Your data is not affected if you updated to2.3.4or2.3.5, just your server may not start until you upgrade.

`2.3.3``2.4.1``2.3.4``2.3.5``2.3.4``2.3.5``2.4.1``2.4.1``2.3.4``2.3.5`# tagRestoring from backup

This section includes information on restoring from a backup. Backups from2.2.xare NOT supported on2.3.xand above. If you would like to use a backup from2.2.xon a newer version, you can either roll back to2.2.23and restore from a backup and let the server perform the migration again (see above), or just restore the2.2.xbackup manually in the filesystem as explained below, and then perform the migration as above.

`2.2.x``2.3.x``2.2.x``2.2.23``2.2.x`Before restoring from a backup using the filesystem, make sure your ABS server is not running.



## tagRestoring 2.2.x

To restore a backup in2.2.x, you can either use the web GUI in the server settings or manually restore using the filesystem.

`2.2.x`These backups are just a zip file of the/config,/metadata/authorsand/metadata/items. If you're on Windows, you can just rename the backup file to end in.zipinstead of.audiobookshelf, then extract the backup. You will then replace the corresponding directories on your server with these extracted files. Note that the metadata directories from the backup are replacing the/metadata/authorsand/metadata/itemsdirectories, NOT creating a new/metadata-itemsdirectory on the server.

`/config``/metadata/authors``/metadata/items``.zip``.audiobookshelf``/metadata/authors``/metadata/items``/metadata-items`## tagRestoring 2.3.x and above

To restore from a backup in2.3.xand above, follow these steps:

`2.3.x`- Stop the Service:If ABS is installed as a service:systemctl stop audiobookshelf.serviceIf using Docker:docker stop <container-name>If on Windows: Close the application via the tray
- If ABS is installed as a service:systemctl stop audiobookshelf.service
- If using Docker:docker stop <container-name>
- If on Windows: Close the application via the tray
- Navigate to Your Base Path:

Stop the Service:

> If ABS is installed as a service:systemctl stop audiobookshelf.serviceIf using Docker:docker stop <container-name>If on Windows: Close the application via the tray

- If ABS is installed as a service:systemctl stop audiobookshelf.service
- If using Docker:docker stop <container-name>
- If on Windows: Close the application via the tray

`systemctl stop audiobookshelf.service``docker stop <container-name>`Navigate to Your Base Path:

- Note: If you have changed the metadata or config paths, navigate to those paths instead.

> Service:cd /usr/share/audiobookshelfDocker:cd <path-to-your-docker-compose-file>

- Service:cd /usr/share/audiobookshelf
- Docker:cd <path-to-your-docker-compose-file>

`cd /usr/share/audiobookshelf``cd <path-to-your-docker-compose-file>`- Locate and Unzip the Backup Folder:

- Note: The backup is named according to the date it was created. Use the newest backup and if that doesn't work, try the next newest.

> Service:cd metadata/backupsandunzip <date>.audiobookshelfDocker:cd metadata/backupsandunzip <date>.audiobookshelfWindows: Open the backup folder in Explorer and unzip the file using a tool like 7-Zip

- Service:cd metadata/backupsandunzip <date>.audiobookshelf
- Docker:cd metadata/backupsandunzip <date>.audiobookshelf
- Windows: Open the backup folder in Explorer and unzip the file using a tool like 7-Zip

`cd metadata/backups``unzip <date>.audiobookshelf``cd metadata/backups``unzip <date>.audiobookshelf`- Replace theaudiobookshelf.sqliteFile:Service:cp audiobookshelf.sqlite ../../config/audiobookshelf.sqliteDocker:cp audiobookshelf.sqlite ../../config/audiobookshelf.sqliteWindows: Copy theaudiobookshelf.sqlitefile to the config folder
- Service:cp audiobookshelf.sqlite ../../config/audiobookshelf.sqlite
- Docker:cp audiobookshelf.sqlite ../../config/audiobookshelf.sqlite
- Windows: Copy theaudiobookshelf.sqlitefile to the config folder
- Replace theauthorsanditemsFolders:Service:cp -r metadata-authors ../authorsandcp -r metadata-items ../itemsDocker:cp -r metadata-authors ../authorsandcp -r metadata-items ../itemsWindows: Copy the contents ofmetadata-authorsandmetadata-itemsto themetadata/authorsandmetadata/itemsfolders
- Service:cp -r metadata-authors ../authorsandcp -r metadata-items ../items
- Docker:cp -r metadata-authors ../authorsandcp -r metadata-items ../items
- Windows: Copy the contents ofmetadata-authorsandmetadata-itemsto themetadata/authorsandmetadata/itemsfolders
- Start the Service:If ABS is installed as a service:systemctl start audiobookshelf.serviceIf using Docker:docker start <container-name>If on Windows: Start the application via the tray
- If ABS is installed as a service:systemctl start audiobookshelf.service
- If using Docker:docker start <container-name>
- If on Windows: Start the application via the tray

Replace theaudiobookshelf.sqliteFile:

`audiobookshelf.sqlite`> Service:cp audiobookshelf.sqlite ../../config/audiobookshelf.sqliteDocker:cp audiobookshelf.sqlite ../../config/audiobookshelf.sqliteWindows: Copy theaudiobookshelf.sqlitefile to the config folder

- Service:cp audiobookshelf.sqlite ../../config/audiobookshelf.sqlite
- Docker:cp audiobookshelf.sqlite ../../config/audiobookshelf.sqlite
- Windows: Copy theaudiobookshelf.sqlitefile to the config folder

`cp audiobookshelf.sqlite ../../config/audiobookshelf.sqlite``cp audiobookshelf.sqlite ../../config/audiobookshelf.sqlite``audiobookshelf.sqlite`Replace theauthorsanditemsFolders:

`authors``items`> Service:cp -r metadata-authors ../authorsandcp -r metadata-items ../itemsDocker:cp -r metadata-authors ../authorsandcp -r metadata-items ../itemsWindows: Copy the contents ofmetadata-authorsandmetadata-itemsto themetadata/authorsandmetadata/itemsfolders

- Service:cp -r metadata-authors ../authorsandcp -r metadata-items ../items
- Docker:cp -r metadata-authors ../authorsandcp -r metadata-items ../items
- Windows: Copy the contents ofmetadata-authorsandmetadata-itemsto themetadata/authorsandmetadata/itemsfolders

`cp -r metadata-authors ../authors``cp -r metadata-items ../items``cp -r metadata-authors ../authors``cp -r metadata-items ../items``metadata-authors``metadata-items``metadata/authors``metadata/items`Start the Service:

> If ABS is installed as a service:systemctl start audiobookshelf.serviceIf using Docker:docker start <container-name>If on Windows: Start the application via the tray

- If ABS is installed as a service:systemctl start audiobookshelf.service
- If using Docker:docker start <container-name>
- If on Windows: Start the application via the tray

`systemctl start audiobookshelf.service``docker start <container-name>`
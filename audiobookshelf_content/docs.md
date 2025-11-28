# audiobookshelf

**Source:** https://www.audiobookshelf.org/docs

**Crawled:** 2025-11-27 21:18:54

---

Install

Upgrade

Configuration

Books

Podcasts

# tagIntroduction

Audiobookshelf is an open-source self-hosted media server for your audiobooks and podcasts.

Features include...

- Companionandroid and iOS appw/ offline listening(in beta)
- Multi-user support w/ custom permissions
- Keeps progress per user and syncs across devices
- Lookup and apply metadata and cover art from several providers
- Audiobook chapter editor w/ chapter lookup
- Audiobook tools: Embed metadata in audio files & merge multiple audio files to a single m4b
- Search and add podcasts to download episodes w/ auto-download
- Open RSS feeds for audiobooks and podcast episodes
- Backups with automated backup scheduling
- Basic ebook support and ereader (epub, pdf, cbr, cbz) + send to device (i.e. Kindle)
- And much more...

Join ourDiscord server.

If you are interested in integrating with Audiobookshelf, visit theAPI documentation.

The source for this documentation can be found at theAudiobookshelf GitHub repository. Contributions to this documentation can be made through a pull request.

Demo

Check out the web client demo:https://audiobooks.dev/(thanks for hosting@Vito0912!)

Username/password:demo/demo(user account)

`demo``demo`# tagDocker Compose

```
services:
  audiobookshelf:
    image: ghcr.io/advplyr/audiobookshelf:latest
    ports:
      - 13378:80
    volumes:
      - </path/to/audiobooks>:/audiobooks
      - </path/to/podcasts>:/podcasts
      - </path/to/config>:/config
      - </path/to/metadata>:/metadata
    environment:
      - TZ=America/Toronto

```

`services:
  audiobookshelf:
    image: ghcr.io/advplyr/audiobookshelf:latest
    ports:
      -13378:80
    volumes:
      -</path/to/audiobooks>:/audiobooks
      -</path/to/podcasts>:/podcasts
      -</path/to/config>:/config
      -</path/to/metadata>:/metadata
    environment:
      -TZ=America/Toronto`- Remember to change the path to your actual directory and remove the <> symbols
- Volume mappings should all be separate directories that are not contained in eachother

Volume mappings

- /configwill contain the database (users/books/libraries/settings). Beginning with2.3.x,this needs to be on the same machine you are running ABS on.
- /metadatawill contain cache, streams, covers, downloads, backups and logs
- Map any other directories you want to use for your book and podcast collections (ebooks supported)
Still confused about Docker? Check outthis FAQ

`/config``2.3.x``/metadata`💡Prefer the CLI? This is our docker run command. YMMV

`💡`> dockerpull ghcr.io/advplyr/audiobookshelfdockerrun-d\-p13378:80\-v</path/to/config>:/config\-v</path/to/metadata>:/metadata\-v</path/to/audiobooks>:/audiobooks\-v</path/to/podcasts>:/podcasts\--nameaudiobookshelf\-eTZ="America/Toronto"\ghcr.io/advplyr/audiobookshelf

```
docker pull ghcr.io/advplyr/audiobookshelf

docker run -d \
 -p 13378:80 \
 -v </path/to/config>:/config \
 -v </path/to/metadata>:/metadata \
 -v </path/to/audiobooks>:/audiobooks \
 -v </path/to/podcasts>:/podcasts \
 --name audiobookshelf \
 -e TZ="America/Toronto" \
 ghcr.io/advplyr/audiobookshelf

```

`dockerpull ghcr.io/advplyr/audiobookshelfdockerrun-d\-p13378:80\-v</path/to/config>:/config\-v</path/to/metadata>:/metadata\-v</path/to/audiobooks>:/audiobooks\-v</path/to/podcasts>:/podcasts\--nameaudiobookshelf\-eTZ="America/Toronto"\ghcr.io/advplyr/audiobookshelf`⚠️Windows users will need to remove the \ and run this as a single line

`⚠️`# tagLinux (Debian, Ubuntu, …)

For Debian based systems, you can activate the official Audiobookshelf repository and install the Debian package.

## tagInstallation

Activate the repository:

```
sudo apt install gnupg curl
wget -O- https://advplyr.github.io/audiobookshelf-ppa/KEY.gpg | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/adb-archive-keyring.gpg
sudo curl -s -o /etc/apt/sources.list.d/audiobookshelf.list https://advplyr.github.io/audiobookshelf-ppa/audiobookshelf.list

```

`sudoaptinstallgnupgcurlwget-O- https://advplyr.github.io/audiobookshelf-ppa/KEY.gpg|gpg--dearmor|sudotee/etc/apt/trusted.gpg.d/adb-archive-keyring.gpgsudocurl-s-o/etc/apt/sources.list.d/audiobookshelf.list https://advplyr.github.io/audiobookshelf-ppa/audiobookshelf.list`Install Audiobookshelf:

```
sudo apt update
sudo apt install audiobookshelf

```

`sudoaptupdatesudoaptinstallaudiobookshelf`## tagConfiguration

The Audiobookshelf service will use the config file localted at/etc/default/audiobookshelf.
The default configuration is as follows:

`/etc/default/audiobookshelf````
METADATA_PATH=/usr/share/audiobookshelf/metadata
CONFIG_PATH=/usr/share/audiobookshelf/config
FFMPEG_PATH=/usr/lib/audiobookshelf-ffmpeg/ffmpeg
FFPROBE_PATH=/usr/lib/audiobookshelf-ffmpeg/ffprobe
TONE_PATH=/usr/lib/audiobookshelf-ffmpeg/tone
PORT=13378

```

`METADATA_PATH=/usr/share/audiobookshelf/metadataCONFIG_PATH=/usr/share/audiobookshelf/configFFMPEG_PATH=/usr/lib/audiobookshelf-ffmpeg/ffmpegFFPROBE_PATH=/usr/lib/audiobookshelf-ffmpeg/ffprobeTONE_PATH=/usr/lib/audiobookshelf-ffmpeg/tonePORT=13378`If you update the configuration, restart the service by running:

```
sudo systemctl restart audiobookshelf.service

```

`sudosystemctl restart audiobookshelf.service`# tagLinux (RHEL, CentOS, …)

- This installation method is still in testing.
- Only for amd64 architecture.
- Supported operating systems are all Red Hat and CentOS Stream 8/9 variants.

## tagInstallation

To activate the repository, run:

```
dnf install -y "https://github.com/lkiesow/audiobookshelf-rpm/raw/el$(rpm -E %rhel)/audiobookshelf-repository-1-1.el$(rpm -E %rhel).noarch.rpm"

```

`dnfinstall-y"https://github.com/lkiesow/audiobookshelf-rpm/raw/el$(rpm-E%rhel)/audiobookshelf-repository-1-1.el$(rpm-E%rhel).noarch.rpm"`You can now install Audiobookshelf.
All dependencies will be installed automatically:

```
dnf install audiobookshelf

```

`dnfinstallaudiobookshelf`## tagConfiguration

You can configure Audiobookshelf in/etc/default/audiobookshelf.
Here you can add the same configuration options you would pass to the Docker container.

`/etc/default/audiobookshelf````
METADATA_PATH=/var/lib/audiobookshelf/metadata
CONFIG_PATH=/var/lib/audiobookshelf/config
PORT=13378
HOST=127.0.0.1

```

`METADATA_PATH=/var/lib/audiobookshelf/metadataCONFIG_PATH=/var/lib/audiobookshelf/configPORT=13378HOST=127.0.0.1`By default, Audiobookshelf will listen tolocalhostonly.
This should be sufficient if you install a reverse proxy (you should!).
If you want to listen to all network interfaces, setHOST=0.0.0.0instead.

`localhost``HOST=0.0.0.0`## tagStart Audiobookshelf

To run Audiobookshelf and ensure it will be started automatically after a reboot, run:

```
systemctl start audiobookshelf.service
systemctl enable audiobookshelf.service

```

`systemctl start audiobookshelf.service
systemctlenableaudiobookshelf.service`To check the current status of the service, run:

```
systemctl status audiobookshelf.service

```

`systemctl status audiobookshelf.service`# tagLinux (NixOS)

## tagInstallation

Declarative installation:

```
environment.systemPackages = [
  pkgs.audiobookshelf
];

```

`environment.systemPackages=[pkgs.audiobookshelf];`## tagConfiguration

You can configure audiobookshelf using the parameters to the executable.
It supports the same configuration options you would pass to the Docker container,
the options below are the defaults if the option is missing.

```
audiobookshelf --metadata "$(pwd)/metadata" \
  --config "$(pwd)/config" \
  --port 8000 \
  --host 0.0.0.0

```

`audiobookshelf--metadata"$(pwd)/metadata"\--config"$(pwd)/config"\--port8000\--host0.0.0.0`If you use a reverse proxy (you should!) listing on localhost only would be enough.
In this case set--host 127.0.0.1instead.

`--host 127.0.0.1`## tagStart audiobookshelf

You can create a simple systemd service in yourconfiguration.nixto automatically start
audiobookshelf:

`configuration.nix````
services.audiobookshelf.enable = true;

```

`services.audiobookshelf.enable=true;`For further options, seethe NixOS options page.

To configure a reverse nginx proxy, add the following:

```
services.nginx = {
  enable = true;
  recommendedProxySettings = true;
  virtualHosts."your.hostname.org" = {
    forceSSL = true; # Optional, but highly recommended
    locations."/" = {
      proxyPass = "http://127.0.0.1:${builtins.toString config.services.audiobookshelf.port}";
      proxyWebsockets = true;
      extraConfig = ''
        proxy_redirect http:// $scheme://;
      '';
    };
    useACMEHost = "[attribute name from security.acme.certs]"; # Optional, but highly recommended
  };
};

```

`services.nginx={enable=true;recommendedProxySettings=true;virtualHosts."your.hostname.org"={forceSSL=true;# Optional, but highly recommendedlocations."/"={proxyPass="http://127.0.0.1:${builtins.toStringconfig.services.audiobookshelf.port}";proxyWebsockets=true;extraConfig=''
        proxy_redirect http:// $scheme://;
      '';};useACMEHost="[attribute name from security.acme.certs]";# Optional, but highly recommended};};`To check the current status of the service, run:

```
systemctl status audiobookshelf.service

```

`systemctl status audiobookshelf.service`# tagWindows

View latest release

See project repo for more information:https://github.com/mikiher/audiobookshelf-windows

Note: Requires Windows 10 64-bit or later

Issues with the installer or Windows tray app should be openedhere.

You can also install audiobookshelf on Windows using Docker. Check out theuser-contributed guide for installing on Windowsand join our Discord server for support.

# tagReverse Proxy

See Github readmefor user-contributed reverse proxy configs

# tagDeploy on Easypanel

## tagDeploying audiobookshelf on Easypanel

Easypanelit's a modern server control panel. You can use it to deploy audiobookshelf on your own server.



## tagInstructions

- Create a VM that runs Ubuntu on your cloud provider.
- Install Easypanel using the instructions from the website.
- Create a new project.
- Install audiobookshelf using the dedicated template.

# tagPodman

Quadlet Container (Requires Podman version 4.4 or above)

```
# audiobookshelf.container
[Container]
ContainerName=audiobookshelf
Image=ghcr.io/advplyr/audiobookshelf:latest
AutoUpdate=registry
NoNewPrivileges=true
PublishPort=13378:80
Volume=</path/to/audiobooks>:/audiobooks
Volume=</path/to/books>:/books
Volume=</path/to/podcasts>:/podcasts
Volume=</path/to/config>:/config
Volume=</path/to/metadata>:/metadata

[Service]
Restart=always

[Install]
WantedBy=default.target

```

`# audiobookshelf.container[Container]ContainerName=audiobookshelfImage=ghcr.io/advplyr/audiobookshelf:latestAutoUpdate=registryNoNewPrivileges=truePublishPort=13378:80Volume=</path/to/audiobooks>:/audiobooksVolume=</path/to/books>:/booksVolume=</path/to/podcasts>:/podcastsVolume=</path/to/config>:/configVolume=</path/to/metadata>:/metadata[Service]Restart=always[Install]WantedBy=default.target`- Remember to change the path to your actual directory and remove the <> symbols
- Volume mappings should all be separate directories that are not contained in each other
- If SELinux is enabled on your host, you may need to run the following command to allow the container to access the directories you are mapping to it:sudo chcon -R -t svirt_sandbox_file_t /path/to/directory

`sudo chcon -R -t svirt_sandbox_file_t /path/to/directory`Volume mappings

- /configwill contain the database (users/books/libraries/settings). Beginning with2.3.x,this needs to be on the same machine you are running ABS on.
- /metadatawill contain cache, streams, covers, downloads, backups and logs
- Map any other directories you want to use for your book and podcast collections (ebooks supported)
Still confused about containers? Check outthis FAQ(It is about Docker, but the concept is the same)

`/config``2.3.x``/metadata`💡Prefer the CLI? This is our podman run command. YMMV

`💡`> podmanpull ghcr.io/advplyr/audiobookshelfpodmanrun-d\-p13378:80\-v</path/to/config>:/config\-v</path/to/metadata>:/metadata\-v</path/to/audiobooks>:/audiobooks\-v</path/to/books>:/books\-v</path/to/podcasts>:/podcasts\--nameaudiobookshelf\-eTZ="America/Toronto"\ghcr.io/advplyr/audiobookshelf

```
podman pull ghcr.io/advplyr/audiobookshelf

podman run -d \
 -p 13378:80 \
 -v </path/to/config>:/config \
 -v </path/to/metadata>:/metadata \
 -v </path/to/audiobooks>:/audiobooks \
 -v </path/to/books>:/books \
 -v </path/to/podcasts>:/podcasts \
 --name audiobookshelf \
 -e TZ="America/Toronto" \
 ghcr.io/advplyr/audiobookshelf

```

`podmanpull ghcr.io/advplyr/audiobookshelfpodmanrun-d\-p13378:80\-v</path/to/config>:/config\-v</path/to/metadata>:/metadata\-v</path/to/audiobooks>:/audiobooks\-v</path/to/books>:/books\-v</path/to/podcasts>:/podcasts\--nameaudiobookshelf\-eTZ="America/Toronto"\ghcr.io/advplyr/audiobookshelf`# tagMobile Apps

The mobile apps are open source onGithub. Report bugs and suggest features there.

### tagAndroid

Install from the Google Play Store.

### tagiOS

Join Test Flight beta testing and install the app.

# tagDocker

To upgrade the server to the newest version, you just need to pull the new docker image and restart the container. If you are using Portainer or Docker Desktop, you can just update the stack and pull the new image. If you are using a pinned version number, you will need to update that version number.

Still confused about Docker? Check outthis FAQ

# tagDocker Compose

If you used docker compose, you just need to make sure the tag is either the version you want orlatestif you want the newest release. If you want to run a specific release, such as older version, change the tag to the desired version number.

`latest`Then, you can just run the following commands.

```
docker compose pull
docker compose down
docker compose up --detach

```

`dockercompose pulldockercompose downdockercompose up--detach`Still confused about Docker? Check outthis FAQ

# tagPodman

If AutoUpdate policy is set to registry, you can just execute the following command:

```
podman auto-update

```

`podmanauto-update`Otherwise, you can manually update the container by pulling the new image and replacing the old one.

For rootless containers: (Containers not running as root)

To pull the new image:

```
podman pull ghcr.io/advplyr/audiobookshelf

```

`podmanpull ghcr.io/advplyr/audiobookshelf`To start the container with the new image:

```
systemctl --user restart audiobookshelf

```

`systemctl--userrestart audiobookshelf`For rootful containers: (Containers running as root)

To pull the new image:

```
sudo podman pull ghcr.io/advplyr/audiobookshelf

```

`sudopodmanpull ghcr.io/advplyr/audiobookshelf`To start the container with the new image:

```
sudo systemctl restart audiobookshelf

```

`sudosystemctl restart audiobookshelf`If you are running the container with thepodman runcommand, you can remove the old container and start it again with the new image:

`podman run````
podman stop audiobookshelf
podman rm audiobookshelf
podman run -d \
  -p 13378:80 \
  -v </path/to/config>:/config \
  -v </path/to/metadata>:/metadata \
  -v </path/to/audiobooks>:/audiobooks \
  -v </path/to/books>:/books \
  -v </path/to/podcasts>:/podcasts \
  --name audiobookshelf \
  -e TZ="America/Toronto" \
  ghcr.io/advplyr/audiobookshelf

```

`podmanstop audiobookshelfpodmanrmaudiobookshelfpodmanrun-d\-p13378:80\-v</path/to/config>:/config\-v</path/to/metadata>:/metadata\-v</path/to/audiobooks>:/audiobooks\-v</path/to/books>:/books\-v</path/to/podcasts>:/podcasts\--nameaudiobookshelf\-eTZ="America/Toronto"\ghcr.io/advplyr/audiobookshelf`# tagConfiguration

Audiobookshelf is configured via environment variables.
You can pass them to your Docker container using-e VARIABLE=VALUEor set them in/etc/default/audiobookshelfif you install audiobookshelf via packages.

`-e VARIABLE=VALUE``/etc/default/audiobookshelf`Here is a list of all available options:

## tagFilesystem

- CONFIG_PATH(default:./config)Path to the config directory.It will contain the database (users/books/libraries/settings). This location must not be mounted over the network.
- Path to the config directory.
- It will contain the database (users/books/libraries/settings). This location must not be mounted over the network.
- METADATA_PATH(default:./metadata)Path to the metadata directory.It will contain cache, streams, covers, downloads, backups and logs.
- Path to the metadata directory.
- It will contain cache, streams, covers, downloads, backups and logs.
- BACKUP_PATH(default:./metadata/backups)Path to where backups are stored.Backups contain a backup of the database in/configand images/metadata stored in./metadata/itemsand./metadata/authors
- Path to where backups are stored.
- Backups contain a backup of the database in/configand images/metadata stored in./metadata/itemsand./metadata/authors

`CONFIG_PATH``./config`- Path to the config directory.
- It will contain the database (users/books/libraries/settings). This location must not be mounted over the network.

`METADATA_PATH``./metadata`- Path to the metadata directory.
- It will contain cache, streams, covers, downloads, backups and logs.

`BACKUP_PATH``./metadata/backups`- Path to where backups are stored.
- Backups contain a backup of the database in/configand images/metadata stored in./metadata/itemsand./metadata/authors

`/config``./metadata/items``./metadata/authors`## tagExternal Tools

- FFMPEG_PATH(default:ffmpeg)Path to theffmpegbinary.If no path is set, Audiobookshelf will assume the binary to exist in the system path.
- Path to theffmpegbinary.
- If no path is set, Audiobookshelf will assume the binary to exist in the system path.
- FFPROBE_PATH(default:ffprobe)Path to theffprobebinary.If no path is set, Audiobookshelf will assume the binary to exist in the system path.
- Path to theffprobebinary.
- If no path is set, Audiobookshelf will assume the binary to exist in the system path.

`FFMPEG_PATH``ffmpeg`- Path to theffmpegbinary.
- If no path is set, Audiobookshelf will assume the binary to exist in the system path.

`ffmpeg``FFPROBE_PATH``ffprobe`- Path to theffprobebinary.
- If no path is set, Audiobookshelf will assume the binary to exist in the system path.

`ffprobe`## tagNetwork

- HOSTThe host Audiobookshelf binds to.
Most commonly, this will be127.0.0.1if you want the service to listen to localhost only,
or left unset if you want to listen to all interfaces (both IPv4 and IPv6).
- The host Audiobookshelf binds to.
Most commonly, this will be127.0.0.1if you want the service to listen to localhost only,
or left unset if you want to listen to all interfaces (both IPv4 and IPv6).
- PORTThe TCP port Audiobookshelf will listen on.
- The TCP port Audiobookshelf will listen on.
- EXP_PROXY_SUPPORTExperimental workaround to repsect theHTTP_PROXYandHTTPS_PROXYenvironment variables.
The SSRF request filter is also disablede by using thes environment variable
- Experimental workaround to repsect theHTTP_PROXYandHTTPS_PROXYenvironment variables.
The SSRF request filter is also disablede by using thes environment variable

`HOST`- The host Audiobookshelf binds to.
Most commonly, this will be127.0.0.1if you want the service to listen to localhost only,
or left unset if you want to listen to all interfaces (both IPv4 and IPv6).

`127.0.0.1``PORT`- The TCP port Audiobookshelf will listen on.

`EXP_PROXY_SUPPORT`- Experimental workaround to repsect theHTTP_PROXYandHTTPS_PROXYenvironment variables.
The SSRF request filter is also disablede by using thes environment variable

`HTTP_PROXY``HTTPS_PROXY`## tagSecurity

- TOKEN_SECRETRemoved in v2.26.0Secret used for generating the JSON Web Tokens.If none is provided, a secure random token is generated automatically.
That will usually be sufficient.
- Secret used for generating the JSON Web Tokens.
- If none is provided, a secure random token is generated automatically.
That will usually be sufficient.
- ACCESS_TOKEN_EXPIRYAdded in v2.26.0Access token expiration in seconds (default: 43200 = 12 hours)
- Access token expiration in seconds (default: 43200 = 12 hours)
- REFRESH_TOKEN_EXPIRYAdded in v2.26.0Refresh token expiration in seconds (default: 604800 = 7 days)
- Refresh token expiration in seconds (default: 604800 = 7 days)
- RATE_LIMIT_AUTH_WINDOWAdded in v2.26.0Rate limiting window in milliseconds (default: 600000 = 10 minutes)
- Rate limiting window in milliseconds (default: 600000 = 10 minutes)
- RATE_LIMIT_AUTH_MAXAdded in v2.26.0Maximum auth attempts per window (default: 40)Use 0 to disable rate limiter
- Maximum auth attempts per window (default: 40)
- Use 0 to disable rate limiter
- JWT_SECRET_KEYAdded in v2.26.0⚠ Warning: Do not change the secret on an existing server until the next mobile app release or the 3rd party app you are using has migrated. This will make the old tokens unusable so that only migrated apps can authenticate with your server.Secret used for signing the JSON Web Tokens (auto-generated if not provided)
- ⚠ Warning: Do not change the secret on an existing server until the next mobile app release or the 3rd party app you are using has migrated. This will make the old tokens unusable so that only migrated apps can authenticate with your server.
- Secret used for signing the JSON Web Tokens (auto-generated if not provided)
- ALLOW_CORS(default:'0')Allow Cross-Origin Resource Sharing if set to'1'.
- Allow Cross-Origin Resource Sharing if set to'1'.
- DISABLE_SSRF_REQUEST_FILTER(default:'0')Disables the security of using the "Server Side Request Forgery" filter.If you are self-hosting a podcast from the same server, you may need to disable the SSRF filter.
- Disables the security of using the "Server Side Request Forgery" filter.
- If you are self-hosting a podcast from the same server, you may need to disable the SSRF filter.
- SSRF_REQUEST_FILTER_WHITELISTA comma-separated whitelist of domains to exclude from the SSRF filter
- A comma-separated whitelist of domains to exclude from the SSRF filter
- ALLOW_IFRAME(default:'0')Allow use of iframes. This can also be done at the reverse proxy level.
- Allow use of iframes. This can also be done at the reverse proxy level.

`TOKEN_SECRET`- Secret used for generating the JSON Web Tokens.
- If none is provided, a secure random token is generated automatically.
That will usually be sufficient.

`ACCESS_TOKEN_EXPIRY`- Access token expiration in seconds (default: 43200 = 12 hours)

`REFRESH_TOKEN_EXPIRY`- Refresh token expiration in seconds (default: 604800 = 7 days)

`RATE_LIMIT_AUTH_WINDOW`- Rate limiting window in milliseconds (default: 600000 = 10 minutes)

`RATE_LIMIT_AUTH_MAX`- Maximum auth attempts per window (default: 40)
- Use 0 to disable rate limiter

`JWT_SECRET_KEY`- ⚠ Warning: Do not change the secret on an existing server until the next mobile app release or the 3rd party app you are using has migrated. This will make the old tokens unusable so that only migrated apps can authenticate with your server.
- Secret used for signing the JSON Web Tokens (auto-generated if not provided)

`ALLOW_CORS``'0'`- Allow Cross-Origin Resource Sharing if set to'1'.

`'1'``DISABLE_SSRF_REQUEST_FILTER``'0'`- Disables the security of using the "Server Side Request Forgery" filter.
- If you are self-hosting a podcast from the same server, you may need to disable the SSRF filter.

`SSRF_REQUEST_FILTER_WHITELIST`- A comma-separated whitelist of domains to exclude from the SSRF filter

`ALLOW_IFRAME``'0'`- Allow use of iframes. This can also be done at the reverse proxy level.

## tagOther

- SOURCEInstallation source. Will be shown in the web client.Usually set todocker,debianorrpm.
- Installation source. Will be shown in the web client.
- Usually set todocker,debianorrpm.
- NODE_ENV(default:production)Type of deployment.Should beproductionunless usingdevelopment.
- Type of deployment.
- Should beproductionunless usingdevelopment.
- PODCAST_DOWNLOAD_TIMEOUT(default:30seconds)Timeout to wait for a podcast to start downloading.
- Timeout to wait for a podcast to start downloading.
- QUERY_LOGGINGDebug information for logging SQL queriesUselogto log the queries, andbenchmarkto also log the runtime of each query.
- Debug information for logging SQL queries
- Uselogto log the queries, andbenchmarkto also log the runtime of each query.
- QUERY_PROFILINGExperimental profiling of specific database queries. Not implemented on most queries.
- Experimental profiling of specific database queries. Not implemented on most queries.
- SQLITE_MMAP_SIZESet themmap_sizepragma for the SQLite database
- Set themmap_sizepragma for the SQLite database
- SQLITE_CACHE_SIZESet thecache_sizepragma for the SQLite database
- Set thecache_sizepragma for the SQLite database
- SQLITE_TEMP_STORESet thetemp_storepragma for the SQLite database
- Set thetemp_storepragma for the SQLite database

`SOURCE`- Installation source. Will be shown in the web client.
- Usually set todocker,debianorrpm.

`docker``debian``rpm``NODE_ENV``production`- Type of deployment.
- Should beproductionunless usingdevelopment.

`production``development``PODCAST_DOWNLOAD_TIMEOUT``30`- Timeout to wait for a podcast to start downloading.

`QUERY_LOGGING`- Debug information for logging SQL queries
- Uselogto log the queries, andbenchmarkto also log the runtime of each query.

`log``benchmark``QUERY_PROFILING`- Experimental profiling of specific database queries. Not implemented on most queries.

`SQLITE_MMAP_SIZE`- Set themmap_sizepragma for the SQLite database

`mmap_size``SQLITE_CACHE_SIZE`- Set thecache_sizepragma for the SQLite database

`cache_size``SQLITE_TEMP_STORE`- Set thetemp_storepragma for the SQLite database

`temp_store`# tagDirectory Structure

Here is an example supported directory structure for Books

Terry Goodkind

Sword of Truth

Vol 1 - 1994 - Wizards First Rule {Sam Tsoutsouvas}

Audio Track 1.mp3

Audio Track 2.mp3

Cover.jpg

Vol 2 - 1995 - Stone of Tears

Audiobook.m4b

Heart of Black Ice - Sister of Darkness

Audio File.m4a

Steven Levy

Hackers - Heroes of the Computer Revolution {Mike Chamberlain}

Audio File.m4a

1945 - Animal Farm

Audiobook.mp3

Animal Farm.m4b

Books are designated by folders. Any audio files (or ebook files) within a folder will be grouped into that book, except in the root folder where each audio file will be treated as an individual book.

# tagTitle Folder Naming

In addition to the book title, the title folder can include the publish year, series sequence, the subtitle, and the narrator.

Here are a bunch of ways the same book could be named:

Wizards First Rule

Wizards First Rule {Sam Tsoutsouvas}

1994 - Wizards First Rule

Wizards First Rule - A Really Good Subtitle

1994 - Book 1 - Wizards First Rule

1994 - Volume 1. Wizards First Rule {Sam Tsoutsouvas}

Vol 1 - 1994 - Wizards First Rule

1994 - Wizards First Rule - Volume 1

Vol. 1 - 1994 - Wizards First Rule - A Really Good Subtitle {Sam Tsoutsouvas}

(1994) - Wizards First Rule - A Really Good Subtitle

1 - Wizards First Rule

1. Wizards First Rule

- Subtitle:Parsing out subtitles into a separate field is optional and must be enabled in settings. Subtitle must be separated by " - ".
- Series Sequence:Case insensitive & decimals supported.
- The sequence can be placed anywhere in the folder name.
- It must be followed by " - " or ". "
- If it is not at the beginning of the folder name, it must be preceded by " - " and "Vol" "Vol." "Volume" or "Book"
- Publish Year:The publish year must be the first part of the name OR directly after a series sequence, and separated by " - " on both sides.
- Narrator:Must be wrapped in curly braces. e.g. {Sam Tsoutsouvas}.
- Disc Numbers:The title folder can contain subfolders for discs as long as they are named "Disc", "CD", or "Disk" with a number following (case insensitive). Example: "Disc 1", "CD 2", "Disk 3", "Disc 004", or no space between like "Disc1".

- The sequence can be placed anywhere in the folder name.
- It must be followed by " - " or ". "
- If it is not at the beginning of the folder name, it must be preceded by " - " and "Vol" "Vol." "Volume" or "Book"

# tagAuthor Folder Naming

Supports "Last, First" author naming as well as multiple authors separated by ",", ";", "&" or "and".Valid author folder names:

Ichiro Kishimi

Kishimi, Ichiro

Ichiro Kishimi, Fumitake Koga

Kishimi, Ichiro, Koga, Fumitake

Ichiro Kishimi & Fumitake Koga

Kishimi, Ichiro & Koga, Fumitake

Terry Goodkind, Ichiro Kishimi and Fumitake Koga

# tagAudio Metadata

Audiobookshelf uses the ID3 metadata tags in audio files to populate data.

Ensure your settings for themetadata priority settingsmatches your file structure.

Metadata on audio files will be mapped as follows (second tag after "/" is a fallback):

*Genre meta tag can include multiple genres separated by "/", "//", or ";". e.g. "Science Fiction/Fiction/Fantasy"

**Chapter extraction from Overdrive MediaMarkers must be enabled in your server settings

Embedded cover art will be extracted and used only if there are no images in the book folder.

# tagAudio Tracks

An audiobook contains tracks. Tracks are audio files assigned a track number.The track number is parsed from the audio filename and from the ID3 tags of the audio file.Audiobooks that are made up of multiple discs or cd's will be ordered first by disc number then by track number.

The scanner will choose the more accurate track/disc number between the filename and ID3 tag numbers.

Tracks can be manually ordered and enabled/disabled by pressing the "Manage Tracks" button on the audiobook page.

# tagAdditional Metadata

If you have a file nameddesc.txtin the library item folder it will be used as the description.

If you have a file namedreader.txtin the library item folder it will be used as the narrator.

If you have anOPF filewith extension.opfin the library item folder it will be parsed.Details extracted from OPF:

# tagDirectory Structure

Here is an example supported directory structure for Podcasts

Lex Fridman Podcast

#219 – Donald Knuth.mp3

#252 – Elon Musk.mp3

Cover.jpg

Self-Hosted

#69 - Get Off My Lawn.mp3

Podcasts only support a flat directory structure for each podcast (meaning no season folders). All episodes and the cover image must be in the same podcast folder.


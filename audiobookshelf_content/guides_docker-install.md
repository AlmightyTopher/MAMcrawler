# audiobookshelf

**Source:** https://www.audiobookshelf.org/guides/docker-install

**Crawled:** 2025-11-27 21:19:06

---

# Docker Windows Install

# tagHow to Install ABS on Windows (Portainer Method)

> Thanks to EvilSerenityReborn onDiscordfor this contribution! <

> 💡Already know docker? Take a look at ourDocker run command.

💡Already know docker? Take a look at ourDocker run command.

`💡`### tagPhase 1: Installation + Initial Setup

Step 1: Install Docker Desktop for Windows

Install on Windows

### tagPhase 2:

- Run DockerDesktop.exe
- After Docker starts, you can click “Add Extensions” on the left pane.
- Search for Portainer, click Install, and once done, Open it.
- The home page should greet you with this layout:



- Click on the “local” environment



- Click on “Stacks”



- And then click on “Add Stack” on the top right
- Name your stack (I did “audiobookshelf”), and be sure your build method is Web Editor (for sake of ease)



- Head over here:https://www.audiobookshelf.org/docs#docker-compose-installAnd copy/paste the contents into the Web Editor in Docker Desktop:
- And copy/paste the contents into the Web Editor in Docker Desktop:
- IMPORTANT - YOU HAVE TO CHANGE THE PATHS IN THE VOLUMES SECTION (the <> stuff)
- This is what mine looks like. Yes, you have to remove the < > as well. I just use one volume per library as well as run abs under its own unprivileged user, so I have theuser: <UID>:<GID>variable filled in.

Head over here:https://www.audiobookshelf.org/docs#docker-compose-install

- And copy/paste the contents into the Web Editor in Docker Desktop:

IMPORTANT - YOU HAVE TO CHANGE THE PATHS IN THE VOLUMES SECTION (the <> stuff)

This is what mine looks like. Yes, you have to remove the < > as well. I just use one volume per library as well as run abs under its own unprivileged user, so I have theuser: <UID>:<GID>variable filled in.

`user: <UID>:<GID>`

- Once edited, scroll down and click “Deploy”

### tagPhase 3: THE SET UP

- Open up your favorite browser and go to:localhost:13378If you want to find your device IP address, open up powershell and type:
- localhost:13378
- If you want to find your device IP address, open up powershell and type:

- localhost:13378
- If you want to find your device IP address, open up powershell and type:

```
Get-NetIPAddress -AddressFamily IPV4

```

`Get-NetIPAddress -AddressFamily IPV4````
  - Look for the one that starts with 192.168 or 10.0 … and then tack on the port
     - 192.168.12.345:13378 [example]

```

`- Look for the one that starts with 192.168 or 10.0 … and then tack on the port
     - 192.168.12.345:13378 [example]`- You should be greeted with the ABS page, so go ahead and create your account and set up your library (add library, name it, select the folder your audiobooks are in, etc.)

### tagPhase 4: Opening Ports so you can access remotely

- Warning!Opening the port on your router is the easiest way to access ABS outside of your home network but it is not secure. A secure way to do this is to setup areverse proxy.
- I’d recommend making your device’s IP static (google instructions), and then setting up port forwarding on your router to point to that local IP address:13378 port
- You may also have to open up ports on your firewall (google instructions)
- All that’s left is to find your public IPv4 address (https://whatismyipaddress.com) and using that as your server login instead of the localhost/localip.So 58.49.293.123:13378 [public] instead of 192.168.12.345:13378 [local]
- So 58.49.293.123:13378 [public] instead of 192.168.12.345:13378 [local]

- So 58.49.293.123:13378 [public] instead of 192.168.12.345:13378 [local]

### tagEXTRA - UPDATING ABS

- ABS will tell you when there is an update if you look at the lower left corner of your ABS web client



- First, stop the ABS stack in Portainer (go to stacks on the left pane, click on the stack, and click on “stop this stack”)



- go to the Images tab there and delete the audiobookshelf image.



- Then go back to the Stacks tab and start up your ABS stack.


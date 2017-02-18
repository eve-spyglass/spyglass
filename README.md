
<p align="center">
  <img align="middle" src="http://www.crypta.tech/wp-content/uploads/2017/02/logo.png">
</p>

<p>

<p align="center">
"Casting his sight on his realm, the Lord witnessed<br>
The cascade of evil, the torrents of war.<br>
Burning with wrath, He stepped<br>
down from the Heavens<br>
To judge the unworthy,<br>
To redeem the pure."<br>
<b>- The Scriptures, Book II, Revelations 2:12</b> <br>
</p>

# Welcome To Provi I: The Eye of Providence

Provi I: The Eye of Providence is an intel visualisation and alarm system for [EVE Online](http://www.eveonline.com). This too gathers information from in game chat channels and presents the data on a [dotlan](http://evemaps.dotlan.net/map/Catch#npc24) generated map. The map is highlighted in real time as players report intel in monitored chat channels.

Provi I is written with Python 2.7, using PyQt4 for the graphical interface, BeautifulSoup4 for SVG parsing, and Pyglet for audio playback.

### News
-The current release version of Provi I [can be found here](http://www.crypta.tech/provi-i-the-eye-of-providence) at the bottom of the page or on the [GitHub releases page](https://github.com/Crypta-Eve/provi-i/releases).


## Screenshot

![](http://www.crypta.tech/wp-content/uploads/2017/02/VI_px.png)

## Features

 - Platforms supported: Mac, Windows and Linux.
 - A pilot may be KOS-checked right from in-game chat channels.
 - Quick batch KOS-checking of the Local system when foregrounding Provi I.
 - Monitored intel chat channels are merged to one chat stream. You can add or remove channels via a menu option.
 - An interactive map of Providence / Catch is provided. Systems on the map display real-time intel data as reported through intel channels.
 - Systems on the map display different color backgrounds as their alarms age, with text indicating how long ago the specific system was reported. Background color becomes red when a system is reported and lightens (red->orange->yellow->white) in the following intervals: 4min, 10min, 15min, and 25min.
 - Systems reported clear display on the map with a green background for 10 minutes.
 - Clicking on a specific system will display all messages bound on that system in the past 20 minutes. From there one can can set a system alarm, set the systems clear or set it as the current system for one or more of your characters.
 - Clicking on a system in the intel channel (right hand column) causes it to be highlighted on the map with a blue background for 10 seconds.
 - The system where your character is currently located is highlighted on the map with an violet background automatically whenever a character changes systems.
 - Alarms can be set so that task-bar notifications are displayed when an intel report calls out a system within a specified number of jumps from your character(s). This can be configured from the task-bar icon.
 - The main window can be set up to remain "always on top" and be displayed with a specified level of transparency.
 - Ship names in the intel chat are marked blue.

## Usage

 - Manually checking pilot(s) using an EVE client chat channel:
 Type xxx in any chat channel and drag and drop the pilots names after this. (e.g., xxx [Xanthos](http://image.eveonline.com/Character/183452271_256.jpg)). Provi I recognizes this as a request and checks the pilots listed.
 - Checking all pilots in the local system:
This option must first be activated by checking the Provi I app menu: Menu > Auto KOS-Check Clipboard.
To use this feature: click on a pilot in the local pilot list and then type the shortcuts for select-all and copy-selection. This places the pilots in local on your clipboard. Next switch to the Provi I app momentarily and back to Eve. KOS checking of these pilots will continue in the background.


## KOS Results

"KOS" status values reported by Provi I

 - **KOS**: the pilot is known as KOS to the alliance and has been marked as such in the KOS-checker system.
 - **RED by last**: the last player (non-NPC) corp in the pilot's employment history is KOS.
 - **Not KOS**: the pilot is known as NOT KOS to the alliance and has been marked as such in the KOS-checker system.
 - **? (Unknown)**: the pilot is not known by the KOS-checker system and there are no hostile corporations in her employment history.


## Running Provi I from Source

To run or build from the source you need the following packages installed on your machine. Most, if not all, can be installed from the command line using package management software such as "pip". Mac and Linux both come with pip installed, Windows users may need to install [cygwin](https://www.cygwin.com) to get pip. Of course all the requirements also have download links.

The packages required are:
- Python 2.7.x
https://www.python.org/downloads/
Provi I is not compatible with Python 3!
- PyQt4x
http://www.riverbankcomputing.com/software/pyqt/download
Please use the PyQt Binary Package for Py2.7
Provi I is not compatible with PyQt5!
- BeautifulSoup 4
https://pypi.python.org/pypi/beautifulsoup4
- Pyglet 1.2.4 (for python 2.7)
https://bitbucket.org/pyglet/pyglet/wiki/Download
pyglet is used to play the sound – If it is not available the sound option will be disabled.
- Requests 2
https://pypi.python.org/pypi/requests
- Six for python 3 compatibility https://pypi.python.org/pypi/six
- pyttsx for text to speech

## The background Provi I

Provi I is a project aimed at the continuation to the work done on the Vintel tool by [Xanthos](https://github.com/Xanthos-Eve) which can be found [here](https://github.com/Xanthos-Eve/vintel).

## FAQ

**License?**

Provi I is licensed under the [GPLv3](http://www.gnu.org/licenses/gpl-3.0.html).

**Provi I does not play sounds - is there a remedy for this?**

The most likely cause of this is that pyglet is not installed.

**A litte bit to big for such a little tool.**

The .exe ships with the complete environment and needed libs. You could save some space using the the source code instead.

**What platforms are supported?**

Provi I runs on Mac (OS X), Windows and Linux. Windows standalone packages are provided with each release. Linux users are advised to install all the requirements listed above then download and run from source.

**What file system permissions does Provi I need?**

- It reads your EVE chatlogs
- It creates and writes to **path-to-your-chatlogs**/../../provii/.
- It needs to connect the internet (dotlan.evemaps.net, eveonline.com, cva-eve.org, and eve gate).

**Provi I calls home?**

Yes it does. If you don't want to this, use a firewall to forbid it.
Provi I looks for a new version at startup and loads dynamic infomation (i.e., jump bridge routes) from home. It will run without this connection but some functionality will be limited.

**Provi I does not find my chatlogs or is not showing changes to chat when it should. What can I do?**

Provi I looks for your chat logs in ~\EVE\logs\chatlogs and ~\DOCUMENTS\EVE\logs\chatlogs. Logging must be enabled in the EVE client options. You can set this path on your own by giving it to Provi I at startup. For this you have to start it on the command line and call the program with the path to the logs.

Examples:

`win> provii-1.0.0.exe "d:\strange\path\EVE\logs\chatlogs"`

    – or –

`linux and mac> python provii.py "/home/user/myverypecialpath/EVE/logs/chatlogs"`

**Provi I does not start! What can I do?**

Please try to delete Provi I's Cache. It is located in the EVE-directory where the chatlogs are in. If your chatlogs are in \Documents\EVE\logs\chatlogs Provi I writes the cachte to \Documents\EVE\provii

**Provi I takes many seconds to start up; what are some of the causes and what can I do about it?**

Provi I asks the operating system to notifiy when a change has been made to the ChatLogs directory - this will happen when a new log is created or an existing one is updated. In response to this notification, Provi I examines all of the files in the directory to analysze the changes. If you have a lot of chat logs this can make Provi I slow to scan for file changes. Try perodically moving all the chatlogs out of the ChatLogs directory (zip them up and save them somewhere else if you think you may need them some day).

**Provi I complains about missing dll files on Windows at app launch, is there a workaround for this?**

Yes there is! There is a bit of a mix up going on with the latest pyinstaller and the Microsoft developer dlls. Here is a link to help illuminate the issue https://github.com/pyinstaller/pyinstaller/issues/1974

You can visit Microsoft's web site to download the developer dlls https://www.microsoft.com/en-in/download/details.aspx?id=5555.

You can also read a more technical treatment of the issue here http://www.tomshardware.com/answers/id-2417960/msvcr100-dll-32bit-64bit.html

**How can I resolve the "empty certificate data" error?**

Do not use the standalone EXE, install the environment and use the sourcecode directly. There are missing certificates that must be provided by the environment. This error was discovered when running the standalone EXE on Linux using wine.

**Provi I is misbehaving and I dont know why - how can I easily help diagnose problems with Provi I**

Provi I writes its own set of logs to the \Documents\EVE\provii\logs directory. A new log is created as the old one fills up to its maximum size setting. Each entry inside the log file is time-stamped. These logs are emitted in real-time so you can watch the changes to the file as you use the app.

**I love Provi I - how can I help?**

If you are technically inclined and have a solid grasp of Python, [contact the project maintainer via email](mailto:crypta@crypta.tech) to see how you can best help out. Alternatively you can find something you want to change and create a pull request to have your changes reviewed and potentially added to the codebase. There have been several great contributions made this way!

**I'm not a coder, how can I help?**

Your feedback is needed! Use the program for a while, then come back [here and create issues](https://github.com/Crypta-Eve/provi-i/issues). Record anything you think about Provi I - bugs, frustrations, and ideas to make it better.

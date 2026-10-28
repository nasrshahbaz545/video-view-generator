VIDEO PLAYBACK LOAD TESTER v1.0.0
=================================

PURPOSE
-------
A Windows BAT-launched Python utility for local video playback QA and PC load testing.
It can open 1-50 isolated browser contexts, attempt muted autoplay, monitor CPU/RAM,
record a CSV log, close contexts at a timer, and repeat for a chosen number of cycles.

IMPORTANT BOUNDARY
------------------
Public-internet targets are intentionally blocked. Use only:
- A video file stored on your PC (for example C:\Videos\test.mp4)
- http://localhost:PORT/...
- A private-LAN address such as http://192.168.1.20/video.html

This prevents the tool from being used to manufacture views, traffic, or engagement.
It does not bypass a website's autoplay rules, anti-abuse systems, or browser throttling.

INSTALL ONCE
------------
1. Install Python 3.11 or newer and select "Add Python to PATH".
2. Double-click install_requirements.bat.
3. Wait while Playwright Chromium and Firefox are installed.

RUN
---
1. Double-click run_utility.bat.
2. Enter a local file or localhost/private-LAN URL.
3. Choose Chromium, installed Chrome, installed Edge, or Firefox.
4. Enter context count, timer, batch size, launch delay, cycles, and headless option.
5. Press Ctrl+C at any time to request shutdown.

BROWSER NOTES
-------------
- Chromium and Firefox are installed by install_requirements.bat.
- Chrome and Edge options use browsers already installed on Windows.
- Internet Explorer is not supported. Choose Microsoft Edge.
- Background playback is attempted through browser preferences and JavaScript, but no
  utility can guarantee continuous playback on every site/player/browser combination.

SAFETY
------
- Launch pauses at 88% RAM.
- Launch stops at 92% RAM.
- During monitoring, contexts are closed if RAM reaches 92%.
- Contexts are reduced after CPU stays at 98% for 15 seconds.
- Maximum contexts: 50.
- Close other heavy programs and monitor system temperature separately.
- The utility reads NVIDIA GPU temperature when nvidia-smi is available, but it does
  not enforce a GPU-temperature limit because the command may be absent or report
  different hardware configurations.

OUTPUT
------
stress_log.csv is recreated on every run. It contains:
timestamp, cycle, phase, CPU %, RAM %, RAM used GB, GPU temperature, active contexts,
and safety/lifecycle events.

FILES
-----
run_utility.bat             Main launcher
install_requirements.bat    One-time dependency installer
main.py                     Engine
requirements.txt            Python packages
README.txt                  This guide

LIMITATION
----------
This package was syntax-checked in a Linux build environment. Actual browser launch and
Windows BAT behavior must be tested on your Windows 10/11 PC after installation.

* Download Youtube livestreams from the very beginning to the end.
* Monitor a given channel for upcoming livestreams and download them automatically when they become active.

Cookies (in Netscape format) are needed to access membership-only videos as well as age-restricted videos (which would also mean that you sold your soul to Youtube and your account is "verified").

The example config file `livestream_saver.cfg` is optional and is meant as a convenience to override the default values.


# Monitoring a channel

Monitor a given Youtube channel for any upcoming livestream by requesting the channel's *videos* and *community* tabs every few minutes or so. 
It should automatically download a live stream as soon as one is listed as being active in any of said tabs.

Basic usage example: `python livestream_saver.py monitor --cookie /path/to/cookie.txt CHANNEL_URL`

```
> python3 livestream_saver.py monitor --help

usage: livestream_saver.py monitor [-h] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [-c CONFIG_FILE] [--cookie COOKIE_PATH] [-q MAX_VIDEO_QUALITY] [-o OUTPUT_DIR] [--channel-name CHANNEL_NAME] [-s SECTION] [-d] [-n] [-k] [--scan-delay SCAN_DELAY] [--email-notifications] [--skip-download] [YOUTUBE_CHANNEL_URL]

positional arguments:
  YOUTUBE_CHANNEL_URL   The Youtube channel to monitor for live streams. Either a full youtube URL, /channel/ID, or /c/name format. (default: None)

optional arguments:
  -h, --help            show this help message and exit
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Log level. (Default: INFO)
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Path to config file to use. (Default: ~/.config/livestream_saver/livestream_saver.cfg)
  --cookie COOKIE_PATH  Path to Netscape formatted cookie file.
  -q MAX_VIDEO_QUALITY, --max-video-quality MAX_VIDEO_QUALITY
                        Use best available video resolution up to this height in pixels. Example: "360" for maximum height 360p. Get the highest available resolution by default.
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Output directory where to save channel data. (Default: CWD)
  --channel-name CHANNEL_NAME
                        User-defined name of the channel to monitor. Will fallback to channel ID deduced from the URL otherwise.
  -s SECTION, --section SECTION
                        Override values from the section [monitor NAME] found in config file. If none is specified, will load the first section in config with that name pattern. (default: None)
  -d, --delete-source   Delete source segment files once the final merging of them has been done. (default: False)
  -n, --no-merge        Do not merge segments after live streams has ended. (default: False)
  -k, --keep-concat     Keep concatenated intermediary files even if merging of streams has been successful. Only useful for troubleshooting. (default: False)
  --scan-delay SCAN_DELAY
                        Interval in minutes to scan for channel activity. (Default: 15.0)
  --email-notifications
                        Enables sending e-mail reports to administrator. (Default: False)
  --skip-download       Skip the download phase (useful to run hook scripts instead). (Default: False)
```

# Downloading a live stream

Downloads an active Youtube livestream specified by its URL.

Basic usage example: `python livestream_saver.py download --cookie /path/to/cookie.txt VIDEO_STREAM_URL`

```
> python3 livestream_saver.py download --help

usage: livestream_saver.py download [-h] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [-c CONFIG_FILE] [--cookie COOKIE_PATH] [-q MAX_VIDEO_QUALITY] [-o OUTPUT_DIR] [-d | -n] [-k] [--scan-delay SCAN_DELAY] [--email-notifications] [--skip-download] YOUTUBE_VIDEO_URL

positional arguments:
  YOUTUBE_VIDEO_URL     Youtube video stream URL to download.

optional arguments:
  -h, --help            show this help message and exit
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Log level. (Default: INFO)
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Path to config file to use. (Default: ~/.config/livestream_saver/livestream_saver.cfg)
  --cookie COOKIE_PATH  Path to Netscape formatted cookie file.
  -q MAX_VIDEO_QUALITY, --max-video-quality MAX_VIDEO_QUALITY
                        Use best available video resolution up to this height in pixels. Example: "360" for maximum height 360p. Get the highest available resolution by default.
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Output directory where to write downloaded chunks. (Default: CWD)
  -d, --delete-source   Delete source files once final merge has been done. (default: False)
  -n, --no-merge        Do not merge segments after live streams has ended. (default: False)
  -k, --keep-concat     Keep concatenated intermediary files even if merging of streams has been successful. Only useful for troubleshooting. (default: False)
  --scan-delay SCAN_DELAY
                        Interval in minutes to scan for status update. (Default: 2.0)
  --email-notifications
                        Enable sending e-mail reports to administrator. (Default: False)
  --skip-download       Skip the download phase (useful to run hook scripts instead). (Default: False)
```

# Merging segments

The *download* sub-command above should automatically merge the downloaded segments once the live stream has ended. If it failed for whatever reason, this sub-command can be invoked on the directory path to the downloaded segments. That directory should be named something like "stream_capture_{VIDEO_ID}".

Basic usage example: `python livestream_saver.py merge /path/to/stream_capture_{VIDEO_ID}` (Windows users should use `py livestream_saver.py`)

```
> python3 livestream_saver.py merge --help

usage: livestream_saver.py merge [-h] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [-c CONFIG_FILE] [-d] [-k] [-o OUTPUT_DIR] PATH

positional arguments:
  PATH                  Path to directory holding vid/aud sub-directories in which segments have been downloaded as well as the metadata.txt file.

optional arguments:
  -h, --help            show this help message and exit
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Log level. (Default: INFO)
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Path to config file to use. (Default: ~/.config/livestream_saver/livestream_saver.cfg)
  -d, --delete-source   Delete source files (vid/aud) once final merging of streams has been successfully done. (default: False)
  -k, --keep-concat     Keep concatenated intermediary files even if merging of streams has been successful. This is only useful for debugging. (default: False)
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Output directory where to write final merged file. (default: None)
```

# Dependencies

* python 3.8
* [pytube](https://github.com/pytube/pytube) 10.9.2
* ffmpeg (and ffprobe) to concatenate segments and merge them into one file 
* [Pillow](https://pillow.readthedocs.io/en/stable/installation.html) (optional) to convert webp thumbnail

# Installation

Either install dependencies system-wide (requires root privileges, use `sudo`):
```
python3 -m pip install -r requirements.txt
``` 
Or create a virtual environment and install the dependencies inside it, but do note that in this case you will need to activate the venv everytime you need to run the program.
```
virtualenv -p python3 venv
source ./venv/bin/activate
pip3 install -r requirements.txt
```
One could also clone the corresponding repositories manually to get the latest updates.

# Configuration

The template config file `livestream_saver.cfg.template` is provided as an example. The default path should be `~/.config/livestream_saver/livestream_saver.cfg` (On Windows, it is read directly from your base user directory).
A lot of options can be overriden via command line arguments. See the --help message for details.

A monitor section for a specific channel can be invoked from the CLI with `--section NAME` where `NAME` is the same string of characters from `[monitor NAME]` in the config file. This helps having one central config file. By default, the first section with this pattern will be loaded if none has been specified on the command line.

## On-download started hook

You can spawn a process of your choosing on various events (see config file template). This can be useful to spawn youtube-dl (yt-dlp) in parallel for example.
Note that these hooks can only be specified in a config file. Example:
```ini
# Call this program whenever a download is starting (the live stream might be pending still)
on_download_initiated = yt-dlp --add-metadata --embed-thumbnail --wait-for-video 5 %VIDEO_URL%
```
The following place-holders will be replaced by the corresponding value (more will be added in the future):
- `%VIDEO_URL%`: the URL of the live stream being currently downloaded
- `%COOKIE_PATH%`: the path to the cookie file you have specified (in config, or CLI argument)

Each section (`[monitor]`, `[download]` and `[monitor CHANNEL]`) can have a different value for the same option / event. The `[DEFAULT]` section is only used as a fallback if none of them have an expected value specified. The `[monitor CHANNEL]` section will override any value from the `monitor` section, so you can specify different programs for different channels for example.
The command can be disabled and its output logged with the following options (placed in the **same section** as the affected command). Additionally, regex can be used to narrow own when to spawn a command based on the targeted video's metadata:
```ini
# Disable spawning the command above (same as commenting the command out)
on_download_initiated_enabled = false

# Log command's output (both stdout & stderr)
on_download_initiated_logged = true

# The command will only spawn if these expressions match against the video title + description:
on_download_initiated_allow_regex = ".*archiv.*|.*sing.*"

# The command will not spawn if these expressions match (honestly, this is not that useful, so don't use it): 
on_download_initiated_block_regex = ".*pineapple.*|.*banana.*"
```
You can also skip the downloading phase every time with the following option:
```ini
# Skip download phase and only run the subprocess when a stream has started
skip_download = true
```
This is useful if you only want to run yt-dlp (or any other program) when livestream_saver has detected an active broadcast but you don't care about downloading with livestream_saver. This option in particular can be specified in **any** section, even on the command line with argument `--skip-download`.


## Notifications via e-mail

The e-mail options can be overriden via environment variables if you find it more secure.
Login and password are not mandatory. That depends on your smtp server configuration.
You can send a test e-mail notification with this sub-command: 
```
livestream_saver.py test-notification
```
Whenever a crash, or an error occurs, the program should send you a notification at the configured e-mail address via the configured smtp server.

# License

GPLv3

# Notes:

This is beta software. It should work, but in case it doesn't, feel free to report issues. Or better yet, fix them yourself and submit a merge request. Keep in mind that these mega corporations will often attempt to break our things.

# TODO

* Better stream quality selection (webm, by fps, etc.).
* Use other libs (yt-dlp, streamlink) as backends for downloading fragments.
* Add proxy support.
* Fetch segments in parallel to catch up faster.
* Make sure age-restricted videos are not blocked (we rely on Pytube for this).
* Monitor Twitch channels.
* Make Docker container.
* Make web interface.

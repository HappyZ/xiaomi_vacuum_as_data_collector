# Prerequisite

Follow https://gitlab.com/EECE-5698-Group-7/vacuum-repo to root your vacuum (use `imagebuilder.sh` at your own risk).

Install `python3-minimal` using `apt`.

After rooted, need to start the vacuum in `unprovisioned mode` (by pressing the `reset` button on vacuum lightly).

## Unprovisioned mode setup (if not included in rooted image)
#### 1. in /etc/rc.local, add the following line
```
/opt/unprovisioned/start_wifi.sh >/dev/null 2>&1
```

#### 2. create a foler at `/opt/`
```
mkdir /opt/unprovisioned/
```

#### 3. create file `/opt/unprovisioned/wpa_supplicant.conf`:
```
network={
    ssid="<ssid name>"
    scan_ssid=1
    proto=RSN
    key_mgmt=WPA-PSK
    pairwise=CCMP
    group=CCMP
    psk="<password>"
}
```

#### 4. create file `/opt/unprovisioned/start_wifi.sh`:
```
#!/bin/bash

file="/opt/unprovisioned/wpa_supplicant.conf"
if [ ! -f "$file" ]
then
    echo "$0: File '${file}' not found." > "/opt/unprovisioned/log.log"
else
    #add enough time to fix wrong wireless settings
    sleep 200

    #disable accesspoint
    ifdown wlan0 > /dev/null 2>&1
    ifconfig wlan0 down > /dev/null 2>&1
    killall hostapd >/dev/null 2>&1
    iw mon.wlan0 del >/dev/null 2>&1
    create_ap --stop wlan0 > /dev/null 2>&1
    killall wpa_supplicant >/dev/null 2>&1
    killall dhclient >/dev/null 2>&1

    ifconfig >> /opt/unprovisioned/log.log

    #login to your network
    ifconfig wlan0 up >/dev/null 2>&1
    /sbin/wpa_supplicant -s -B -P /var/run/wpa_supplicant_1.wlan0.pid -i wlan0 -D nl80211,wext -c /opt/unprovisioned/wpa_supplicant.conf -C /var/run/wpa_supplicant >/dev/null 2>&1
    echo "done!" >> /opt/unprovisioned/log.log
    dhclient wlan0 >/dev/null 2>&1
fi
```

#### 5. Restart vacuum


# Tools Usage

```
python controller.py
```

## Update scripts on vacuum

If in any case the script has been modified, we need to use `init_vacuum.sh` to update the scripts on vacuum. Run it within the python script via `update` so it takes in the discovered vacuum IP. 

Otherwise, you can also set environment variable `MIROBO_IP` and run `./init_vacuum.sh` directly.

## Control vacuum

Type `control` to enter the control panel

Available commands can be found via `help` in control panel:
```
control >>> help
Control Command Menu
help                         - this message
home                         - move vacuum to dock location
status                       - print the status of vacuum
start                        - automatically start one cleaning sesssion and get data
move auto/pause/stop/home    - auto scanning movement (no data parsing)
move rotate speed time       - move (-180, 180)deg at (-0.3,0.3)m/s for `time`ms
fanspeed integer             - set fan speed to be [1-99]
goto x_coor y_coor           - move to x,y location on map
trace on/off                 - manually start/stop collecting trace
download trace/map           - download the trace or map on vacuum
config <cmds>                - configuration
quit/exit                    - exit controller (Ctrl + D does the same)
```

Example commands:
```
python controller.py
>>> control help
...
>>> control status
<VacuumStatus state=Cleaning, error=No error bat=93%, fan=1% cleaned 18.2775 m² in 0:16:12>
>>> control
control >>> help
...
control >>> start
Cleaning old data on device..
Enabling trace on the vacuum..
Starting..
<VacuumStatus state=Charging, error=No error bat=98%, fan=1% cleaned 2.6975 m² in 0:01:58>
...
control >>> config get remote_script_folder
/mnt/data/exp
```

## Config vacuum

Nothing much yet. But notice once you entered config panel, have to exit before doing any controls.
```
config >>> help
Config Command Menu
help             - this message
set <key> <val>  - set key value in config
get <key>        - get config from key, if `key` not set, print all
save/load <file> - save/load configuration from file (default: ./config.json)
quit/exit        - exit controller (Ctrl + D does the same)
```

Example commands:
```
>>> config get remote_script_folder
/mnt/data/exp
>>> config
config >>> get remote_script_folder
/mnt/data/exp
```


# Reference

1. [dustcloud](https://github.com/dgiese/dustcloud)
2. [aerodust](https://github.com/dgiese/aerodust)

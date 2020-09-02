A [kang (炕)](https://en.wikipedia.org/wiki/Kang_bed-stove) is a heating system in northern China.
This project is a project used to remote control a heating system using SMS.

# Dependencies #

Rasbian dependencies:

* python3-serial
* python3-rpi.gpio

Installing:

```
pip install .
cp kang.json /home/pi
cp authorized.txt /home/pi
```
Add the administrator phone number to the `kang.json` `admins` property.
Also add the phone numbers allowed to control the system using SMS in the `authorized.txt` file.

Enable the service to be started when the raspberry pi starts:

```
systemctl enable --now $PWD/kang.service
```

Accessing the logs:

```
journalctl -u kang
```

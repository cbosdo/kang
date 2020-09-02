A [kang (炕)](https://en.wikipedia.org/wiki/Kang_bed-stove) is a heating system in northern China.
This project is a project used to remote control a heating system using SMS.

# Dependencies #

Rasbian dependencies:

* python3-serial
* python3-rpi.gpio

Installing:

```
python3 ./setup.py install
systemctl enable --now /path/to/chauffage.service
```

Accessing the logs:

```
journalctl -u chauffage
```

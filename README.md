# UST Projector cabinet

![Render of cabinet](_docs/img/render.png)

### Setup

```python
# Connectivity
import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("Wuhuuu", "Kq4admD7EJJGDjl")
wlan.ifconfig()

# Installing libraries
import upip
#upip.install('micropython-ulogging')
# upip.install('uasyncio')
upip.install('picoweb')
upip.install('utemplate')
upip.install('micropython-pathlib')
```

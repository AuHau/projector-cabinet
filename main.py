import sys

import uasyncio as asyncio

OTA_REPO = "https://github.com/AuHau/projector-cabinet"


def connect_to_wifi():
    import time, network, gc, app.secrets as secrets
    time.sleep(1)
    print("Bootstrapping")
    print('=> Memory free', gc.mem_free())

    # network.hostname('projector_cabinet')
    wlan = network.WLAN(network.STA_IF)
    print(f"=> WiFi: {'connected - ' + wlan.ifconfig()[0] if wlan.isconnected() else 'NOT connected --> connecting'}")
    if not wlan.isconnected():
        wlan.active(True)
        time.sleep(1)
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASS)
        while not wlan.isconnected():
            pass

    print('=> Network config:', wlan.ifconfig())


def check_for_update():
    import machine, gc
    import ulogging as logging
    from uota import UOta

    print('=> Checking if new firmware version can be installed')
    ota = UOta(OTA_REPO, logger=logging.getLogger('UOta'))
    has_updated = ota.install_new_firmware()
    if has_updated:
        print('=> New version installed! Restarting!')
        machine.reset()
    else:
        del ota
        gc.collect()


def set_global_exception():
    def handle_exception(loop, context):
        import sys
        sys.print_exception(context["exception"])
        sys.exit()

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)


def start_app():
    print("Sys path: ", ",".join(sys.path))

    from app.main import main
    set_global_exception()  # Debug aid

    return main()


sys.path.append('/app')
sys.path.append('/app/lib')

connect_to_wifi()
check_for_update()

try:
    asyncio.run(start_app())
finally:
    asyncio.new_event_loop()  # Clear retained state

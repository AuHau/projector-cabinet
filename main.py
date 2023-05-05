import sys

import uasyncio as asyncio

# TODO: Add support for connection timeout

SRC_REPO = "https://github.com/AuHau/projector-cabinet"
UPDATE_CHECK_INTERVAL = 30 * 60  # Once in half an hour


def connect_to_wifi():
    import time, network, gc, app.secrets as secrets
    time.sleep(1)
    print("Bootstrapping")
    print('=> Memory free', gc.mem_free())

    wlan = network.WLAN(network.STA_IF)
    print(f"=> WiFi: {'connected - ' + wlan.ifconfig()[0] if wlan.isconnected() else 'NOT connected --> connecting'}")
    if not wlan.isconnected():
        wlan.active(True)
        time.sleep(1)
        wlan.config(dhcp_hostname='projector_cabinet')
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASS)
        while not wlan.isconnected():
            pass

    print('=> Network config:', wlan.ifconfig())


def check_for_update():
    import machine, gc
    from ota_updater import OTAUpdater

    print('=> Checking for new firmware version')
    ota_updater = OTAUpdater(SRC_REPO, main_dir='app', secrets_file="secrets.py")
    has_updated = ota_updater.install_update_if_available()
    if has_updated:
        print('=> New version installed! Restarting!')
        machine.reset()
    else:
        del ota_updater
        gc.collect()


def set_global_exception():
    def handle_exception(loop, context):
        import sys
        sys.print_exception(context["exception"])
        sys.exit()

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)


async def periodically_check_for_update():
    while True:
        await asyncio.sleep(UPDATE_CHECK_INTERVAL)
        check_for_update()


def start_app():
    print("Sys path: ", ",".join(sys.path))

    from app.main import main
    set_global_exception()  # Debug aid

    # TODO: Enable on release
    # asyncio.create_task(periodically_check_for_update())
    return main()


sys.path.append('/app')
sys.path.append('/app/lib')

connect_to_wifi()
# TODO: Enable on release
# check_for_update()

try:
    asyncio.run(start_app())
finally:
    asyncio.new_event_loop()  # Clear retained state

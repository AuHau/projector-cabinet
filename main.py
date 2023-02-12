import uasyncio as asyncio
import ulogging as logging
import network
from cabinet import cabinet, server, settings


async def main():
    set_global_exception()  # Debug aid
    logging.basicConfig(logging.DEBUG)
    print("Bootstrapping")

    print("=> Starting cabinet")
    cab = cabinet.Cabinet()
    cab.start()

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print(f"=> WiFi: {'connected - ' + wlan.ifconfig()[0] if wlan.isconnected() else 'NOT connected --> connecting'}")
    if not wlan.isconnected():
        wlan.connect(settings.WIFI_SSID, settings.WIFI_PASS)
        print("WiFi connected!")

    print("=> Starting HTTP server")
    server.start()

    print("Finished bootstrap")

    while True:
        await asyncio.sleep(10)


def set_global_exception():
    def handle_exception(loop, context):
        import sys
        sys.print_exception(context["exception"])
        sys.exit()

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)


try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()  # Clear retained state

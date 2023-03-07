import uasyncio as asyncio
import ulogging as logging
from cabinet import cabinet, server


async def main():
    logging.basicConfig(logging.DEBUG)

    print("=> Starting cabinet")
    cab = cabinet.Cabinet()
    cab.start()

    print("=> Starting HTTP server")
    server.start()

    print("Finished bootstrap")

    while True:
        await asyncio.sleep(10)

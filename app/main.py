import uasyncio as asyncio
import ulogging as logging
import gc

async def main():
    logging.basicConfig(logging.DEBUG)

    print("=> Starting MQTT")
    print('=> Memory free', gc.mem_free())
    from cabinet import mqtt
    mq = mqtt.MQTT()
    await mq.start()
    gc.collect()

    print("=> Starting cabinet")
    from cabinet import cabinet
    cab = cabinet.Cabinet()
    cab.start()
    gc.collect()

    print("=> Starting HTTP server")
    from cabinet import server
    server.start()
    gc.collect()

    print("Finished bootstrap")

    while True:
        await asyncio.sleep(10)

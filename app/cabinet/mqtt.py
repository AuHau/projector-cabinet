import ujson, gc
import ulogging as logging
import uasyncio as asyncio
from mqtt_as import MQTTClient, config

from cabinet import cabinet
from utils import singleton
from app import secrets

DEVICE_DEFINITION = {
    "name": "Projector cabinet",
    "configuration_url": "http://192.168.5.2",
    "manufacturer": "Adam Uhlir",
    "identifiers": ["cabinet_device"]
}

STATE_INTERVAL = 2000
CABINET_AVAILABILITY_TOPIC = "projector_cabinet/availability"

# Main on/off cabinet switch
SWITCH_DISCOVERY_TOPIC = "homeassistant/switch/projector_cabinet/main_switch/config"
SWITCH_STATE_TOPIC = "projector_cabinet/switch/state"
SWITCH_COMMAND_TOPIC = "projector_cabinet/switch/set"

# Temperature sensor
TEMP_DISCOVERY_TOPIC = "homeassistant/sensor/projector_cabinet/temp/config"
TEMP_STATE_TOPIC = "projector_cabinet/temp/state"


# Local configuration
config['ssid'] = secrets.WIFI_SSID
config['wifi_pw'] = secrets.WIFI_PASS
config['server'] = secrets.MQTT_BROKER
config['user'] = secrets.MQTT_USER
config['password'] = secrets.MQTT_PASS
config["queue_len"] = 1  # Use event interface with default queue size
config["will"] = (
    CABINET_AVAILABILITY_TOPIC, "offline", True, 0)  # This to let know Home Assistant that this device dropped from MQTT


@singleton
class MQTT:
    def __init__(self):
        self._logger = logging.getLogger('MQTT')
        MQTTClient.DEBUG = True
        self._client = MQTTClient(config, self._logger)
        self._cabinet = cabinet.Cabinet()
        self._state_loop = None
        self._topics_commands_mapping = {
            SWITCH_COMMAND_TOPIC: self._handle_switch_command
        }

    async def _handle_switch_command(self, msg):
        if msg == "ON":
            await self._cabinet.turn_on()
        elif msg == "OFF":
            await self._cabinet.turn_off()
        else:
            self._logger.error(f'Handling switch command, but got unknown command: {msg}')

        await self._client.publish(SWITCH_STATE_TOPIC, "ON" if self._cabinet.is_on() else "OFF")

    async def _messages(self):
        async for topic, msg, retained in self._client.queue:
            topic = topic.decode()
            msg = msg.decode()
            self._logger.debug(f'Topic "{topic}" got message "{msg}"')

            if topic in self._topics_commands_mapping:
                await self._topics_commands_mapping[topic](msg)
            else:
                self._logger.error(f'Unknown topic "{topic}"!')

    async def _down(self):
        while True:
            await self._client.down.wait()  # Pause until outage
            self._client.down.clear()
            self._logger.warning('WiFi or broker is down.')
            self._state_loop.cancel()

    async def _up(self):  # (re)connection.
        while True:
            await self._client.up.wait()
            self._client.up.clear()
            self._logger.info('We are connected to broker.')

            await self._announce_service_discovery()
            await self._client.subscribe(SWITCH_COMMAND_TOPIC, 1)
            await self._client.publish(CABINET_AVAILABILITY_TOPIC, "online")
            await self._client.publish(SWITCH_STATE_TOPIC, "ON" if self._cabinet.is_on() else "OFF")
            self._state_loop = asyncio.create_task(self._read_state())

    async def _read_state(self):  # send status data
        while True:

            await self._client.publish(TEMP_STATE_TOPIC, str(await self._cabinet.get_temp()))
            await asyncio.sleep_ms(STATE_INTERVAL)

    async def _announce_service_discovery(self):
        switch_discovery_payload = {
            "name": "Cabinet's switch",
            "unique_id": "projector_cabinet_switch",
            "command_topic": SWITCH_COMMAND_TOPIC,
            "state_topic": SWITCH_STATE_TOPIC,
            "availability_topic": CABINET_AVAILABILITY_TOPIC,
            "device": DEVICE_DEFINITION,
        }
        self._logger.info(f'Announcing cabinet capability on topic: {SWITCH_DISCOVERY_TOPIC}')
        await self._client.publish(SWITCH_DISCOVERY_TOPIC, ujson.dumps(switch_discovery_payload))

        temp_discovery_payload = {
            "name": "Cabinet's temperature",
            "unique_id": "projector_cabinet_temp",
            "state_class": "measurement",
            "device_class": "temperature",
            "native_unit_of_measurement": "C",
            "state_topic": TEMP_STATE_TOPIC,
            "availability_topic": CABINET_AVAILABILITY_TOPIC,
            "device": DEVICE_DEFINITION,
        }
        self._logger.info(f'Announcing cabinet capability on topic: {TEMP_DISCOVERY_TOPIC}')
        await self._client.publish(TEMP_DISCOVERY_TOPIC, ujson.dumps(temp_discovery_payload))

    async def start(self):
        await self._client.connect()
        for coroutine in (self._up, self._down, self._messages):
            asyncio.create_task(coroutine())

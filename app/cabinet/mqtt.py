import ulogging as logging
import uasyncio as asyncio
import ujson
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

SWITCH_DISCOVERY_TOPIC = "homeassistant/switch/projector_cabinet/main_switch/config"
SWITCH_STATE_TOPIC = "projector_cabinet/switch/state"
SWITCH_COMMAND_TOPIC = "projector_cabinet/switch/set"
SWITCH_AVAILABILITY_TOPIC = "projector_cabinet/switch/availability"
SWITCH_DISCOVERY_PAYLOAD = {
    "name": "Cabinet's switch",
    "unique_id": "projector_cabinet_switch",
    "command_topic": SWITCH_COMMAND_TOPIC,
    "state_topic": SWITCH_STATE_TOPIC,
    "availability_topic": SWITCH_AVAILABILITY_TOPIC,
    "device": DEVICE_DEFINITION,
}

# Local configuration
config['ssid'] = secrets.WIFI_SSID
config['wifi_pw'] = secrets.WIFI_PASS
config['server'] = secrets.MQTT_BROKER
config['user'] = secrets.MQTT_USER
config['password'] = secrets.MQTT_PASS
config["queue_len"] = 1  # Use event interface with default queue size
config["will"] = (
    SWITCH_AVAILABILITY_TOPIC, "offline", True, 0)  # This to let know Home Assistant that this device dropped from MQTT


@singleton
class MQTT:
    def __init__(self):
        self._logger = logging.getLogger('MQTT')
        MQTTClient.DEBUG = True
        self._client = MQTTClient(config, self._logger)
        self._cabinet = cabinet.Cabinet()
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

        await self._client.publish(SWITCH_STATE_TOPIC, self._cabinet_state())

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

    async def _up(self):  # (re)connection.
        while True:
            await self._client.up.wait()
            self._client.up.clear()
            self._logger.info('We are connected to broker.')

            await self._client.subscribe(SWITCH_COMMAND_TOPIC, 1)
            await self._client.publish(SWITCH_AVAILABILITY_TOPIC, "online")
            await self._client.publish(SWITCH_STATE_TOPIC, "ON" if self._cabinet.is_on() else "OFF")

    async def _announce_service_discovery(self):
        self._logger.info(f'Announcing cabinet on {SWITCH_DISCOVERY_TOPIC}')
        await self._client.publish(SWITCH_DISCOVERY_TOPIC, ujson.dumps(SWITCH_DISCOVERY_PAYLOAD))

    async def start(self):
        await self._client.connect()
        for coroutine in (self._up, self._down, self._messages):
            asyncio.create_task(coroutine())
        await self._announce_service_discovery()

    def _cabinet_state(self):
        return "ON" if self._cabinet.is_on() else "OFF"

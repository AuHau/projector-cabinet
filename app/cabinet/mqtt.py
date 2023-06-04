import ujson, machine
import ulogging as logging
import uasyncio as asyncio
from mqtt_as import MQTTClient, config
from ota_updater import OTAUpdater

from cabinet import cabinet
from utils import singleton
from app import secrets

SRC_REPO = "https://github.com/AuHau/projector-cabinet"

DEVICE_DEFINITION = {
    "name": "Projector cabinet",
    "configuration_url": "http://192.168.5.2",
    "manufacturer": "Adam Uhlir",
    "identifiers": ["cabinet_device"]
}

TEMP_STATE_INTERVAL = 2000
#FW_VERSIONS_STATE_INTERVAL = 15*60*1000
FW_VERSIONS_STATE_INTERVAL = 3000
CABINET_AVAILABILITY_TOPIC = "projector_cabinet/availability"

# Main on/off cabinet switch
SWITCH_DISCOVERY_TOPIC = "homeassistant/switch/projector_cabinet/main_switch/config"
SWITCH_STATE_TOPIC = "projector_cabinet/switch/state"
SWITCH_COMMAND_TOPIC = "projector_cabinet/switch/set"

# Temperature sensor
TEMP_DISCOVERY_TOPIC = "homeassistant/sensor/projector_cabinet/temp/config"
TEMP_STATE_TOPIC = "projector_cabinet/temp/state"

# Firmware update
FW_DISCOVERY_TOPIC = "homeassistant/update/projector_cabinet/fw/config"
FW_STATE_TOPIC = "projector_cabinet/fw/state"
FW_COMMAND_TOPIC = "projector_cabinet/fw/update"

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
        self._state_loops = []
        self._updater = OTAUpdater(SRC_REPO, main_dir='app', secrets_file="secrets.py")
        self._topics_commands_mapping = {
            SWITCH_COMMAND_TOPIC: self._handle_switch_command,
            FW_COMMAND_TOPIC: self._handle_fw_command
        }

    async def _handle_switch_command(self, msg):
        if msg == "ON":
            await self._cabinet.turn_on()
        elif msg == "OFF":
            await self._cabinet.turn_off()
        else:
            self._logger.error(f'Handling switch command, but got unknown command: {msg}')

        await self._client.publish(SWITCH_STATE_TOPIC, "ON" if self._cabinet.is_on() else "OFF")

    async def _handle_fw_command(self, msg):
        if msg == "install" and self._updater.check_for_update(True):
            self._logger.info('Received install new firmware command and new version is available. Marking for install and restarting.')
            machine.reset()

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
            for task in self._state_loops:
                task.cancel()

    async def _up(self):  # (re)connection.
        while True:
            await self._client.up.wait()
            self._client.up.clear()
            self._logger.info('We are connected to broker.')

            await self._announce_service_discovery()
            await self._client.subscribe(SWITCH_COMMAND_TOPIC, 1)
            await self._client.publish(CABINET_AVAILABILITY_TOPIC, "online")
            await self._client.publish(SWITCH_STATE_TOPIC, "ON" if self._cabinet.is_on() else "OFF")
            self._state_loops.append(asyncio.create_task(self._read_temp()))
            self._state_loops.append(asyncio.create_task(self._read_fw_version()))

    async def _read_temp(self):  # send temperature data
        while True:
            await self._client.publish(TEMP_STATE_TOPIC, str(await self._cabinet.get_temp()))
            await asyncio.sleep_ms(TEMP_STATE_INTERVAL)

    async def _read_fw_version(self):  # poll if new fw update is available
        while True:
            (current_version, latest_version) = self._updater.get_versions()
            json_payload = ujson.dumps({
                "installed_version": current_version,
                "latest_version": latest_version,
            })
            await self._client.publish(FW_STATE_TOPIC, json_payload)
            await asyncio.sleep_ms(FW_VERSIONS_STATE_INTERVAL)

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

        update_discovery_payload = {
            "name": "Cabinet's device update",
            "unique_id": "projector_cabinet_fw",
            "device_class": "firmware",
            "state_topic": FW_STATE_TOPIC,
            "command_topic": FW_COMMAND_TOPIC,
            "payload_install": "install",
            "availability_topic": CABINET_AVAILABILITY_TOPIC,
            "device": DEVICE_DEFINITION,
        }
        self._logger.info(f'Announcing cabinet capability on topic: {FW_DISCOVERY_TOPIC}')
        await self._client.publish(FW_DISCOVERY_TOPIC, ujson.dumps(update_discovery_payload))

    async def start(self):
        await self._client.connect()
        for coroutine in (self._up, self._down, self._messages):
            asyncio.create_task(coroutine())

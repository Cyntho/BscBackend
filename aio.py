import asyncio_mqtt as aiomqtt
import paho.mqtt as mqtt
import paho.mqtt.client

aio = aiomqtt.Client(
    hostname="10.66.66.1",  # The only non-optional parameter
    port=8883,
    username="broker",
    password="32tz7u8mM",
    client_id="broker-001",
    protocol=paho.mqtt.client.MQTTv5,
    transport="tcp",
    keepalive=60,
    clean_start=mqtt.client.MQTT_CLEAN_START_FIRST_ONLY,
)

# aiomqtt.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

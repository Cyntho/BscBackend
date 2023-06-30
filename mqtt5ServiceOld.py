import time
import mqttCallbacks

from paho.mqtt import client as mqtt
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

# Settings
broker = "10.66.66.1"
myPort = 1883
clt_id = "python-mqtt-service-0001"
transport_layer = "tcp"
username = "emqx-phone-001"
password = "32tz7u8mM"


def on_message(client, userdata, msg):
    match msg.topic:
        case "mqtt/test":
            print(f"[{msg.topic}] [{msg.payload}]")
        case "req/settings":
            client.publish("res/settings", "ELF1, ELF2, ELF3, CDC")
        case "req/messages":
            client.publish("res/messages", "m1, m2, m3")
        case _:
            print(f"Unhandled message in [{msg.topic}]: [{msg.payload}]")



def setup():
    client = mqtt.Client(client_id=clt_id,
                         transport=transport_layer,
                         protocol=mqtt.MQTTv5)
    client.username_pw_set(username, password)
    client.on_connect = mqttCallbacks.on_connect
    client.on_message = on_message
    client.on_publish = mqttCallbacks.on_publish
    client.on_subscribe = mqttCallbacks.on_subscribe
    return client


def run():
    print("Attempting to connect to Mqtt Server..")
    client = setup()
    properties=Properties(PacketTypes.CONNECT)
    properties.SessionExpiryInterval=30*60 # in seconds
    client.connect(broker, port=myPort, clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY, properties=properties, keepalive=60)
    client.subscribe("mqtt/test", 1)
    client.subscribe("req/settings")
    client.subscribe("req/messages")
    client.loop_forever()

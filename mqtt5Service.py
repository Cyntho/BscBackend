import ssl
import random
import time
from multiprocessing import Process

import MessageWrapper
import mqttCallbacks
from MessageWrapper import MessageWrapper
from settings import Settings

from uuid import uuid4
from datetime import timezone, datetime

from paho.mqtt import client as mqtt
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes


class Mqtt5Service:
    host = "10.66.66.1"
    clientID = "broker"
    transportLayer = "tcp"
    emqxPort = 8883
    username = "broker"
    password = "32tz7u8mM"
    messages: list[MessageWrapper]

    def __init__(self, config: Settings):
        self.config = config
        self.messages = list[MessageWrapper]()
        self.client = mqtt.Client(
            client_id=self.clientID,
            transport=self.transportLayer,
            protocol=mqtt.MQTTv5,
            reconnect_on_failure=True
        )

        self.client.username_pw_set(self.username, self.password)
        self.client.tls_set(
            ca_certs="certs/ca.crt",
            tls_version=ssl.PROTOCOL_TLS
        )
        self.client.tls_insecure_set(True)

        self.client.on_connect = mqttCallbacks.on_connect
        self.client.on_publish = mqttCallbacks.on_publish
        self.client.on_subscribe = mqttCallbacks.on_subscribe
        self.client.on_message = self.on_message

    def connect(self):
        if self.client is None:
            return

        properties = Properties(PacketTypes.CONNECT)

        self.client.connect_async(host=self.host,
                                  port=self.emqxPort,
                                  keepalive=360,
                                  clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
                                  properties=properties)
        self.client.subscribe("mqtt/test", 1)
        self.client.subscribe("req/settings", 1)
        self.client.subscribe("req/messages", 1)
        self.client.loop_start()

    def disconnect(self):
        if self.client is None:
            return
        try:
            self.client.disconnect()
        finally:
            print(f"Disconnected.")

    def on_message(self, client, userdata, msg):
        match msg.topic:
            case "mqtt/test":
                print(f"[{msg.topic}] [{msg.payload}]")
            case "req/settings":
                # client.publish("res/settings", "ELF1, ELF2, ELF3, CDC")
                self.handleSettingsQuery()
            case "req/messages":
                # client.publish("res/messages", "m1, m2, m3")
                self.handleMessagesQuery()
            case _:
                print(f"Unhandled message in [{msg.topic}]: [{msg.payload}]")

    def publish(self, message: MessageWrapper, topic: str):
        if self.client is None or not self.client.is_connected():
            print("Can't publish messages while the client is disconnected!")
            return
        self.client.publish(str, message.toJSON(), 1, True)
        self.messages.append(message)

    def handleMessagesQuery(self):
        data = ""
        for entry in self.messages:
            data += str(entry)
        self.client.publish("res/messages", str(data), qos=1, retain=False)

    def handleSettingsQuery(self):
        data = ""
        for entry in self.config.getLocations():
            data += str(entry)
        self.client.publish("res/settings", str(data), qos=1, retain=False)

    def run_generator(self):
        print("Running generator..")

        while True:
            time.sleep(1.0)
            err = str(uuid4())
            dt = datetime.now(timezone.utc)

            utc_time = dt.replace(tzinfo=timezone.utc)
            utc_timestamp = utc_time.timestamp()

            # print(utc_timestamp)
            temp: MessageWrapper = MessageWrapper(
                location=random.randint(0, 3),
                error_id=err,
                error_code=0,
                error_type=random.randint(1, 3),
                sps_id=random.randint(0, 99),
                timestamp=utc_timestamp
            )
            print(f"Attempting to publish: {temp.toString()}")
            self.client.publish(temp, "mqtt/test")

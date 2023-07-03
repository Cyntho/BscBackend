
import asyncio
import socket
import ssl
import uuid
import paho.mqtt.client as mqtt

from AsyncioHelper import AsyncioHelper
from MessageWrapper import MessageWrapper

host = "10.66.66.1"
clientID = "broker"
transportLayer = "tcp"
emqxPort = 8883
username = "broker"
password = "32tz7u8mM"
messages: list[MessageWrapper]


class AsyncMqttExample:
    def __init__(self, loop):
        self.loop = loop

    def on_connect(self, client, userdata, flags, rc):
        print("Connected!")

    def on_message(self, client, userdata, msg):
        if not self.got_message:
            print("Got unexpected message: {}".format(msg.decode()))
        else:
            self.got_message.set_result(msg.payload)

    def on_disconnect(self, client, userdata, rc):
        self.disconnected.set_result(rc)

    async def main(self):
        self.disconnected = self.loop.create_future()
        self.got_message = None

        self.client = mqtt.Client(client_id=clientID,
                                  transport=transportLayer,
                                  protocol=mqtt.MQTTv5)
        self.client.username_pw_set(username, password)
        self.client.tls_set(
            ca_certs="certs/ca.crt",
            tls_version=ssl.PROTOCOL_TLS
        )
        self.client.tls_insecure_set(True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        aioh = AsyncioHelper(self.loop, self.client)

        self.client.connect('10.66.66.1', 8883, 60)
        self.client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)

        for c in range(3):
            await asyncio.sleep(2)
            print("Publishing")
            self.got_message = self.loop.create_future()
            self.client.publish("mqtt/test", b'Hello', qos=1)
            # msg = await self.got_message
            # print("Got response with {} bytes".format(len(msg)))
            self.got_message = None

        self.client.disconnect()
        print("Disconnected: {}".format(await self.disconnected))

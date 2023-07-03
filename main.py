#!/src/usr/python3

import random
import ssl
import paho.mqtt.client
import MessageWrapper
import asyncio
import asyncio_mqtt as aiomqtt

from MessageWrapper import MessageWrapper
from settings import Settings


lock = asyncio.Lock()
message_list = list()
tls_params = aiomqtt.TLSParameters(ca_certs="certs/ca.crt",
                                   tls_version=ssl.PROTOCOL_TLS,
                                   cert_reqs=ssl.CERT_NONE)


async def get_settings():
    temp = Settings("settings.json").get_locations()
    i = 0
    for entry in temp:
        entry["id"] = i
        i += 1
    return temp


async def listen():
    async with aiomqtt.Client(hostname="10.66.66.1",
                              client_id="broker_listening",
                              port=8883,
                              username="broker",
                              password="32tz7u8mM",
                              clean_start=paho.mqtt.client.MQTT_CLEAN_START_FIRST_ONLY,
                              tls_params=tls_params) as client:
        async with client.messages() as messages:
            await client.subscribe("req/settings", 1)
            await client.subscribe("req/messages", 1)

            async for message in messages:
                if message.topic.matches("req/messages"):
                    # give the client a bit to build its ui
                    await asyncio.sleep(1)
                    print(f"Responding to req/message with:")
                    async with lock:
                        for entry in message_list:
                            e = str(entry.to_json())
                            print(f"\t{e}")
                            await client.publish("res/messages", qos=1, payload=e)

                if message.topic.matches("req/settings"):

                    print(f"Caught request for settings.")
                    cfg = await get_settings()
                    await client.publish("res/settings", str(cfg), 1, False)
                    print(f"Responded with [{cfg}]")


async def publish_generator():
    async with aiomqtt.Client(hostname="10.66.66.1",
                              client_id="broker_generator",
                              port=8883,
                              username="broker",
                              password="32tz7u8mM",
                              clean_start=paho.mqtt.client.MQTT_CLEAN_START_FIRST_ONLY,
                              tls_params=tls_params) as client:
        # Initialize config once
        cfg = Settings("settings.json")

        # Generate a few messages to see something on the client
        for i in range(0, random.randint(5, 7)):
            msg = MessageWrapper.randomize(cfg)
            print(f"Initial generation [{i}]: {msg.to_string()}")
            await client.publish("messages/add", qos=1, payload=msg.to_json())
            async with lock:
                message_list.append(msg)

        # Loop
        while True:
            # Generate random number. If list is empty or picked number large enough, generate message
            if random.randint(0, 100) > 50 or len(message_list) == 0:
                print("Publishing..")
                msg = MessageWrapper.randomize(cfg)
                print(f"Generated message with id [{msg.id}]")
                # await client.publish("mqtt/test", qos=1, payload=b"Das ist ein Test")
                await client.publish("messages/add", qos=1, payload=msg.to_json())
                async with lock:
                    message_list.append(msg)

            # Randomly pick a message and send delete to clients
            else:
                index = random.randint(0, len(message_list) - 1)
                async with lock:
                    msg = message_list[index]
                    message_list.remove(msg)
                    print(f"Removing message: {msg.id}. There are {len(message_list)} entries left.")
                await client.publish("messages/remove", qos=1, payload=msg.to_json())
            await asyncio.sleep(1)


async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(listen())
        tg.create_task(publish_generator())


if __name__ == '__main__':
    print("Starting")
    asyncio.run(main())
    print("Finished")

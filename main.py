#!/src/usr/python3
import datetime
import random
import sys
import os
import time
import uuid
import asyncio

from AsyncMqttExample import AsyncMqttExample
from MessageWrapper import MessageWrapper
from mqtt5Service import Mqtt5Service
from settings import Settings

from multiprocessing import Process
from concurrent.futures import ProcessPoolExecutor


if __name__ == '__main__':
    print("Starting")
    loop = asyncio.get_event_loop()

    if sys.platform.lower() == "win32" or os.name.lower() == "nt":
        from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
        print("Changing policy..")

    asyncio.run(AsyncMqttExample(loop).main())
    # loop.run_until_complete(AsyncMqttExample(loop).main())
    # loop.close()
    print("Finished")

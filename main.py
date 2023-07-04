#!/src/usr/python3
import hashlib
import io
import os
import random
import re
import ssl
import uuid

import paho.mqtt.client

import sqlite3
import click
from getpass import getpass
from pysqlitecipher import sqlitewrapper

import bsc_util
from LocationWrapper import LocationWrapper
from MessageWrapper import MessageWrapper
import MessageWrapper
from bcolors import bcolors
from mqtt5Service import Mqtt5Service
from settings import Settings

import asyncio
import asyncio_mqtt as aiomqtt

import argparse

lock = asyncio.Lock()
message_list = list()
tls_params = aiomqtt.TLSParameters(ca_certs="certs/ca.crt",
                                   tls_version=ssl.PROTOCOL_TLS,
                                   cert_reqs=ssl.CERT_NONE)

# Using ArgParser to handle easier setup
parser = argparse.ArgumentParser(
    prog="program",
    description="BSC Backend"
)
parser.add_argument(
    "-host",
    "--hostname",
    default="10.66.66.1",
    action="store_const",
    help="Specify the MQTT broker's hostname"
)
parser.add_argument(
    "-p",
    "--port",
    default=8883,
    dest="port",
    action="store_const",
    help="Specify the MQTT broker's Port"
)
parser.add_argument(
    "--database",
    default="./users.db",
    action="store",
    type=str,
    help="Specify where user data should be stored (*.db)"
)
parser.add_argument(
    "--run",
    action="store_true",
    help="Start the server"
)
parser.add_argument(
    "--password",
    action='store',
    type=str,
    default=""
)
parser.add_argument(
    "--setup",
    action="store_true",
    help="Add or modify users"
)

args = parser.parse_args()


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


def install():
    # Choose database file location
    db_location = click.prompt("Choose database file: ", type=str, default=args.database)

    # Check if file already exists
    if os.path.exists(db_location):
        print(f"{bcolors.WARNING} Attention: This file already exists!")
        confirmation = click.prompt(f"Would you like to overwrite it? (yes/no) {bcolors.HEADER}", type=str)
        if confirmation == "yes":
            print("Deleting file...")
            try:
                os.remove(db_location)
            except IOError:
                print(f"Unable to remove file {db_location}")
                input("Press any key to return to the menu")
                return
        else:
            print(f"Aborting..")
            return

    args.database = db_location

    # Request password protection:
    db_pass = args.password
    print(f"{bcolors.WARNING}Please be advised: The password you set here {bcolors.BOLD} can't be restored!{bcolors.ENDC}")
    while not bsc_util.check_password(db_pass):
        print(f"Secure passwords consist of at least 12 characters")
        print(f"It must include lower and uppercase characters, numbers and symbols")
        db_pass = getpass(">> ")

    args.database = db_location
    args.password = db_pass
    try:
        connection = sqlitewrapper.SqliteCipher(dataBasePath=db_location, checkSameThread=False, password=db_pass)
        col_list = [
            ["id", "TEXT"],
            ["username", "TEXT"],
            ["password", "TEXT"],
            ["salt", "TEXT"],
            ["banned", "INT"]
        ]
        connection.createTable("users", colList=col_list, makeSecure=True, commit=True)
        connection.sqlObj.close()
        print(f"Database has been created!")
        print(f"{bcolors.WARNING}Please keep the password secure. It cannot be restored!{bcolors.HEADER}")
        print("")
        input("Press any key to return to the menu")

    except IOError:
        print(f"Could not connect to database at {db_location}")


def print_users(debug: bool = False):
    try:
        if args.password is None or not bsc_util.check_password(args.password):
            args.password = getpass("Please enter the password: ")

        connection = sqlitewrapper.SqliteCipher(dataBasePath=args.database, checkSameThread=False,
                                                password=args.password)
        col, data = connection.getDataFromTable("users", raiseConversionError=True, omitID=False)
        if debug:
            for entry in data:
                print(entry)
        else:
            for entry in data:
                b = "BANNED" if entry[5] == 0 else ""
                print(f"User: {entry[2]}\t{b}")
        connection.sqlObj.close()

    except RuntimeError as r:
        print(f"Could not connect to the database: [{args.password}] {r}")
    except ValueError as v:
        print(f"Conversion error: {v}")


def add_user():
    username = ""

    try:
        if args.password is None or not bsc_util.check_password(args.password):
            args.password = getpass("Please enter the password: ")

        connection = sqlitewrapper.SqliteCipher(dataBasePath=args.database, checkSameThread=False,
                                                password=args.password)

        while username == "":
            temp = click.prompt("Please enter a username: ")
            col, data = connection.getDataFromTable("users", raiseConversionError=False, omitID=True)
            is_free = True
            for entry in data:
                if entry[1].lower() == temp.lower():
                    print(f"Username '{temp}' is already taken.")
                    is_free = False

            # Only allow letters, numbers, minus and underscore
            if is_free and re.match("^[A-Za-z0-9_-]*$", temp) and len(temp) > 3:
                username = temp
            else:
                print(f"Username contains illegal characters or is too short.")

        while True:
            password = click.prompt("Please enter a password: ", confirmation_prompt=True, hide_input=True)
            if bsc_util.check_password(password):
                break
            else:
                print(f"Secure passwords consist of at least 12 characters")
                print(f"It must include lower and uppercase characters, numbers and symbols")

        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)

        connection.insertIntoTable("users", insertList=[
            str(uuid.uuid4()),
            username,
            key,
            salt,
            1
        ], commit=True)
        connection.sqlObj.close()
        print(f"User [{username}] has been added!")

    except RuntimeError:
        print(f"Could not connect to the database using password: {args.password}")
    except ValueError as v:
        print(f"Conversion error: {v}")


def edit_user(mode: int = 0):
    if args.password is None or not bsc_util.check_password(args.password):
        args.password = getpass("Please enter the password: ")

    connection = sqlitewrapper.SqliteCipher(dataBasePath=args.database, checkSameThread=False,
                                            password=args.password)

    col, data = connection.getDataFromTable("users", raiseConversionError=False, omitID=False)
    for user in data:
        print(f"[{user[0]}] {user[2]}")

    selection = click.prompt("Please select the user", type=int)
    if 0 < selection >= len(data):
        print("Invalid selection")
        return

    if mode == 0:

        # Update password
        while True:
            password = click.prompt("Please enter a new password: ", confirmation_prompt=True, hide_input=True)
            if bsc_util.check_password(password):
                break
            else:
                print(f"Secure passwords consist of at least 12 characters")
                print(f"It must include lower and uppercase characters, numbers and symbols")

        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
        connection.updateInTable("users", selection, "password", key, commit=True, raiseError=True)
        connection.updateInTable("users", selection, "salt", salt, commit=True, raiseError=True)
        print(f"The user has been updated!")

    elif mode == 1:
        # Ban a user
        connection.updateInTable("users", selection, "banned", 0, commit=True, raiseError=True)
        print(f"The user has been banned!")

    connection.sqlObj.close()


def setup():
    print(f"--------------------------------------")
    print(f"Welcome to the setup of the BscBackend")
    print(f"--------------------------------------")

    def print_options():
        # click.clear()
        print(f"Options are:")
        print(f"[1] Install")
        print(f"[2] List all users")
        print(f"[3] Add new user")
        print(f"[4] Change user's password")
        print(f"[5] Ban user")
        print("")
        print(f"Press anything else to exit")

    try:
        while True:
            print_options()
            choice = int(input("\nChoose option: "))
            match choice:
                case 1:
                    install()
                case 2:
                    print_users()
                case 3:
                    add_user()
                case 4:
                    edit_user(0)
                case 5:
                    edit_user(1)
                case _:
                    print("exit")
                    break
    except ValueError:
        print(f"Exiting..")
        return


async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(listen())
        tg.create_task(publish_generator())


if __name__ == '__main__':

    if args.password:
        print(f"{bcolors.FAIL} Startup with password! This is okay for playing around, but don't automate it like that.{bcolors.HEADER}")

    print(f"{bcolors.HEADER}")
    if args.run:
        print("Starting Server..")
        asyncio.run(main())
    elif args.setup:
        setup()
    else:
        print("You need to specify --run if you wish to start the server.")

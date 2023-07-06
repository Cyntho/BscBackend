#!/src/usr/python3
import datetime
import hashlib
import io
import ipaddress
import os
import random
import re
import ssl
import time
import uuid

import MySQLdb
import paho.mqtt.client

import pymysql

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
    prog="bsc_backend",
    description="BSC Backend"
)
# MQTT
parser.add_argument(
    "--mqtt-host",
    default="10.66.66.1",
    action="store",
    help="Host of mqtt broker"
)
parser.add_argument(
    "--mqtt-port",
    default=8883,
    action="store",
    help="Specify the MQTT broker's Port"
)

# MySQL
parser.add_argument(
    "--mysql-host",
    default="10.66.66.1",
    action='store',
    help="Host of mysql auth. server"
)
parser.add_argument(
    "--mysql-port",
    default=3306,
    action='store',
    type=int,
    help="MySQL server port"
)
parser.add_argument(
    "--database",
    default="mqtt",
    action="store",
    type=str,
    help="MySQL database"
)
parser.add_argument(
    "--username",
    action='store',
    type=str,
    default="admin",
    help="MySQL username"
)
parser.add_argument(
    "--password",
    action='store',
    type=str,
    default="public",
    help="MySQL password"
)

# Runtime
parser.add_argument(
    "--run",
    action="store_true",
    help="Start the server"
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
    global args
    async with aiomqtt.Client(hostname=args.mqtt_host,
                              client_id="broker_listening",
                              port=args.mqtt_port,
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
    conn: pymysql.connections.Connection
    try:

        # Welcome and explain
        print(f"Welcome to the install wizard of BscBackend!\n")

        if args.username != "root":
            bsc_util.alert(f"You are running this script --username '{args.username}', not as database user 'root'")
            bsc_util.alert(f"Creating the database and tables may fail.")

        print(f"Testing database connection.. ")

        # Setup connection
        conn = pymysql.connect(host=args.mysql_host,
                               port=args.mysql_port,
                               user=args.username,
                               password=args.password,
                               database=args.database)
        cursor = conn.cursor()
        cursor.execute(query="SELECT TABLE_NAME FROM information_schema.TABLES "
                             "WHERE TABLE_SCHEMA LIKE %s "
                             "AND TABLE_TYPE LIKE 'BASE TABLE' "
                             "AND (TABLE_NAME = %s OR TABLE_NAME = %s)",
                       args=(args.database, "mqtt_user", "mqtt_acl"))
        counter = cursor.fetchall()

        if len(counter) > 0:
            bsc_util.alert(f"Database already exists!")
            if click.prompt(f"{bcolors.WARNING} Do you wish to wipe all data and install again? (yes/no)"
                            f"{bcolors.HEADER}") != "yes":
                return
        else:
            print(f"Connection established.")

        print(f"Setting up database.. ")
        # Clean up
        cursor.execute(query="DROP TABLE IF EXISTS `mqtt_user`")
        cursor.execute(query="DROP TABLE IF EXISTS `mqtt_acl`")

        # Create Database
        cursor.execute(query="CREATE DATABASE IF NOT EXISTS %s",
                       args=args.database)

        # Create table: mqtt_user (Authentication)
        cursor.execute(query="CREATE TABLE `mqtt_user` ("
                             "`id` int(11) UNSIGNED NOT NULL AUTO_INCREMENT, "
                             "`username` varchar(100) DEFAULT NULL, "
                             "`password_hash` varchar(100) DEFAULT NULL, "
                             "`salt` varchar(35) DEFAULT NULL, "
                             "`is_superuser` tinyint(1) DEFAULT 0, "
                             "`ipaddress` varchar(60) DEFAULT NULL "
                             "PRIMARY KEY (`id`), "
                             "UNIQUE KEY `mqtt_username` (`username`)"
                             ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;)")

        # Create table: mqtt_acl (Authorization)
        cursor.execute(query="CREATE TABLE `mqtt_acl` ( "
                             "`id` int(11) unsigned NOT NULL AUTO_INCREMENT, "
                             "`ipaddress` VARCHAR(60) NOT NULL DEFAULT '', "
                             "`username` VARCHAR(255) NOT NULL DEFAULT '', "
                             "`action` ENUM('publish', 'subscribe', 'all') NOT NULL, "
                             "`permission` ENUM('allow', 'deny') NOT NULL, "
                             "`topic` VARCHAR(255) NOT NULL DEFAULT '', "
                             "PRIMARY KEY (`id`) "
                             ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;)")
        conn.commit()
        print("Database and tables created!")

        print(f"{bcolors.UNDERLINE}Create EMQX user:{bcolors.ENDC}{bcolors.HEADER}")
        print(f"This account will be used by the EMQX-Dashboard/Mqtt-Broker to authenticate client connections")
        print(f"and authorize subscriptions and publishes from broker and clients!\n")
        emqx_username = bsc_util.request_username()
        emqx_password = bsc_util.request_password(True)

        emqx_key, emqx_salt = bsc_util.calc_password_hash(emqx_password)
        cursor.execute(query="INSERT INTO mqtt_user "
                             "(`username`, `password_hash`, `salt`, `is_superuser`) "
                             "VALUES(%s, %s, %s, %s)",
                       args=(emqx_username, emqx_key, emqx_salt, 1))

        print(f"\n")
        print(f"{bcolors.UNDERLINE}Create Backend user:{bcolors.ENDC}{bcolors.HEADER}")
        print(f"This account will be used by this program to generate status messages,")
        print(f"listen for client requests and respond accordingly. \n")

        backend_username = bsc_util.request_username()
        backend_password = bsc_util.request_password()

        backend_key, backend_salt = bsc_util.calc_password_hash(backend_password)

        print(f"Specify the static IPv4Address the backend will connect from:")
        backend_ip = click.prompt("IP address", type=ipaddress.IPv4Address)
        backend_ip = str(backend_ip)

        # Create user account
        cursor.execute(query="INSERT INTO `mqtt_user` "
                             "(`username`, `pasword_hash`, `salt`, `ipaddress`) "
                             "VALUES (%s, %s, %s, %s)",
                       args=(backend_username, backend_key, backend_salt, backend_ip))

        # Granting permissions:

        # Listen for request for old messages
        cursor.execute(query="INSERT INTO mqtt_acl "
                             "(`ipaddress`, `username`, `action`, `permission`, `topic`) "
                             "VALUES(%s, %s, %s, %s, %s)",
                       args=(backend_ip, backend_username, 'subscribe', 'allow', 'req/messages'))

        # Respond to request for old messages
        cursor.execute(query="INSERT INTO mqtt_acl "
                             "(`ipaddress`, `username`, `action`, `permission`, `topic`) "
                             "VALUES(%s, %s, %s, %s, %s)",
                       args=(backend_ip, backend_username, 'publish', 'allow', 'res/messages'))

        # Listen for request for server settings
        cursor.execute(query="INSERT INTO mqtt_acl "
                             "(`ipaddress`, `username`, `action`, `permission`, `topic`) "
                             "VALUES(%s, %s, %s, %s, %s)",
                       args=(backend_ip, backend_username, 'subscribe', 'allow', 'req/messages'))

        # Respond to request for server settings
        cursor.execute(query="INSERT INTO mqtt_acl "
                             "(`ipaddress`, `username`, `action`, `permission`, `topic`) "
                             "VALUES(%s, %s, %s, %s, %s)",
                       args=(backend_ip, backend_username, 'publish', 'allow', 'res/settings'))

        # Publish messages
        cursor.execute(query="INSERT INTO mqtt_acl "
                             "(`ipaddress`, `username`, `action`, `permission`, `topic`) "
                             "VALUES(%s, %s, %s, %s, %s)",
                       args=(backend_ip, backend_username, 'publish', 'allow', 'messages/add'))

        # Delete messages
        cursor.execute(query="INSERT INTO mqtt_acl "
                             "(`ipaddress`, `username`, `action`, `permission`, `topic`) "
                             "VALUES(%s, %s, %s, %s, %s)",
                       args=(backend_ip, backend_username, 'publish', 'allow', 'messages/remove'))

        conn.commit()

    except Exception as ex:
        bsc_util.alert(f"{ex}")
        return


def list_users():
    try:

        conn = pymysql.connect(host=args.mysql_host,
                               port=args.mysql_port,
                               user=args.username,
                               password=args.password,
                               database="mqtt")
        cursor = conn.cursor()
        cursor.execute("SELECT `id`, `username`, `ipaddress` FROM mqtt_user WHERE `is_superuser` = %s", False)
        data = cursor.fetchall()
        cursor.close()
        conn.close()

        if len(data) == 0:
            bsc_util.alert("There are no users yet.")
            return

        print(f"There are {len(data)} users:\n")
        for x in data:
            print(f"id: {x[0]}\tusername: {x[1]}\tIp Address: {x[2]}")

    except MySQLdb.Error as ex:
        bsc_util.alert(f"Could not connect to the database: {ex}", color_message=bcolors.FAIL)


def add_user():
    username = ""

    try:
        conn = pymysql.connect(host=args.mysql_host,
                               port=args.mysql_port,
                               user=args.username,
                               password=args.password,
                               database="mqtt")
        cursor = conn.cursor()
        cursor.execute("SELECT `username` FROM mqtt_user")
        existing_users = cursor.fetchall()
        cursor.close()
        conn.close()

        while username == "":
            temp = click.prompt("Please enter a username: ")
            is_free = True

            for user in existing_users:
                if user[0].lower() == temp.lower():
                    bsc_util.alert(f"Username {temp} is already taken!")
                    is_free = False

            if is_free is True and re.match("^[A-Za-z0-9_-]*$", temp) and len(temp) > 3:
                username = temp
            elif is_free:
                bsc_util.alert("Username contains illegal characters or is too short.")

        password = bsc_util.request_password()

        ip = click.prompt("Please enter IPv4 address: ", type=ipaddress.IPv4Address)
        ip = str(ip)

        key, salt = bsc_util.calc_password_hash(password)
        conn = pymysql.connect(host=args.mysql_host,
                               port=args.mysql_port,
                               user=args.username,
                               password=args.password,
                               database="mqtt")
        cursor = conn.cursor()
        cursor.execute(query="INSERT INTO mqtt_user "
                             "(`username`, `password_hash`, `salt`, `ipaddress`) "
                             "VALUES(%s, %s, %s, %s)",
                       args=(username, key, salt, ip))

        cursor.execute(query="INSERT INTO mqtt_acl "
                             "(`ipaddress`, `username`, `action`, `permission`, `topic`) "
                             "VALUES(%s, %s, %s, %s, %s)",
                       args=(str(ip), username, 'publish', 'allow', 'req/messages'))

        cursor.execute(query="INSERT INTO mqtt_acl "
                             "(`ipaddress`, `username`, `action`, `permission`, `topic`) "
                             "VALUES(%s, %s, %s, %s, %s)",
                       args=(str(ip), username, 'publish', 'allow', 'req/settings'))

        cursor.execute(query="INSERT INTO mqtt_acl "
                             "(`ipaddress`, `username`, `action`, `permission`, `topic`) "
                             "VALUES(%s, %s, %s, %s, %s)",
                       args=(str(ip), username, 'subscribe', 'allow', 'res/messages'))

        cursor.execute(query="INSERT INTO mqtt_acl "
                             "(`ipaddress`, `username`, `action`, `permission`, `topic`) "
                             "VALUES(%s, %s, %s, %s, %s)",
                       args=(str(ip), username, 'subscribe', 'allow', 'res/settings'))

        cursor.execute(query="INSERT INTO mqtt_acl "
                             "(`ipaddress`, `username`, `action`, `permission`, `topic`) "
                             "VALUES(%s, %s, %s, %s, %s)",
                       args=(str(ip), username, 'subscribe', 'allow', 'messages/add'))

        cursor.execute(query="INSERT INTO mqtt_acl "
                             "(`ipaddress`, `username`, `action`, `permission`, `topic`) "
                             "VALUES(%s, %s, %s, %s, %s)",
                       args=(str(ip), username, 'subscribe', 'allow', 'messages/remove'))

        conn.commit()
        conn.close()
        cursor.close()
        bsc_util.alert(f"User '{username}' has been added as client and may connect from '{str(ip)}'")

    except RuntimeError as r:
        print(f"Could not connect to the database: {r}")
    except ValueError as v:
        print(f"Conversion error: {v}")


def edit_user():
    try:
        conn = pymysql.connect(host=args.mysql_host,
                               port=args.mysql_port,
                               user=args.username,
                               password=args.password,
                               database="mqtt")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mqtt_user WHERE `is_superuser` = FALSE")
        existing_users = cursor.fetchall()
        for user in existing_users:
            print(f"[{user[0]}]\t{user[1]}")

        username = ""
        while True:
            selection = click.prompt("\nPlease select the user", type=int)
            valid = False
            for user in existing_users:
                if user[0] == selection:
                    username = user[1]
                    valid = True
            if valid:
                break
            else:
                bsc_util.alert(f"'{selection}' is not a valid selection.")

        def print_options():
            print(f"\n\nOptions are:")
            print(f"[1] Change IP")
            print(f"[2] Change Password")
            print(f"[3] Delete")
            print("")
            print(f"[0] Back\n")

        conn = pymysql.connect(host=args.mysql_host,
                               port=args.mysql_port,
                               user=args.username,
                               password=args.password,
                               database="mqtt")
        cursor = conn.cursor()

        print_options()
        bsc_util.alert(f"Updating user '{username}':\n")
        while True:
            choice = click.prompt("Select option", type=int)
            if 0 <= choice < 4:
                break
            else:
                bsc_util.alert(f"'{choice}' is not a valid option.")

        match choice:
            case 1:
                value = click.prompt("New IP", type=ipaddress.IPv4Address)
                cursor.execute(query="UPDATE mqtt_user SET `ipaddress` = %s WHERE `id` = %s",
                               args=(str(value), str(selection)))
                cursor.execute(query="UPDATE mqtt_acl SET `ipaddress` = %s WHERE `username` = %s",
                               args=(str(value), username))
                conn.commit()
                cursor.close()
                conn.close()
                bsc_util.alert(f"Changed IP of user {username} to {value}")

            case 2:
                password = bsc_util.request_password()

                key, salt = bsc_util.calc_password_hash(password)
                cursor.execute(query="UPDATE mqtt_user SET `password_hash` = %s, `salt` = %s WHERE `id` = %s",
                               args=(key, salt, str(selection)))
                conn.commit()
                cursor.close()
                conn.close()
                bsc_util.alert(f"Changed password of user '{username}'")

            case 3:
                print(f"{bcolors.WARNING}Warning: This action can not be undone!")
                if click.prompt(
                        f"Are you sure you wish to delete user '{username}'? (yes/no){bcolors.HEADER}") == "yes":
                    cursor.execute(query="DELETE FROM mqtt_user WHERE `id` = %s",
                                   args=(str(selection)))
                    cursor.execute(query="DELETE FROM mqtt_acl WHERE `username` = %s",
                                   args=username)
                    conn.commit()
                cursor.close()
                conn.close()
                bsc_util.alert(f"Deleted user {username}!")
            case _:
                return
    except MySQLdb.Error as sqlError:
        print(f"Error while interacting with the database: {sqlError}")


def setup():
    print(f"--------------------------------------")
    print(f"Welcome to the setup of the BscBackend")
    print(f"--------------------------------------")

    def print_options():
        print(f"\nOptions are:")
        print(f"[1] Install")
        print(f"[2] Start Server")
        print(f"[3] List Users")
        print(f"[4] Add User")
        print(f"[5] Edit User")
        print("")
        print(f"[0] Exit\n")

    while True:
        print_options()
        choice = click.prompt("Select option", type=int)
        match choice:
            case 1:
                install()
            case 2:
                asyncio.run(main())
            case 3:
                list_users()
            case 4:
                add_user()
            case 5:
                edit_user()
            case 0:
                print("exit")
                break


async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(listen())
        tg.create_task(publish_generator())


if __name__ == '__main__':
    click.clear()
    if args.password:
        bsc_util.alert("Startup with password! This is okay for playing around, but don't automate it like that.",
                       color_message=bcolors.FAIL)

    if args.run:
        print("Starting Server..")
        asyncio.run(main())
    elif args.setup:
        print(f"{bcolors.HEADER}")
        setup()
    else:
        print("You need to specify --run if you wish to start the server.")

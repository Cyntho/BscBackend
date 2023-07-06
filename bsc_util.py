import re
import os
import hashlib
import uuid

import click

from bcolors import bcolors


def check_password_strength(password, echo: bool = True):
    value = ((len(password) < 12)
                or (re.search(r"\d", password) is None)
                or (re.search(r"[A-Z]", password) is None)
                or (re.search(r"[a-z]", password) is None)
                or (re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None))
    if echo and value:
        print(f"{bcolors.WARNING}Secure passwords consist of at least 12 characters")
        print(f"It must include lower and uppercase characters, numbers and symbols{bcolors.HEADER}")
    return not value


def calc_password_hash(password):
    salt = uuid.uuid4().hex
    _hash = hashlib.sha256(password.encode() + salt.encode()).hexdigest()
    return _hash, salt


def alert(message: str,
          color_message: str = bcolors.WARNING,
          color_next: str = bcolors.HEADER):
    print(f"{color_message}{message}{color_next}")


def request_username():
    while True:
        tmp = click.prompt("Username", type=str)
        if 3 < len(tmp) >= 15 and re.match(r"^[A-Za-z0-9_-]*$", tmp):
            return tmp
        else:
            alert("Username must be between 3 and 15 characters long and not contain special characters")


def request_password(echo: bool = True):
    while True:
        tmp = click.prompt("Password", type=str, hide_input=True, confirmation_prompt=True)
        if check_password_strength(tmp, echo):
            return tmp
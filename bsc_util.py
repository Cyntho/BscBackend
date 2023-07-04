import re


def check_password(password):
    return not ((len(password) < 12)
                or (re.search(r"\d", password) is None)
                or (re.search(r"[A-Z]", password) is None)
                or (re.search(r"[a-z]", password) is None)
                or (re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None))

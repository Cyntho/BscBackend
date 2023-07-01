import io
import json


class Settings:

    def __init__(self, path):
        try:
            f = open(path, "r")
            self.config = json.load(f)
        except Exception as e:
            print(e)

    def getLocations(self):
        if self.config is None:
            print("Invalid config file.")
            return
        return self.config["locations"]

import json


class LocationWrapper:

    def __init__(self,
                 name: str,
                 sps: set,
                 rbg: set
                 ):
        self.name = name
        self.sps = sps
        self.rbg = rbg

    def toString(self):
        return f"[{self.name}] {self.sps=} {self.rbg=}"

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=False, indent=4)

    def fromJSON(self, data):
        x = json.loads(data)
        return LocationWrapper(**x)

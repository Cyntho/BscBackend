import json
import random
from datetime import timezone, datetime
from uuid import uuid4

from settings import Settings


error_types = ("WARNING", "ERROR")

def randomize(cfg: Settings):
    try:
        #location = random.choice(cfg.get_locations())

        available_locations = cfg.get_locations()
        # location_id = random.randint(0, len(available_locations) - 1)
        location_id = 0
        location = available_locations[location_id]

        sps = random.choice(location["SPS"])
        group = random.choice(cfg.config["groups"])
        device = random.choice(cfg.config["devices"])
        err = random.choice(cfg.config["error_messages"])
        # status = random.choice(("WARNING", "ERROR"))
        status = error_types[err["err_type"]]

        dt = datetime.now(timezone.utc)
        utc_time = dt.replace(tzinfo=timezone.utc)

        return MessageWrapper(str(uuid4()),
                              location_id,
                              status,
                              int(utc_time.timestamp()),
                              sps,
                              group,
                              device,
                              random.randint(0, 99),
                              err["msg"])
    except IndexError as ex:
        print(f"Caught: {ex}")


def from_json(data):
    x = json.loads(data)
    return MessageWrapper(**x)


class MessageWrapper:

    def __init__(self,
                 error_id: str,
                 location: int,
                 status: int,
                 timestamp: int,
                 sps: int,
                 group: int,
                 device: str,
                 part: int,
                 message: str,
                 ):
        self.location = location
        self.id = error_id
        self.status = status
        self.timestamp = timestamp
        self.sps = sps
        self.group = group
        self.device = device
        self.part = part
        self.message = message

    def to_string(self):
        return f"[{self.timestamp}] [{self.id}] {self.location=} {self.status=}, {self.sps=}, {self.group=}, " \
               f"{self.device=}, {self.part=}, {self.message=}"

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=False, indent=4)

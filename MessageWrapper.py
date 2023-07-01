import json


class MessageWrapper:

    def __init__(self, location: int,
                 error_id: str,
                 error_code: int,
                 error_type: int,
                 sps_id: int,
                 timestamp):
        self.location = location
        self.error_id = error_id
        self.error_code = error_code
        self.error_type = error_type
        self.sps_id = sps_id
        self.timestamp = timestamp

    def toString(self):
        return f"[´{self.timestamp}´] [`{self.error_id}`] test"

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=False, indent=4)

    def fromJSON(self, data):
        x = json.loads(data)
        return MessageWrapper(**x)

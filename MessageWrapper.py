import json


class MessageWrapper:
    error_id = 0
    error_code = 0
    error_type = 0
    sps_id = 0
    timestamp = 0

    def __init__(self, error_id, error_code, error_type, sps_id, timestamp):
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

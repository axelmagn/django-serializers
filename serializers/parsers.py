import json


class JSONParser(object):
    def parse(self, stream):
        return json.load(stream)

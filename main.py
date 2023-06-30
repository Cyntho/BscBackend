#!/src/usr/python3

import mqtt5Service
import MessageWrapper as mw


if __name__ == '__main__':
    mqtt = mqtt5Service.Mqtt5Service.setup()
    wrapper = mw.MessageWrapper(0, 0, 0, 0, 0)


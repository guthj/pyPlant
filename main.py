
import logging
import signal

from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import (CATEGORY_HUMIDIFIER)

import const

import paho.mqtt.client as mqtt

from time import sleep

#test

##pubStrings

pubPumpOn = "/Pump/setOn"
pubEnableWatering = "/enableWatering/setOn"
pubSetWaterTarget = "/WaterTarget/setValue"
pubReset = "/Kill"

subLog =                    "/Log"
subCurrentMoisture =        "/currentMoisture"
subPumpOn =                 "/Pump/getOn"
subEnableWatering =         "/enableWatering/getOn"
subWaterTargetIncrease =    "/WaterTarget/getIncrease"
subWaterTargetDecrease =    "/WaterTarget/getDecrease"
subWaterTargetValue =       "/WaterTarget/currentValue"
subError =                  "/MotionSensor/Error"
subWatering =               "/MotionSensor/Watering"
subBattery =                "/Battery"
subPing =                   "/Ping/Response"

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

# """
# "HumidifierDehumidifier": {
#       "OptionalCharacteristics": [
#          "LockPhysicalControls",
#          "Name",
#          "SwingMode",
#          "WaterLevel",
#          "RelativeHumidityDehumidifierThreshold",
#          "RelativeHumidityHumidifierThreshold",
#          "RotationSpeed"
#       ],
#       "RequiredCharacteristics": [
#          "CurrentRelativeHumidity",
#          "CurrentHumidifierDehumidifierState",
#          "TargetHumidifierDehumidifierState",
#          "Active"
#       ],
#       "UUID": "000000BD-0000-1000-8000-0026BB765291"
#    },
# """


class Plant(Accessory):

    category = CATEGORY_HUMIDIFIER

    plantNum = - 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        plant_hum = self.add_preload_service("HumidifierDehumidifier",
                                             chars=['RelativeHumidityHumidifierThreshold',
                                                    'RelativeHumidityDehumidifierThreshold',
                                                    'Name'])

        # passive set via .set_value
        self.char_currentMoisture = plant_hum.configure_char('CurrentRelativeHumidity')
        self.char_name = plant_hum.configure_char('Name')

        # CurrentHumidifierDehumidifierState: 0,1,2,3
        # (inactive, idle, humidifying, dehumidifying)

        self.char_curr_state = plant_hum.configure_char('CurrentHumidifierDehumidifierState')
        self.char_curr_state.set_value(1)

        # active with func
        # TargetHumidifierDehumidifierState
        # 0,1,2
        # (humidifier or dehumidifier, humidifier, dehumidifier)

        self.char_target_state = plant_hum.configure_char('TargetHumidifierDehumidifierState',
                                                          setter_callback=self.set_Target)
        self.char_target_state.set_value(0)

        self.char_active = plant_hum.configure_char(
            'Active', setter_callback=self.set_active)
        self.char_threshold = plant_hum.configure_char(
            'RelativeHumidityHumidifierThreshold', setter_callback=self.set_humidity)
        self.char_threshold_de = plant_hum.configure_char(
            'RelativeHumidityDehumidifierThreshold', setter_callback=self.set_humidity_de)
        self.char_threshold.set_value(60)
        self.char_threshold_de.set_value(100)

        self.set_info_service(firmware_revision = "0.1", manufacturer = "test", model = "test")

    def test(self, value):
        print(value)

    def set_active(self, value):
        # 0, 1
        # (inactive, active)
        print("Active: " + str(value))

        if value == 0:
            print("Active: is 0, setting enable Watering to false")
            client.publish(const.plantArray[self.plantNum] + pubPumpOn, "false")
            sleep(2)
            client.publish(const.plantArray[self.plantNum] + pubEnableWatering, "false")
        print("Active: is 1, setting enable Watering to true")
        if value == 1:
            client.publish(const.plantArray[self.plantNum] + pubEnableWatering, "true")
            self.char_curr_state.set_value(1)


    def set_humidity_de(self, value):
        log("Set dehum value to " + str(value) + "-> Resetting to 100", 4)
        self.char_threshold_de.set_value(100)
        self.char_threshold.set_value(value)
        client.publish(const.plantArray[self.plantNum] + pubSetWaterTarget, value)

    def set_humidity(self, value):
    #     hum_val = value + 10
    #     if hum_val > 100: hum_val = 100
    #     log("Set dehum_value to " + str(value), 4)
    #     self.char_threshold.set_value(hum_val)
    #     log("Setting hum_value to " + str(hum_val), 4)
    #     client.publish(const.plantArray[self.plantNum] + pubSetWaterTarget, value)
        log("Setting hum_value to " + str(value), 4)
        self.char_threshold_de.set_value(100)
        self.char_threshold.set_value(value)
        client.publish(const.plantArray[self.plantNum] + pubSetWaterTarget, value)


    def set_Target(self, value):
        # 0,1,2
        # (humidifier or dehumidifier, humidifier, dehumidifier)
        log("set target: " + str(value), 4)
        if value == 0:
            log("Auto set", 4)

        if value == 1:
            log("Start Pump", 4)
            client.publish(const.plantArray[self.plantNum] + pubPumpOn, "true")

        if value == 2:
            log("Selected Dehumidifier = turn off", 4)
            client.publish(const.plantArray[self.plantNum] + pubEnableWatering, "false")
            self.char_active.set_value(0)

#
# def get_bridge(driver):
#     bridge = Bridge(driver, 'Bridge')
#
#     bridge.add_accessory(LightBulb(driver, 'Light bulb'))
#     bridge.add_accessory(FakeFan(driver, 'Big Fan'))
#     bridge.add_accessory(GarageDoor(driver, 'Garage'))
#     bridge.add_accessory(TemperatureSensor(driver, 'Sensor'))
#
#     return bridge
# ###


# MQTT
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    if rc == 0:
        print("-> This means we connected successfully")
        log("Connection to server successful", 2)
    else:
        print("Major connection error")
        raise SystemExit

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    for i in range(len(const.plantArray)):
        client.subscribe(const.plantArray[i] + subCurrentMoisture)
        client.subscribe(const.plantArray[i] + subEnableWatering)
        client.subscribe(const.plantArray[i] + subWaterTargetValue)
        client.subscribe(const.plantArray[i] + subPumpOn)


def on_message(client, userdata, msg):

    messageText = str(msg.payload, 'utf-8')
    print(msg.topic + " " + str(msg.payload))
    log(msg.topic + " " + messageText, 4)
    # CHECK FOR PLANT SPECIFIC MESSAGES
    for i in range(len(const.plantArray)):
        if msg.topic == const.plantArray[i]+subWatering:
            if messageText == "true":
                # set target state to humidify
                plantAccessories[i].char_target_state.set_value(1)
                plantAccessories[i].char_curr_state.set_value(2)
            if messageText == "false":
                # set target state to auto
                plantAccessories[i].char_target_state.set_value(0)
                plantAccessories[i].char_curr_state.set_value(1)

        if msg.topic == const.plantArray[i]+subEnableWatering:
            if messageText == "true":
                plantAccessories[i].char_active.set_value(1)
            if messageText == "false":
                plantAccessories[i].char_active.set_value(0)

        if msg.topic == const.plantArray[i]+subCurrentMoisture:
            plantAccessories[i].char_currentMoisture.set_value(int(messageText))

        if msg.topic == const.plantArray[i]+subWaterTargetValue:
            plantAccessories[i].char_threshold.set_value(int(messageText))


def log(text, level):
    if level <= const.debuglevel:
        print(const.debugStr[level]+text)
        client.publish("pyPlant/Log", const.debugStr[level]+text)


# sleep(10.0)  # wait for everything to connect (Wifi, etc)
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("10.0.0.16", 1883, 60)
client.loop_start()
sleep(2)
log("MQTT Started", 2)
log("Waiting For Everything To Settle", 2)
sleep(5)


driver = AccessoryDriver(port=51826, persist_file='busy_home.state')
bridge = Bridge(driver, 'Bridge')
plantAccessories = []
for plant in const.plantArray:
    plantAccessories.append(Plant(driver, 'Irrigation '+plant))
for i in range(len(const.plantArray)):
    plantAccessories[i].char_active.set_value(1)
    plantAccessories[i].char_name.set_value(const.plantArray[i])
    plantAccessories[i].plantNum = i
    bridge.add_accessory(plantAccessories[i])

# bridge.add_accessory(FakeFan(driver, 'Big Fan'))
# bridge.add_accessory(GarageDoor(driver, 'Garage'))
# bridge.add_accessory(TemperatureSensor(driver, 'Sensor'))

driver.add_accessory(accessory=bridge)
signal.signal(signal.SIGTERM, driver.signal_handler)
driver.start()

import logging
import signal

from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import (CATEGORY_HUMIDIFIER, CATEGORY_SENSOR, CATEGORY_SWITCH)

import matplotlib.pyplot as plt

import const

import json

import paho.mqtt.client as mqtt

from apscheduler.schedulers.background import BackgroundScheduler


from time import sleep

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")


import platform


# "MotionSensor": {
#     "OptionalCharacteristics": [
#         "StatusActive",
#         "StatusFault",
#         "StatusTampered",
#         "StatusLowBattery",
#         "Name"
#     ],
#     "RequiredCharacteristics": [
#         "MotionDetected"
#     ],
#     "UUID": "00000085-0000-1000-8000-0026BB765291"
# },
class MotionSensor(Accessory):


    category = CATEGORY_SENSOR
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


        motion = self.add_preload_service("MotionSensor")
        self.char_motion = motion.configure_char('MotionDetected')

        self.char_motion.set_value(False)


def signalMotion(plantNum, repeats):
    if plantNum == - 2:
        for repeat in range(repeats):
            MSLogger.char_motion.set_value(True)
            sleep(1)
            MSLogger.char_motion.set_value(False)
            sleep(1)

    elif plantNum == - 1:
        for repeat in range(repeats):
            MSpyPlant.char_motion.set_value(True)
            sleep(1)
            MSpyPlant.char_motion.set_value(False)
            sleep(1)
    else:
        for repeat in range(repeats):
            plantMotionSensors[plantNum].char_motion.set_value(True)
            sleep(1)
            plantMotionSensors[plantNum].char_motion.set_value(False)
            sleep(1)

def signalError(plantNum):
    signalMotion(plantNum, 3)

def signalEvent(plantNum):
    signalMotion(plantNum, 1)


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
class ErrorSwitch(Accessory):
    category = CATEGORY_SWITCH
    plantNum = - 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plantNum = const.currentPlant

        error_switch = self.add_preload_service('Switch',
                                                chars=['Name'])
        self.char_errorState = error_switch.configure_char(
                                            'On', setter_callback=self.setError)
        self.char_name = error_switch.configure_char('Name')


    def setError(self, value):
        resetErrors()
        client.publish(const.plantArray[self.plantNum] + const.pubMeasureNow, "true")





class Plant(Accessory):

    category = CATEGORY_HUMIDIFIER

    plantNum = - 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.plantNum = int(self.display_name)
        # self.display_name = str(const.plantArray[self.plantNum]+' Irrigation')
        self.plantNum = const.currentPlant
        plant_hum = self.add_preload_service("HumidifierDehumidifier",
                                             chars=['RelativeHumidityHumidifierThreshold',
                                                    'RelativeHumidityDehumidifierThreshold',
                                                    'Name'])
        self.char_name = plant_hum.configure_char('Name')

        # passive set via .set_value
        self.char_currentMoisture = plant_hum.configure_char('CurrentRelativeHumidity')
        self.char_currentMoisture.set_value(const.plantAccValues[const.currentPlant]["moisture"])

        # CurrentHumidifierDehumidifierState: 0,1,2,3
        # (inactive, idle, humidifying, dehumidifying)

        self.char_curr_state = plant_hum.configure_char('CurrentHumidifierDehumidifierState')
        if const.plantAccValues[const.currentPlant]["WateringEnabled"]:
            self.char_curr_state.set_value(1)
        else:
            self.char_curr_state.set_value(0)

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
        self.char_threshold.set_value(const.plantAccValues[const.currentPlant]["moistureTarget"])

        self.char_threshold_de = plant_hum.configure_char(
            'RelativeHumidityDehumidifierThreshold', setter_callback=self.set_humidity_de)
        self.char_threshold_de.set_value(100)
        self.set_info_service(firmware_revision=const.plantAccValues[const.currentPlant]["firmware"],
                              manufacturer="JPCG",
                              model="Nano"+const.plantAccValues[const.currentPlant]["wifiFirmware"])
        log("Created " + const.plantAccValues[const.currentPlant]['name'] + " accessory", 2)

    def set_active(self, value):
        # 0, 1
        # (inactive, active)
        log("Active: " + str(value), 5)

        if value == 0:
            log("Active: is 0, setting enable Watering to false", 5)
            client.publish(const.plantArray[self.plantNum] + const.pubPumpOn, "false")
            sleep(2)
            client.publish(const.plantArray[self.plantNum] + const.pubEnableWatering, "false")
        log("Active: is 1, setting enable Watering to true", 5)
        if value == 1:
            client.publish(const.plantArray[self.plantNum] + const.pubEnableWatering, "true")
            self.char_curr_state.set_value(1)

    def set_humidity_de(self, value):
        log("Set dehum value to " + str(value) + "-> Resetting to 100", 4)
        self.char_threshold_de.set_value(100)
        # self.char_threshold.set_value(value)
        # client.publish(const.plantArray[self.plantNum] + const.pubSetWaterTarget, value)
        # const.plantAccValues[self.plantNum]["moistureTarget"] = value

    def set_humidity(self, value):
        # hum_val = value + 10
        # if hum_val > 100: hum_val = 100
        # log("Set dehum_value to " + str(value), 4)
        # self.char_threshold.set_value(hum_val)
        # log("Setting hum_value to " + str(hum_val), 4)
        # client.publish(const.plantArray[self.plantNum] + const.pubSetWaterTarget, value)
        log("Setting hum_value to " + str(value), 4)
        self.char_threshold_de.set_value(100)
        self.char_threshold.set_value(value)
        client.publish(const.plantArray[self.plantNum] + const.pubSetWaterTarget, value)
        const.plantAccValues[self.plantNum]["moistureTarget"] = value

    def set_Target(self, value):
        # 0,1,2
        # (humidifier or dehumidifier ("Auto" in Homekit), humidifier, dehumidifier)
        log("set target: " + str(value), 4)
        if value == 0:
            log("Auto set", 4)

        if value == 1:
            log("Start Pump", 4)
            client.publish(const.plantArray[self.plantNum] + const.pubPumpOn, "true")

        if value == 2:
            log("Selected Dehumidifier = turn off", 4)
            client.publish(const.plantArray[self.plantNum] + const.pubEnableWatering, "false")
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
        client.subscribe(const.plantArray[i] + const.subCurrentMoisture)
        client.subscribe(const.plantArray[i] + const.subEnableWatering)
        client.subscribe(const.plantArray[i] + const.subWaterTargetValue)
        client.subscribe(const.plantArray[i] + const.subPumpOn)
        client.subscribe(const.plantArray[i] + const.subWatering)
        client.subscribe(const.plantArray[i] + const.subWifiFirmware)
        client.subscribe(const.plantArray[i] + const.subFirmware)
        client.subscribe(const.plantArray[i] + const.subPing)



def on_message(client, userdata, msg):
    updatePlot = False
    if const.init:  # disable receiving stray Messages during initial init -> errors
        messageText = str(msg.payload, 'utf-8')
        log(msg.topic + " " + messageText, 4)
        # CHECK FOR PLANT SPECIFIC MESSAGES
        for i in range(len(const.plantArray)):

            if msg.topic == const.plantArray[i]+const.subWatering:
                if messageText == "true":
                    # set target state to humidify
                    if const.init_HAP:  # disable reporting while plantAccessories is not yet initialized
                        plantAccessories[i].char_target_state.set_value(1)
                        plantAccessories[i].char_curr_state.set_value(2) # Set to Humidify
                if messageText == "false":
                    # set target state to auto
                    if const.init_HAP:
                        plantAccessories[i].char_target_state.set_value(0)
                        plantAccessories[i].char_curr_state.set_value(1)

            if msg.topic == const.plantArray[i]+const.subPumpOn:
                if messageText == "true":
                    # set target state to humidify
                    if const.init_HAP:
                        plantAccessories[i].char_target_state.set_value(1)
                        plantAccessories[i].char_curr_state.set_value(2)
                    const.plantAccValues[i]["WateringsOverLastDays"][len(const.plantAccValues[i]["WateringsOverLastDays"])-1]\
                        = const.plantAccValues[i]["WateringsOverLastDays"][len(const.plantAccValues[i]["WateringsOverLastDays"])-1]+1
                    updatePlot = True
                if messageText == "false":
                    if const.init_HAP:
                        # set target state to auto
                        plantAccessories[i].char_target_state.set_value(0)
                        plantAccessories[i].char_curr_state.set_value(1)
            if msg.topic == const.plantArray[i]+const.subEnableWatering:
                if messageText == "true":
                    if const.init_HAP:
                        plantAccessories[i].char_active.set_value(1)
                    const.plantAccValues[i]["WateringEnabled"] = True
                if messageText == "false":
                    if const.init_HAP:
                        plantAccessories[i].char_active.set_value(0)
                    const.plantAccValues[i]["WateringEnabled"] = False


            if msg.topic == const.plantArray[i]+const.subCurrentMoisture:
                if const.init_HAP:
                    plantAccessories[i].char_currentMoisture.set_value(int(messageText))
                const.plantAccValues[i]["moisture"] = int(messageText)
                if len(const.plantAccValues[i]["MeasurementValues"])>50:
                    const.plantAccValues[i]["MeasurementValues"].remove(const.plantAccValues[i]["MeasurementValues"][0])
                const.plantAccValues[i]["MeasurementValues"].append(int(messageText))
                updatePlot = True

            if msg.topic == const.plantArray[i]+const.subWaterTargetValue:
                if int(messageText) == 40 and const.plantAccValues[i]["moistureTarget"] != 40:  # 40 is standard val for arduino, set to current if 40
                    log("Inconsistent target value for Plant " + const.plantArray[i] +
                        ". Trying to set to " + str(const.plantAccValues[i]["moistureTarget"]) + "%", 2)
                    client.publish(const.plantArray[i] + const.pubSetWaterTarget,
                                   const.plantAccValues[i]["moistureTarget"])
                else:
                    if const.init_HAP:
                        plantAccessories[i].char_threshold.set_value(int(messageText))
                    if const.plantAccValues[i]["moistureTarget"] != int(messageText):
                        const.plantAccValues[i]["moistureTarget"] = int(messageText)
                        saveJson()


            if msg.topic == const.plantArray[i] + const.subFirmware:
                const.plantAccValues[i]["firmware"] = messageText
            if msg.topic == const.plantArray[i] + const.subWifiFirmware:
                const.plantAccValues[i]["wifiFirmware"] = messageText
            if msg.topic == const.plantArray[i]+const.subSwitchError:
                if messageText == "true":
                    # set target state to humidify
                    if const.init_HAP:
                        turnOnErrorSwitch(i)
                        const.plantAccValues[i]["Error"] = True
                elif messageText == "false":
                    if const.init_HAP:
                        # set target state to auto
                        const.plantAccValues[i]["Error"] = False
                        plantErrorSwitches[i].char_errorState.set_value(False)
                        const.plantAccValues[i]["SwitchOn"] = False
                        checkTurnOffErrorSwitch()
                updatePlot = True

            if msg.topic == const.plantArray[i]+const.subPing:
                const.plantAccValues[i]["Ping"] = True

            if msg.topic == const.plantArray[i]+const.subInfoText:
                const.plantAccValues[i]["InfoText"] = messageText
                updatePlot = True
    if updatePlot and const.pingingNow == False:
        updatePlots()


def checkChangedState(driver):
    if const.changedState:
        driver.config_changed()
        log("Told HomeKit that config changed", 4)
        const.changedState = False

def resetErrors():
    for plant in const.plantArray:
        log("Send /StartUpHAP to Refresh Errors for " + plant, 2)
        client.publish(plant + "/StartUpHAP", "Refresh")
        sleep(0.1)
    sleep(5)
    pingPlants()
    noErrors = True
    for plant in const.plantAccValues:
        if plant["SwitchOn"] == True : noErrors = False
    if noErrors:
        statusErrorSwitch.char_errorState.set_value(False)



def pingPlants():
    # First set Ping = false
    const.pingingNow = True
    for i in range(len(const.plantArray)):
        const.plantAccValues[i]["Ping"] = False
    # Ping Plants -> Ping gets set to true via MQTT Subscription
    for i in range(len(const.plantArray)):
        client.publish(const.plantArray[i] + const.pubPing, "Ping")
        sleep(0.1)
    sleep(7)
    # Check for Errors
    for i in range(len(const.plantArray)):
        if const.plantAccValues[i]["Ping"] == False or const.plantAccValues[i]["Error"] == True:
            turnOnErrorSwitch(i)
        else:
            plantErrorSwitches[i].char_errorState.set_value(False)
            const.plantAccValues[i]["SwitchOn"] = False
    checkTurnOffErrorSwitch()
    const.pingingNow = False
    updatePlots()

def turnOnErrorSwitch(i):
    plantErrorSwitches[i].char_errorState.set_value(True)
    statusErrorSwitch.char_errorState.set_value(True)
    const.plantAccValues[i]["SwitchOn"] = True

def checkTurnOffErrorSwitch():
    noErrors = True
    for plant in const.plantAccValues:
        if plant["SwitchOn"] == True : noErrors = False
    if noErrors:
        statusErrorSwitch.char_errorState.set_value(False)


def xyArraysForPlotting(startPoint, width,height, array, maxVal = -1):
    if maxVal == -1:
        maxVal = max(array)
        if maxVal==0: maxVal = 0.1
    yarray = []
    for i in range(len(array)):
        yarray.append (array[i]* height/maxVal + startPoint[1])
    xarray = []
    for i in range(len(array)):
        xarray.append(i*width/(len(array)-1)+startPoint[0])
    return xarray, yarray


def updatePlots():
    log("Updating Plot", 4)
    fig = plt.figure()
    ax = fig.add_subplot()
    plt.axis('off')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    arraySize = len(const.plantArray)
    ax.text(0.2, (arraySize) * 2 + 0.8, "Plant Name")
    ax.text(2, (arraySize) * 2 + 0.8, "State &")
    ax.text(2, (arraySize) * 2 + 0.25, "Error")
    ax.text(3.05, (arraySize) * 2 + 0.8, "Moisture (/d) &")
    ax.text(3.05, (arraySize) * 2 + 0.25, "Watering (5d)")
    ax.text(4.5, (arraySize) * 2 + 0.8, "Info")

    for i in range(arraySize):
        if const.plantAccValues[i]["WateringEnabled"]:
            ax.plot([0.07],[(arraySize-i)*2-1], marker="o", color='green')
        else:
            ax.plot([0.07], [(arraySize - i) * 2 - 1], marker=".", color='red')

        ax.text(0.2, (arraySize-i)*2-1.2, const.plantArray[i])
        if const.plantAccValues[i]["Ping"]:
            ax.text(2, (arraySize - i) * 2 - 1.2+0.4, "Responsive", color='green')
        else:
            ax.text(2, (arraySize - i) * 2 - 1.2+0.4, "Unresponsive", color='red')
        if const.plantAccValues[i]["Error"]:
            ax.text(2, (arraySize - i) * 2 - 1.2-0.5, "Error", color='red')
        else:
            ax.text(2, (arraySize - i) * 2 - 1.2-0.5, "No Error", color='green')

        xarray, yarray = xyArraysForPlotting( startPoint = [3.1, (arraySize - i) * 2 - 1.2-0.6],width= 1.2,height=0.8, array = const.plantAccValues[i]["WateringsOverLastDays"])
        ax.plot(xarray,yarray)

        for i2 in range (len(xarray)):
            ax.text(xarray[i2], yarray[i2], const.plantAccValues[i]["WateringsOverLastDays"][i2], color='black')
        xarray, yarray = xyArraysForPlotting(startPoint=[3.1, (arraySize - i) * 2 - 1.2 + 0.6], width=1.2, height=0.5, maxVal=100, array = const.plantAccValues[i]["MeasurementValues"])
        ax.plot(xarray, yarray)
        #ax.text(xarray[len(xarray)-1], yarray[len(yarray)-1], const.plantAccValues[i]["MeasurementValues"][len(xarray)-1], color='black')

        if const.plantAccValues[i]["InfoText"] == "":
            ax.text(4.5, (arraySize - i) * 2 - 1.2+0.4, "None", color='green')
        else:
            ax.text(4.5, (arraySize - i) * 2 - 1.2+0.4,
                    const.plantAccValues[i]["InfoText"], color='blue')
        ax.text(4.5, (arraySize - i) * 2 - 1.2 - 0.5,
                str(const.plantAccValues[i]["moisture"])+"% / "
                + str(const.plantAccValues[i]["moistureTarget"]) + "%")
        ax.plot([0, 5.5],[(arraySize-i)*2,(arraySize-i)*2])
    ax.plot([0, 5.5], [0,0])

    try:
        if const.isLinux:
            plt.savefig("/dev/shm/plants.png")
        else:
            plt.savefig("plants.png")
        log("Plot saved", 3)
    except:
        log("Plot saving not possible", 2)
    try:
        if const.isLinux:
            plt.savefig("/mnt/tmp/plants.png")
        log("Plot saved", 3)
    except:
        log("Plot saving not possible in /mnt/tmp", 2)
    plt.close('all')

def saveJson():
    try:
        with open('plantAccValues.json', 'w') as f:
            json.dump(const.plantAccValues, f)
        log("Saved json", 4)
    except:
        print("cannot open plantAccValues.json for write")

def log(text, level):
    if level <= const.debuglevel:
        print(const.debugStr[level]+text)
        try:
            client.publish("pyPlant/Log", const.debugStr[level]+text)
        except:
            print("Publishing via log not possible")

def newDay():
    for plant in const.plantAccValues:
        for i in range(len(plant["WateringsOverLastDays"])-1):
            plant["WateringsOverLastDays"][i]=plant["WateringsOverLastDays"][i+1]
        plant["WateringsOverLastDays"][len(plant["WateringsOverLastDays"])-1] = 0
    saveJson()


# sleep(10.0)  # wait for everything to connect (Wifi, etc)
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("10.0.0.50", 1883, 60)
client.loop_start()
sleep(2)
log("MQTT Started", 2)
const.init = True
sleep(2)



if platform.system() == "Linux":
    const.isLinux = True
    log("Running on Linux, saving plot to /dev/shm", 2)
else:
    const.isLinux = False
    log("Not Running on Linux, saving plot to project folder", 2)


#const.plantArray = sorted(const.plantArray, key=str.lower)
try:
    f = open('resetPyPlantValsOnStart.json')
    resetValsOnStart = json.load(f)
except:
    resetValsOnStart= "False"
    with open('resetPyPlantValsOnStart.json', 'w') as f:
        json.dump(resetValsOnStart, f)

print(resetValsOnStart.upper())
try:
    f = open('plantAccValues.json')
    const.plantAccValues = json.load(f)
    log("Loaded plantAccValues.json",2)
    if len(const.plantArray) != len(const.plantAccValues):
        const.plantAccValues =[]
        raise ValueError('Read JSON File not used: Different amount of plants')
    if resetValsOnStart.upper() == "TRUE":
        const.plantAccValues = []
        raise ValueError('Read JSON File not used: Reset requested in file')
except ValueError as err:
    log("Create plantAccValues from scratch", 3)
    log(",".join(err.args), 1)
    for plant in const.plantArray:
        const.plantAccValues.append({"name": plant,
                                 "moisture": 40,
                                 "moistureTarget": 40,
                                 "firmware": "0.1.0",
                                 "wifiFirmware": "0.1.0",
                                 "WateringEnabled": True,
                                 "Ping": True,
                                 "Error": False,
                                 "InfoText": "",
                                 "SwitchOn": False,
                                 "WateringsOverLastDays": [0, 0, 0, 0, 0],
                                 "MeasurementValues": [40, 60]
                                 })
    saveJson()
    with open('resetPyPlantValsOnStart.json', 'w') as f:
        json.dump("False", f)
except:
    log("File not found",3)
    for plant in const.plantArray:
        const.plantAccValues.append({"name": plant,
                                 "moisture": 40,
                                 "moistureTarget": 40,
                                 "firmware": "0.1.0",
                                 "wifiFirmware": "0.1.0",
                                 "WateringEnabled": True,
                                 "Ping": True,
                                 "Error": False,
                                 "InfoText": "",
                                 "SwitchOn": False,
                                 "WateringsOverLastDays": [0, 0, 0, 0, 0],
                                 "MeasurementValues": [40, 60]
                                 })
    saveJson()

updatePlots()

for plant in const.plantArray:
    log("Send /StartUpHAP for " + plant, 2)
    client.publish(plant+"/StartUpHAP", "Start")
    sleep(2)

log("Waiting For Delayed Responses", 2)
sleep(10)



driver = AccessoryDriver(port=51826, persist_file='busy_home.state')
bridge = Bridge(driver, 'Bridge')
plantAccessories = []
for i in range(len(const.plantArray)):
    # send Array value as initial display_name, gets replaced by const.plantAccValues["name"] in class
    # this workaround is so that the class knows its array position in const.plantAccValues.
    # Passing it to class otherwise caused several errors
    const.currentPlant = i
    plantAccessories.append(Plant(driver, const.plantArray[i]+' Irrigation'))
    plantAccessories[i].plantNum = i

for i in range(len(const.plantArray)):
    plantAccessories[i].char_active.set_value(1)
    bridge.add_accessory(plantAccessories[i])

# Error Switch
plantErrorSwitches = []
for i in range(len(const.plantArray)):
    const.currentPlant = i
    plantErrorSwitches.append(ErrorSwitch(driver, const.plantArray[i]))
    plantErrorSwitches[i].plantNum = i
    bridge.add_accessory(plantErrorSwitches[i])

statusErrorSwitch = ErrorSwitch(driver, "Plant Error")
statusErrorSwitch.plantNum = 0
bridge.add_accessory(statusErrorSwitch)

# Motion Sensors
plantMotionSensors = []
for i in range(len(const.plantArray)):
    plantMotionSensors.append(MotionSensor(driver, const.plantArray[i]+' Event Sensor'))
    bridge.add_accessory(plantMotionSensors[i])

MSLogger = MotionSensor(driver, "Logger Event Sensor")
bridge.add_accessory(MSLogger)
MSpyPlant = MotionSensor(driver, "pyPlant Event Sensor")
bridge.add_accessory(MSpyPlant)

const.init_HAP = True  # false when HAP is not completely initialized. Caused errors before

# bridge.add_accessory(FakeFan(driver, 'Big Fan'))
# bridge.add_accessory(GarageDoor(driver, 'Garage'))
# bridge.add_accessory(TemperatureSensor(driver, 'Sensor'))

scheduler = BackgroundScheduler(timezone="Europe/Berlin")
scheduler.start()
scheduler.add_job(pingPlants,  'interval', minutes=10)
scheduler.add_job(newDay,'cron', hour=0)

driver.add_accessory(accessory=bridge)
signal.signal(signal.SIGTERM, driver.signal_handler)
print("Properties after startup:")
print(const.plantAccValues)

pingPlants()

driver.start()






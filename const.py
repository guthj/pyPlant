plantArray=["AlocasiaZ", "Avocado", "CalathiaM", "Monstera", "CalathiaW", "FloridaGhost", "Melanochrysum"]

plantAccValues = []

init = False
init_HAP = False

currentPlant = 0

debuglevel = 5
# 0 none
# 1 error
# 2 notice (default)
# 3 info
# 4 debug
debugStr = ["None  :  ", "Error :  ", "Notice:  ", "Info  :  ", "Debug :  "]

changedState = False

pingOrResponse = True



pubPumpOn = "/Pump/setOn"
pubEnableWatering = "/enableWatering/setOn"
pubSetWaterTarget = "/WaterTarget/setValue"
pubReset = "/Kill"
pubPing = "/Ping/Signal"
pubMeasureNow = "/MeasureNow"

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
subFirmware =               "/Firmware"
subSwitchError =            "/Error"


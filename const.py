plantArray=["AlocasiaZ", "Avocado", "CalathiaM","Monstera"]

plantAccValues = []

init = False
init_HAP = False


debuglevel = 5
# 0 none
# 1 error
# 2 notice (default)
# 3 info
# 4 debug
debugStr = ["None  :  ", "Error :  ", "Notice:  ", "Info  :  ", "Debug :  "]

changedState = False




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
subFirmware =               "/Firmware"
# Import Libraries
import os
import glob
import time
from datetime import datetime
import threading
import random
import logging
import json

#Rpi related objects
from RPi import GPIO as GPIO
GPIO.setmode(GPIO.BCM)
#import drv8830 #motor drive library
import i2cdisplay


#fake rpi objects - use these when rpi not available
"""
#note this is a local pointer, adjust reference locale as needed.
import sys
sys.path.insert(1, '/Users/lsown/Desktop/ntxdev/simPi') 

import sim_RPi
import sim_drv8830
import sim_i2cdisplay

"""

"""
Notes to remember:
level sensors - signal goes HIGH when water detected
motor fault pins - need to configure for pullup, these go low when fault detected
button - we may want to add 0.1 uF to c7. Hi when button depressed.
"""

class aquarium:
    def __init__(self):

        logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.DEBUG, datefmt="%H:%M:%S")
        self.aquariumID = 100
        self.buttonTime = 0

        #simulated version 
        self.aqdict_sim = {
            'temp': random.randrange(0, 50),
            'drv0' : True if random.randrange(0,2) == 0 else False,
            'drv1' : True if random.randrange(0,2) == 0 else False,
            'drv0Spd' : 0,
            'drv1Spd' : 0,
            'aquaFlag' : random.randrange(0,2),
            'rsvLoFlag' : random.randrange(0,2),
            'rsvHiFlag' : random.randrange(0,2),
            'spareFlag' : random.randrange(0,2),
            'exchangeState' : False,
            'tempmax' : 40,
            'tempmin' : 10
            }

        import onewiretemp as onewiretemp
        self.aqtemp = onewiretemp.onewiretemp() #creates an temp object

        self.pinsIn = {
            #5 : {'name' : 'lvlEN', 'pinType': 'levelSensor', 'state' : 0},
            'buttonSig' : {'name' : 'buttonSig', 'pinType': 'interface', 'state' : 0, 'priorState' : 0, 'pin' : 23},
            'rsvHiFlag' : {'name' : 'rsvHiFlag', 'pinType': 'levelSensor', 'state' : 0, 'pin' : 6},
            'rsvLoFlag' : {'name' : 'rsvLoFlag', 'pinType': 'levelSensor', 'state' : 0, 'pin' : 13},
            'aquaFlag' : {'name' : 'aquaFlag', 'pinType': 'levelSensor', 'state' : 0, 'pin' : 19},
            'spareFlag' : {'name' : 'spareFlag', 'pinType': 'levelSensor', 'state' : 0, 'pin' : 26},
            'aquaKillFlag' : {'name' : 'aquaKillFlag', 'pinType' : 'levelSensor', 'state' : 0, 'pin' : 5},
            'stepFault' : {'name' : 'stepFault', 'pinType': 'motor', 'state' : 0, 'pin' : 17},
            'bdcFault' : {'name' : 'bdcFault', 'pinType': 'motor', 'state' : 0, 'pin' : 27},
            'dpFault' : {'name' : 'dpFault', 'pinType': 'motor', 'state' : 0, 'pin' : 22},
            'stepHome' : {'name' : 'stepHome', 'pinType' : 'motor', 'state' : 0, 'pin' : 8}
        }
        self.pinsOut = {
            #24 : {'name' : 'I2C RST', 'state' : 0},
            'pcaEN' : {'name' : 'pcaEN', 'state' : 0, 'pin' :  14}, #0 to EN LED outputs, totem-pole config
            'LEDPwr' : {'name' : 'LEDPwr', 'state' : 0, 'pin' : 25}, #unused - disconnected, default i2c controlled
            'stepDir' : {'name' : 'stepDir', 'state' : 0, 'pin' : 21},
            'stepEn' : {'name' : 'stepEn', 'state' : 1, 'pin' : 20}, #LOW to EN stepper
            'stepStep' : {'name' : 'stepStep', 'state' : 0, 'pin' : 18}, 
            'stepRST' : {'name' : 'stepRST', 'state' : 1, 'pin' : 12}, #0 to RST
            'stepSleep' : {'name' : 'stepSleep', 'state' : 1, 'pin' : 7} #unused - disconnected, HI to sleep
        }
        self.motors = {
            'drv0' : {'name' : 'wastePump', 'i2cAddress' : 0x60, 'speed' : 0, 'direction' : 'cw', 'faultpin' : 17, 'state' : 'cw: 0'},
            'drv1' : {'name' : 'containerPump', 'i2cAddress' : 0x61, 'speed' : 0, 'direction' : 'cw', 'faultpin' : 27, 'state' : 'cw: 0'},
            #'drv2' : {'name' : 'sparePump', 'i2cAddress' : 0x62, 'speed' : 0, 'direction' : 'cw', 'faultpin': 22}
        }
        logging.info('Initializing NTXpi object')
        self.piSetup() #sets up the pi pin configurations
        #self.drv8830Setup() #sets up the channels for i2c motor drivers
        self.stepMotor = stepMotor(500, 0)
        self.display = i2cdisplay.display() #creates a display object
        self.display.drawStatus(
            text1='NTXPi Ready', 
            text2=('temp: %s' %(str(self.get_temp())) 
                )
            )
        
        #self.displayThread = threading.Thread(target=self.stream_temp, daemon=True)
        #self.displayThread.start()

    def piSetup(self): #Sets up GPIO pins, can also add to GPIO.in <pull_up_down=GPIO.PUD_UP>

        for i in self.pinsOut:
            GPIO.setup(self.pinsOut[i]['pin'], GPIO.OUT, initial = self.pinsOut[i]['state']) #set GPIO as OUT, configure initial value
            logging.info('%s pin %s configured as OUTPUT %s' %(self.pinsOut[i]['name'], str(self.pinsOut[i]['pin']), self.pinsOut[i]['state']))

        for i in self.pinsIn:
            GPIO.setup(self.pinsIn[i]['pin'], GPIO.IN) #set GPIO as INPUT
            logging.info('%s pin %s configured as INPUT' %(self.pinsIn[i]['name'], str(self.pinsIn[i]['pin'])))

            self.pinsIn[i]['state'] = GPIO.input(self.pinsIn[i]['pin'])
            logging.info('%s initial state is %s' %(self.pinsIn[i]['name'], str(self.pinsIn[i]['state'])))

            #configure event detections for pinType levelSensor & interface
            if self.pinsIn[i]['pinType'] == 'levelSensor':
                GPIO.add_event_detect(self.pinsIn[i]['pin'], GPIO.BOTH, callback=self.levelSensor, bouncetime=500) 
                logging.info('%s set as levelSensor callback' %(str(self.pinsIn[i]['name'])))
            elif self.pinsIn[i]['pinType'] == 'interface':
                GPIO.add_event_detect(self.pinsIn[i]['pin'], GPIO.RISING, callback=self.buttonPress, bouncetime=500) 
                logging.info('%s set as button callback' %(str(self.pinsIn[i]['name'])))

    def get_status(self):
        return {
            'temp': self.get_temp(), #0 is celcius, 1 is farenheit
            'motor1' : self.motors['drv0']['state'],
            'motor2' : self.motors['drv0']['state'],
            'aquaFlag' : self.pinsIn['aquaFlag']['state'],
            'rsvLoFlag' : self.pinsIn['rsvLoFlag']['state'],
            'rsvHiFlag' : self.pinsIn['rsvHiFlag']['state'],
            'spareFlag' : self.pinsIn['spareFlag']['state'],
            'time' : datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        } #0 is celcius, 1 is farenheit

    def get_temp(self):
        return self.aqtemp.read_temp()[0]

    def stream_temp(self):
        while True:
            self.get_temp()
            self.display.drawStatus(text1='Temp Grab', text2=('temp: %s' %(str(self.get_temp()))))
            time.sleep(5)

    def flag_hi(self):
        for i in self.pinsIn:
            if i['pinType'] == 'levelSensor':
                if i['state'] == 1:
                    return True


    def updateState(self, channel, value):
        for i in self.pinsIn:
            if channel == self.pinsIn[i]['pin']:
                self.pinsIn[i]['state'] = value
                print('%s pin triggered, %s configured state to %s' %(str(channel), self.pinsIn[i]['name'], self.pinsIn[i]['state'])) # debug

    def buttonPress(self, channel):
        print('button press detected: prior state was %s' %(str(self.pinsIn['buttonSig']['priorState'])))
        if ((time.time() - self.buttonTime) > 1):
            self.updateState(channel, 1)
            if self.pinsIn['buttonSig']['priorState'] == 0:
                GPIO.output(self.pinsOut['LEDPwr']['pin'], 1)
                self.pinsIn['buttonSig']['priorState'] = 1
                self.display.drawStatus(text1='pumping', text2=('temp: %s' %(str(self.get_temp()))))
                
                if self.pinsIn['aquaFlag']['state'] == 0:
                    self.stepMotor.stepInfinite('cw')
                else:
                    pass
                    logging.info('Aqua Flag still high, motor remains disabled')              
                '''
                #old code for running
                motorThread = threading.Thread(target=self.drv8825, args=(600,0,10000,), daemon=True)
                motorThread.start()
                '''
            else:
                GPIO.output(self.pinsOut['LEDPwr']['pin'], 0)
                self.pinsIn['buttonSig']['priorState'] = 0
                self.display.drawStatus(text1='NTXPi Ready!', text2=('temp: %s' %(str(self.get_temp()))))    
                self.stepMotor.disableMotor() #disables stepper
            print('LED state changed to %s' %(str(self.pinsIn['buttonSig']['priorState'])))
            self.buttonTime = time.time() #sets a time for last button press
        global exit_loop
        exit_loop = True

    def levelSensor(self, channel):
        if GPIO.input(channel) == 1:
            self.updateState(channel, 1)
            #self.motorControl(name='drv0', speed=0, direction = 'brake')
            self.stepMotor.disableMotor() #disables stepper
            self.display.drawStatus(text1='Full Aquarium', text2=('temp: ' + str(self.get_temp())))
        if GPIO.input(channel) == 0:
            self.updateState(channel, 0)

    def writeConfig(self, data, filename = 'aqConfig.json'):
        with open(filename, 'w') as outfile:
            json.dump(data, outfile)
            outfile.close()

    def readConfig(self, filename = 'aqConfig.json'):
        with open(filename, 'r') as json_data_file:
            data = json.load(json_data_file)
            json_data_file.close()
            return data


'''
    def motorFault(self, channel):
        #GPIO.add_event_detect(channel, GPIO.RISING, callback=my_callback, bouncetime=200)
        for i in self.motors:
            if self.motors[i]['faultpin'] == channel:
                logging.info("%s has tripped a fault" %(str(i)))

    def motorControl(self, name='drv0', i2cAddress=0x60, speed=1, direction='forward'):
        if speed > 1:
            speed = 1
        voltage = (2 * float(speed)) + 3 #looks like min. speed of our pump is 3V

        if name == 'drv0':
            self.drv0.set_direction(direction)
            self.drv0.set_voltage(voltage)
            print("Setting direction " + name + " " + direction + " " + str(voltage))

        if name == 'drv1':
            self.drv1.set_direction(direction)
            self.drv1.set_voltage(voltage)
            print("Setting direction " + name + direction + " " + str(voltage))

        self.motors[name]['speed'] = speed
        self.motors[name]['direction'] = direction
        self.motors[name]['state'] = (direction + " direction @ speed " + str(speed))

    def drv8830Setup(self):
        self.drv0 = drv8830.DRV8830(i2c_addr=0x60)
        self.drv1 = drv8830.DRV8830(i2c_addr=0x61)
        #self.drv2 = drv8830.DRV8830(i2c_addr=0x62) #note, change HW to 0x63 to work with library
'''

'''
class myThread (threading.Thread):
   def __init__(self, threadID, name, counter, functionPass):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.counter = counter
   def run(self):
      print("Starting thread: " + self.name)
      self.functionPass
      print("Exiting thread: " + self.name)
'''

class stepMotor:
    def __init__(self, frequency, direction, steps=0, disable = False, dutyCycle = 50, stepEnPin = 20, stepDirPin = 21, stepStepPin = 18, stepRSTPin = 12, stepSleepPin = 7):
        self.frequency = frequency
        self.direction = direction
        self.steps = steps
        self.disable = disable
        self.dutyCycle = dutyCycle #default 50%
        self.stepEnPin = 20
        self.stepDirPin = 21
        self.stepStepPin = 18
        self.stepRSTPin = 12
        self.stepSleepPin = 7
        
        self.pwm = GPIO.PWM(self.stepStepPin, self.frequency) #initializes pwm object
        self.initMotor()

    def initMotor(self):
        GPIO.output(self.stepRSTPin, 1)
        GPIO.output(self.stepSleepPin, 1)

    def calculateTime(self, frequency, steps):
        stepTime = 1/frequency/2 #duration for high, duration for low
        totalTime = 1/frequency * steps #calculates total estimated time for routine to finish
        logging.info("Stepper estimated time %s" %(str(totalTime)))
        return [totalTime, stepTime]

    def enableMotor(self):
        GPIO.output(self.stepEnPin, 0)
        self.pwm.start(self.dutyCycle)
        logging.info("motor enabled")

    def disableMotor(self):
        GPIO.output(self.stepEnPin, 1)
        self.pwm.stop()
        logging.info("motor disabled")

    def changeRotation(self, rotation):
        if (rotation == 'cw'):
            GPIO.output(self.stepDirPin, 0)
            self.direction = 0 #update direction of object
            logging.info("set to cw, stepDirPin LOW")
        else:
            GPIO.output(self.stepDirPin, 1)
            self.direction = 1 #update direction of object
            logging.info("set to ccw, stepDirPin HI")

    def changeFrequency(self, frequency):
        self.frequency = frequency #update frequency of object
        self.pwm.ChangeFrequency(frequency)
        logging.info("Frequency changed to %s Hz" %(frequency))

    def changeDutyCycle(self, dutyCycle):
        self.dutyCycle = dutyCycle #update dutyCycle of object
        self.pwm.ChangeDutyCycle(dutyCycle)
        logging.info("Duty cycle changed %s percent" %(str(dutyCycle)))

    def stepRequest(self, steps):
        self.enableMotor()
        totalTime = 1 / self.frequency * steps
        logging.info("Estimated time for %s steps @ %s: %s" %(str(steps), str(self.frequency), str(totalTime)))
        timerThread = threading.Timer(totalTime, self.disableMotor)

        timerThread.start()

    def stepInfinite(self, rotation):
        self.changeRotation(rotation)
        self.enableMotor()

    def stepConfig(self, frequency, rotation, dutyCycle):
        self.changeFrequency(frequency)
        self.changeRotation(rotation)
        self.changeDutyCycle(dutyCycle)
                
        



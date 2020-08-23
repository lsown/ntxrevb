# Import Libraries
import os
import glob
import time

# Initialize the GPIO Pins
os.system('modprobe w1-gpio') # Turns on the GPIO module
os.system('modprobe w1-therm') # Turns on the Temperature module

# Finds the correct device file that holds the temperature data

class onewiretemp:

    def __init__(self):
        self.base_dir = '/sys/bus/w1/devices/'
        #the 0 pulls the item out of a list, which is what glob creates.
        if glob.glob(self.base_dir + '28*'): # validation if it exists
            self.device_folder = glob.glob(self.base_dir + '28*')[0]
        else: 
            self.device_folder = 'failed'
        self.device_file = self.device_folder + '/w1_slave'

    # A function that reads the sensors data
    def read_temp_raw(self):
        #simulated w1 - provides a failed simulation
        if self.device_file == 'failed/w1_slave':
            lines = ['YES', 't=0']
        #normal operation
        else:
            f = open(self.device_file, 'r') # Opens the temperature device file
            lines = f.readlines() # Returns a list of 2 strings
            f.close()
        return lines

    # Convert the value of the sensor into a temperature
    def read_temp(self):
        lines = self.read_temp_raw() # Read the temperature 'device file'

    # While the first line does not contain 'YES', wait for 0.2s
    # and then read the device file again.
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = self.read_temp_raw()

    # Look for the position of the '=' in the second line of the
    # device file.
        equals_pos = lines[1].find('t=')

    # If the '=' is found, convert the rest of the line after the
    # '=' into degrees Celsius, then degrees Fahrenheit
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            temp_f = temp_c * 9.0 / 5.0 + 32.0
            return temp_c, temp_f

    def test(self):
        return 30
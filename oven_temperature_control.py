'''
Version 1.5 last updated on 02-Aug-2018
https://github.com/RickyZiegahn/Oven-Temperature-Controller 
Made for McGill University under D.H. Ryan
'''

import serial
import time
from pyqtgraph.Qt import QtGui
import pyqtgraph as pg
import os
import sys

pname = 'COM3'
channelamount = 2 #amount of channels to recieve data from
band = [5,5] #bands for channel 0 and channel 1
integral_time = [10,10] #integral times for channel 0 and channel 1
logging = 'on' #set logging to 'on' or 'off' to enable real time plots and textfile logging
sample_option = 'on' #set to 'on' or 'off' to disable sample sensor (must be changed on the Arduino as well)

dt = 1 #time interval between measurements (must be equal to that on the arduino)
inputfile = 'tempinputoven.txt' #name of the input file
maxdata = 300 #length of time axis during plotting

ser = serial.Serial(port=pname,baudrate=9600, timeout=10)

'''
initialize lists so that changing the channel amount is the only work that must
be done in the python code to be ready for more heaters
'''
input_temperature = []
set_temperature = []
measured_temperature = []
sample_temperature = []
proportional_term = []
integral_term = []
output = []
flag = []
sample_flag = 0
if logging == 'on':
    logpath = 'heater logs/'
    app = []
    p = []
    curve = []
    datafile = []
    flag = []
    if not os.path.exists(os.path.dirname(logpath)): #create the path if it doesn't exist
        try:
            os.makedirs(os.path.dirname(logpath))
        except OSError:
            if not os.path.isdir(logpath):
                raise
'''
fill the lists with default values and have the amount of items equal to the amount
of channels
'''
for channel in range (0,channelamount):
    input_temperature.append(-1) #default to -1 so it will always be updated to zero immediately when the program begins
    set_temperature.append(-1)
    measured_temperature.append([]) #creates a 2 dimensional list, each sub list will contain all the measured temperature for a channel
    proportional_term.append(0)
    integral_term.append(0)
    output.append(0)
    flag.append(0)
    
    if logging == 'on':
        app.append(QtGui.QApplication([]))
        p.append(pg.plot())
        p[channel].setLabel('top', 'Channel ' + str(channel))
        p[channel].setLabel('bottom', 'Time (s)')
        p[channel].setLabel('left', 'Temperature (Degrees Celsius)')
        p[channel].enableAutoRange(x=True,y=False)
        curve.append(p[channel].plot())
        
        datafile.append(logpath + time.strftime('%Y%m%d %H%M%S') + ' CHANNEL ' + str(channel) + ' log.txt') #replace \\ with / on Linux or MacOS
        try:
            with open(datafile[channel], 'w') as fdata:
                fdata.write('TIME TEMPERATURE PROPORTIONAL INTEGRAL OUTPUT')
        except IOError: #if there is error saving (caused by Cloud Services), the program will not crash
            print 'Creation of Channel ' + str(channel) + ' log file failed'

if sample_option == 'on':
    if logging == 'on':
        sample_app = QtGui.QApplication([])
        sample_p = pg.plot()
        sample_p.setLabel('top', 'Sample Channel')
        sample_p.setLabel('bottom', 'Time (s)')
        sample_p.setLabel('left', 'Temperature (Degrees Celsius)')
        sample_p.enableAutoRange()
        sample_curve = sample_p.plot()
        sample_flag = 0
        
        samplefile = logpath + time.strftime('%Y%m%d %H%M%S') + ' SAMPLE log.txt' #replace \\ with / on Linux or MacOS
        try:
            with open(samplefile, 'w') as fdata:
                fdata.write('TIME TEMPERATURE')
        except IOError: #if there is error saving (caused by Cloud Services), the program will not crash
            print 'Creation of sample log file failed'

with open(inputfile, 'w') as ftemp:
    '''
    Create a text file to input desired temperatures for channels. Text file is
    created with enough inputs for the channels
    '''
    for channel in range (0,channelamount):
        ftemp.write('Target Temperature for Channel ' + str(channel) + ', in Degrees Celsius (do not include units):\n' +
            '000.00\n')

def read_target_temp(channel):
    '''
    Reads the current temperature of a given channel. The input for channel 0
    will appear on line 1, channel 1 on line 3, channel 2 on line 5, channel 4
    on line 7, etc. This follows the pattern <channel> * 2 + 1
    '''
    with open(inputfile, 'r') as ftemp:
        inputlines = ftemp.readlines()
        try:
            float(inputlines[(2*channel + 1)]) #checks that the input is a number
            input_temperature[channel] = round(float(inputlines[(2*channel + 1)].strip()))
        except ValueError:
            print 'Error: Temperature for Channel ' + str(channel) + ' input is not in the correct format.'
        
def give_target_settings(channel):
    '''
    Checks if the temperature inputted is different from the last temperature
    given to the controller. Sends the new temperature if it is different. All
    values are multiplied for because the thermocouple reader is accurate up
    to a quarter of a degree. It is divided by 4 once its reaches the Arduino
    '''
    if input_temperature[:] != set_temperature[:]:
        writestring = '' #empty string for new commands
        for channel in range (0,channelamount): #create a single string with all parameters.
            writestring += str(int(input_temperature[channel] * 4)) + ',' + str(int(round(band[channel]*4))) + ',' + str(int(round(integral_time[channel]*1000*4))) + ','
        ser.write(writestring)
        set_temperature[:] = input_temperature[:]
        
def read_measured_temp(channel):
    '''
    Read the temperature and add it to a list of temperatures for graphing.
    '''
    rstr = ser.readline().strip()
    try:
        rfloat = float(rstr)
    except ValueError:
        print 'Failed to connect to Arduino. Please restart the program.'
        time.sleep(1000)
        sys.exit()
    if channel == 'sample':
        sample_temperature.append(rfloat)
        if rstr == 'nan':
            sample_flag = 1
    else: #if it isn't sample, it'll be a numbered channel
        measured_temperature[channel].append(rfloat)
        if rstr == 'nan':
            flag[channel] = 1

def read_state(channel):
    '''
    Reads the weights of each term (output, proprortional term, integral term)
    '''
    output[channel] = ser.readline().strip()
    proportional_term[channel] = ser.readline().strip()
    integral_term[channel] = ser.readline().strip()
    if flag[channel] == 1:
        output[channel] = 'nan'
        proportional_term[channel] = 'nan'
        integral_term[channel] = 'nan'
    
times = []
time.sleep(2) #time for Arduino to start up and connect

while True:
    for channel in range (0,channelamount):
        read_target_temp(channel)
        give_target_settings(channel)
        read_measured_temp(channel)
        read_state(channel)
    try:
        times.append(times[-1] + dt)
    except IndexError: #if the list is empty, it will append the first value
        times.append(dt)
    if sample_option == 'on':
        read_measured_temp('sample')
    
    if logging == 'on': #only plot and log if logging is on
        for channel in range (0,channelamount):    
            if flag[channel] == 0:
                curve[channel].setData(x = times[-maxdata:], y = measured_temperature[channel][-maxdata:]) #only shows the last 60 seconds of measurements
                #if the last quarter of the data was within the band, change
                #the range so that it only shows the values within the band
                if (
                    (max(measured_temperature[channel][-int(maxdata/4):]) <= set_temperature[channel] + band[channel]/2)
                    and (min(measured_temperature[channel][-int(maxdata/4):]) >= set_temperature[channel] - band[channel]/2)
                    ):
                    p[channel].disableAutoRange()
                    p[channel].enableAutoRange(x=True,y=False)
                    p[channel].setYRange((set_temperature[channel] - band[channel]/2), (set_temperature[channel] + band[channel]/2))
                #if it moves out of the band, move it back to automatically scaling
                else:
                    p[channel].enableAutoRange()
                app[channel].processEvents() #update the graph
                try:
                    with open(datafile[channel], 'a') as fdata: #log to text file
                        fdata.write('\n' + str(times[-1]) + ' ' + str(measured_temperature[channel][-1]) + ' ' + str(proportional_term[channel]) + ' ' + str(integral_term[channel]) + ' ' + str(output[channel]))
                except IOError: #if there is error saving (caused by Cloud Services), the program will not crash
                    print 'Logging for Channel ' + str(channel) + ' at time ' + str(times[-1]) + ' has failed.'
        if sample_option == 'on':
            if sample_flag == 0:
                sample_curve.setData(x=times[-maxdata:], y = sample_temperature[-maxdata:]) #update the data
                sample_app.processEvents() #update the graph
                try:
                    with open(samplefile, 'a') as fdata: #log to text file
                        fdata.write('n' + str(times[-1]) + ' ' + str(sample_temperature[-1]))
                except IOError: #if there is error saving (caused by Cloud Services), the program will not crash
                    print 'Logging for Sample Channel at time ' + str(times[-1]) + ' has failed.'
    
    if len(times) > maxdata: #keep memory usage down
        times.pop(0)
        for channel in range (0,channelamount):
            measured_temperature[channel].pop(0)
        if sample_option == 'on':
            sample_temperature.pop(0)
    
    print '\n\n\nCurrent date and time: ' + time.strftime('%Y-%m-%d at %H:%M:%S')
    if sample_option == 'on':
        print '\nSample Channel'
        if sample_flag == 0:
            print 'Temperature: '+ str(sample_temperature[-1])
        if sample_flag == 1:
            print 'Thermocouple is not functioning'
    for channel in range (0,channelamount): 
        print '\nChannel ' + str(channel)
        if flag[channel] == 0:
            print 'Target Temperature: ' + str(set_temperature[channel])
            print 'Temperature: ' + str(measured_temperature[channel][-1])
            if logging == 'on': #still gets read earlier (not too much overhead there), but is not important to show if not logging
                print 'Output: ' + str(output[channel])
                print 'Proportional term: ' + str(proportional_term[channel])
                print 'Integral term: ' + str(integral_term[channel])
        if flag[channel] == 1:
            print 'Thermocouple is not functioning'
    print '\n-----------------------------------------------------------------------'
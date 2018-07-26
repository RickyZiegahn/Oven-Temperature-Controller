#Version 1.1 last updated on 26-Jul-2018
#https://github.com/RickyZiegahn/Oven-Temperature-Controller 

import serial
import time
from pyqtgraph.Qt import QtGui
import pyqtgraph as pg

pname = 'COM3'

ser = serial.Serial(port=pname,baudrate=9600, timeout=10)

logging = 'off' #set logging to 'on' or 'off', to create textfiles containing the readings

delaytime = 2 #time needed so arduino catches all commands
dt = 1 #time interval between measurements (must be equal to that on the arduino)
inputfile = 'tempinputoven.txt'
channelamount = 1 #amount of channels to recieve data from
maxdata = 300 #length of time axis during plotting

'''
initialize lists so that changing the channel amount is the only work that must
be done in the python code to be ready for more heaters
'''
input_temperature = []
set_temperature = []
band = []
integral_time = []
measured_temperature = []
sample_temperature = []
proportional_term = []
integral_term = []
output = []
app = []
p = []
curve = []
datafile = []
flag = []

'''
fill the lists with default values and have the amount of items equal to the amount
of channels
'''
for channel in range (0,channelamount):
    input_temperature.append(-1) #default to -1 so it will always be updated to zero immediately when the program begins
    set_temperature.append(-1)
    band.append(5)
    integral_time.append(10)
    measured_temperature.append([]) #creates a 2 dimensional list, each sub list will contain all the measured temperature for a channel
    proportional_term.append(0)
    integral_term.append(0)
    output.append(0)
    flag.append(0)
    
    app.append(QtGui.QApplication([]))
    p.append(pg.plot())
    p[channel].setLabel('top', 'Channel ' + str(channel))
    p[channel].setLabel('bottom', 'Time (s)')
    p[channel].setLabel('left', 'Temperature (Degrees Celsius)')
    p[channel].enableAutoRange(x=True,y=False)
    curve.append(p[channel].plot())

    if logging == 'on':
        datafile.append(time.strftime('%Y%m%d %H%M%S') + ' channel ' + str(channel) + ' log.txt')
        with open(datafile[channel], 'w') as fdata:
            fdata.write('TIME TEMPERATURE PROPORTIONAL INTEGRAL OUTPUT')

sample_app = QtGui.QApplication([])
sample_p = pg.plot()
sample_p.setLabel('top', 'Sample Channel')
sample_p.setLabel('bottom', 'Time (s)')
sample_p.setLabel('left', 'Temperature (Degrees Celsius)')
sample_p.enableAutoRange()
sample_curve = sample_p.plot()
sample_flag = 0

if logging == 'on':
    samplefile = time.strftime('%Y%m%d %H%M%S') + ' Sample log.txt'
    with open(samplefile, 'w') as fdata:
        fdata.write('TIME TEMPERATURE')

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
            float(inputlines[(channel + 1)]) #checks that the input is a number
            input_temperature[channel] = float(inputlines[(2*channel + 1)].strip())
        except ValueError:
            print 'Error: Temperature ' + str(channel) + ' input is not in the correct format.'
        
def give_target_settings(channel):
    '''
    Checks if the temperature inputted is different from the last temperature
    given to the controller. Sends the new temperature if it is different.
    '''
    if input_temperature[:] != set_temperature[:]:
        for channel in range (0,channelamount):
            ser.write(str(input_temperature[channel]))
            time.sleep(delaytime)
            ser.write(str(band[channel]))
            time.sleep(delaytime)
            ser.write(str(integral_time[channel] * 1000)) #arduino takes time in milliseconds
            time.sleep(delaytime)
        set_temperature[:] = input_temperature[:]
        
def read_measured_temp(channel):
    '''
    Read the temperature and add it to a list of temperatures for graphing.
    '''
    rstr = ser.readline().strip()
    rfloat = float(rstr)
    measured_temperature[channel].append(rfloat)
    if rstr == 'nan':
        flag[channel] = 1
        print 'Thermocouple on Channel ' + str(channel) + ' is not functioning.'
    else:
        flag[channel] = 0

def read_sample_temperature():
    rstr = ser.readline()
    rfloat = float(rstr)
    sample_temperature.append(rfloat)
    if rstr == 'nan':
        sample_flag = 1
        print 'Thermocouple on Sample is not functioning.'
    else:
        sample_flag = 0

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
time.sleep(1.5)

while True:
    for channel in range (0,channelamount):
        read_target_temp(channel)
        give_target_settings(channel)
        read_measured_temp(channel)
        read_state(channel)
    try:
        times.append(times[-1] + dt)
    except IndexError:
        times.append(dt)
    read_sample_temperature()
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
    
    if sample_flag == 0:
        sample_curve.setData(x=times[-maxdata:], y = sample_temperature[-maxdata:])
        sample_app.processEvents() #update the graph

    if len(times) > 300: #keep memory usage down
        times.pop(0)
        for channel in range (0,channelamount):
            measured_temperature[channel].pop(0)
        sample_temperature.pop(0)

    if logging == 'on':
        for channel in range (0,channelamount):
            with open(datafile[channel], 'a') as fdata:
                fdata.write('\n' + str(times[-1]) + ' ' + str(measured_temperature[channel][-1]) + ' ' + str(proportional_term[channel]) + ' ' + str(integral_term[channel]) + ' ' + str(output[channel]))
        with open(samplefile, 'a') as fdata:
            fdata.write('n' + times[-1] + ' ' + sample_temperature[-1])
    
    print '\n\nCurrent date and time: ' + time.strftime('%Y-%m-%d at %H:%M:%S') + '\n'
    print 'Sample Temperature: ' + str(sample_temperature[-1]) + '\n' + str(sample_flag) + '\n'
    for channel in range (0,channelamount): 
        print 'Channel ' + str(channel)
        print str(flag[channel])
        print 'Target Temperature: ' + str(set_temperature[channel])
        print 'Temperature: ' + str(measured_temperature[channel][-1])
        print 'Output: ' + str(output[channel])
        print 'Proportional term: ' + str(proportional_term[channel])
        print 'Integral term: ' + str(integral_term[channel])
        print '\n'
    print '\n-----------------------------------------------------------------------\n'
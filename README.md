# Victron BMV-70x logger (Domoticz and standalone) 
Monitor the Victron BMV-70x and optionally upload data to Domoticz as JSON via a LUA parser. Optionally log data to a CSV file.
Adapted from various versions of vedirect.py, particularly https://github.com/karioja/vedirect/blob/master/vedirect.py.  Many references here: https://www.victronenergy.com/live/open_source:start
Uses VE.Direct protocol and updated to use Python v3

## vedirect.lua
Lua script to parse json data to domoticz devices via their IDs

### Installation
* Install to your Domoticz folder i.e. /domoticz/scripts/lua_parsers
* Create a BMV parser hardware type 'Dummy' in Domoticz
* Create BMV devices in Domoticz using 'Create Virtual Sensors' button in the Dummy hardware
Example: BMV Volts, BMV Amps, BMV Power, BMV SOC, BMV AHr
* Go to the Devices page and filter for 'BMV' to make them easier to spot.
* Note the Domoticz index (Idx) for each device and update vedirect.lua for each item in the array.

This script is triggered by a URL generated in the python script vedirect.py (see below).  When the BMV python script sends a command to Domoticz, formatted as a JSON URL, this Lua script intercepts and parses the values to Domoticz. The values may be corrected with multipliers.

If you rename this script, change the name also in the python calling script. i.e. vedirect.py.

## vedirect.py
Version 2.0, Python 3

Send Victron BMV (702) values to Domoticz as JSON and/or optionally log to CSV data file.

Example URL: http://domoticz_domain_orIP#:port#/json.htm?type=command&param=udevices&script=ap_bmv.lua&data={"H2":0,"H3":0,"Alarm":"OFF","H7":46666,"V":54645,"FW":307,"H10":14,"H4":0,"H8":60004,"H11":0,"H12":0,"SOC":1000,"H1":-170364,"AR":0,"BMV":700,"CE":0,"P":29,"Relay":"OFF","I":530,"PID":"0x203","TTG":-1,"H9":0,"H17":26572,"H5":0,"H18":41698,"H6":-7695869}

Adapted from various versions of vedirect.py, particularly https://github.com/karioja/vedirect/blob/master/vedirect.py

### Installation
* Install in your chosen folder i.e. /monitor/bmv/vedirect.py
* Set up to run at system startup.
Example: create /lib/systemd/system/victron.service

[Unit]
Description=Victron BMV logging service
After=multi-user.target

[Service]
Type=idle
ExecStart=/usr/bin/python3 /home/pi/monitor/bmv/vedirect.py

[Install]
WantedBy=multi-user.target

### User Variables (review and modify for your setup)
logger_name = "vedirect"
>> name used for log file names, messages, etc

debug_level='debug'
>> debug options: DEBUG, INFO, WARNING, ERROR, CRITICAL
>> debug is verbose, error produces no error logs unless there is an error.
                          
domain="http://rpi3:8080"
>> enter your Domoticz IP address

parse_script = "ap_bmv.lua"
>> script to parse values to Domoticz. Lives in ~/domoticz/scripts/lua_parsers

port = '/dev/serial/by-id/usb-VictronEnergy_BV_VE_Direct_cable_VE3MQXH-if00-port0'
>> set to empty "" if parsing to Domoticz is not required.
>> Verify your serial port in Windows using Device Manager or in Linux by looking at /var/log/syslog when inserting cable OR ls -l /dev/serial/by-id/
>> See file /etc/udev/rules.d/99_usbdevices.rules for vedirectUSB device:
>> SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6015", SYMLINK+="vedirectUSB"
>> Use direct name to prevent issues with USB port swapping, otherwise Windows i.e. 'COM5', Linux try '/dev/ttyUSB0'

delay_time = 30
>> script interval time in seconds
                          
dataFile_columns = "Time," + "Volts," + "Amps," + "AHr," + "SOC"
>> layout for csv data log file.  Set to empty "" to prevent datafile logging.
                          
log_dict = OrderedDict()
>> Ordered dictionary, as we want to insert the values into the file as listed. Not required in Python 3.7+?
                          
log_dict.update([("V", 0.001),("I", 0.001),("CE", 0.001),("SOC", 0.1)])
>> Instantiate dictionary, match dataFile_columns keys and order. Use BMV key names and required multiplier

### Notes
This version adds the ability to optionally log data to a CSV file.  Domoticz only keeps max. and min. values after one day, so I would like to use the shorter interval values for graphing.  The file vedirect_data.csv is saved by default in the same directory as the python script.

I have left in extensive error logging code, as this is how I learnt how the program worked.  The error log vedirect.log is saved by default in the same directory.

I have found over several years that there were some issues:
  1. The updates in Domoticz get further behind as time goes on.
  2. The program fails and stops from time to time.
  3. It would seem to get 'stuck' occasionally, parsing the same values until restarted.
  
To resolve these issues, the 'input' processing routine has been changed slightly from the original vedirect.py:
  1. The original code returns the 'H' registers from the BMV on one pass and the other registers on another.  These are called blocks in the VE.Direct-Protocol-3.25 document.  The code now loops twice to update the dictionary with both blocks before parsing the json string to Domoticz.  This seems to have improved accuracy and reliability. 
  2. In the self.HEX state, the following byte appears mostly in the data to be header1, not header2.
  3. The hex bytes regularly appeared after the Checksum value, so by including these and updating self.bytes_sum, I didn't get as many malformed packets.
  4. Clear the dictionary after a malformed packet, as these would gradually increase the size of the dictionary over time.
 
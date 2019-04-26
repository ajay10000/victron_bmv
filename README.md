Victron BMV monitor.  VE.Direct protocol, using Python v3
Monitor the Victron BMV-70x, optionally upload data to Domoticz as JSON via a LUA parser.
Optionally log data to a CSV file.
Adapted from Victron's vedirect.py, with thanks also to https://github.com/karioja/vedirect/blob/master/vedirect.py

v2.0
This version adds the ability to optionally log data to a CSV file.  Domoticz only keeps max. and min. values after one day, so I would like to use the shorter interval values for graphing.  This file vedirect_data.csv is saved by default in the same directory as the program.

I have left in extensive error logging code, as this is how I learnt how the program worked.  The error log vedirect.log is saved by default in the same directory.

I have found over several years that there were some issues with the original:
  1. The updates in Domoticz get further behind as time goes on.
  2. The program fails and stops from time to time.
  3. It would seem to get 'stuck' ocasionally, parsing the same values until restarted.
  
To resolve these issues, the 'input' processing routine has been changed slightly from the original vedirect.py:
  1. The original code returns the 'H' registers from the BMV on one pass and the other registers on another.  These are called blocks in the VE.Direct-Protocol-3.25 document.  The code now loop twice to update the dictionary with both blocks before parsing the json string to Domoticz.  This seems to have improved accuracy and reliability somewhat. 
  2. In the self.HEX state, the following byte appears mostly in the data to be header1, not header2.
  3. The hex bytes regularly appeared after the Checksum value, so by including these and updating self.bytes_sum, I didn't get as many malformed packets.
  4. Clear the dictionary after a malformed packet, as these would gradually increase the size of the dictionary over time.
 
Variables that should be reviewed or set by the user:

logger_name = "vedirect"  - name used for log file names, messages, etc

debug_level='debug'	      - debug options: DEBUG, INFO, WARNING, ERROR, CRITICAL

                          - debug is verbose, error produces no error logs unless there is an error.
                          
domain="http://rpi3:8080" - enter your Domoticz IP address

                          - script to parse values to Domoticz. Lives in ~/domoticz/scripts/lua_parsers
                          
parse_script = "ap_bmv.lua" - set to empty "" if parsing to Domoticz is not required.

                          - Verify your serial port in Windows using Device Manager or in Linux by looking at /var/log/syslog when inserting cable OR ls -l /dev/serial/by-id/
                          
                          - See file /etc/udev/rules.d/99_usbdevices.rules for vedirectUSB device:
                          
                          - SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6015", SYMLINK+="vedirectUSB"
                          
                          - Use direct name to prevent issues with USB port swapping, otherwise Windows i.e. 'COM5', Linux try '/dev/ttyUSB0'
                          
port = '/dev/serial/by-id/usb-VictronEnergy_BV_VE_Direct_cable_VE3MQXH-if00-port0'

delay_time = 30           - script interval time in seconds

                          - layout for csv data log file.  Set to empty "" to prevent datafile logging.
                          
dataFile_columns = "Time," + "Volts," + "Amps," + "AHr," + "SOC" 

log_dict = OrderedDict()  - Ordered dictionary, as we want to insert the values into the file as listed. Not required in Python 3.7+?

                          - Instantiate dictionary, match dataFile_columns keys and order. Use BMV key names and required multiplier
                          
log_dict.update([("V", 0.001),("I", 0.001),("CE", 0.001),("SOC", 0.1)]) 


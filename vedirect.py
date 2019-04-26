#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Send the Victron BMV (702) values to Domoticz as json
# Adapted from Victron's vedirect.py, thanks also to https://github.com/karioja/vedirect/blob/master/vedirect.py

import os, serial, json, requests, time, logging
from collections import OrderedDict

# Begin user editable variables
logger_name = "vedirect"  #used for log file names, messages, etc
debug_level='debug'	# debug options DEBUG, INFO, WARNING, ERROR, CRITICAL
domain="http://rpi3:8080"
parse_script = "ap_bmv.lua" # script to parse values to Domoticz. Lives in ~/domoticz/scripts/lua_parsers
# Verify port in Windows using Device Manager or in Linux by looking at /var/log/syslog when inserting cable OR ls -l /dev/serial/by-id/  
# See file /etc/udev/rules.d/99_usbdevices.rules for vedirectUSB device:
# SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6015", SYMLINK+="vedirectUSB"
# Use direct name to prevent issues with USB port swapping, otherwise Windows i.e. 'COM5', Linux try '/dev/ttyUSB0'
port = '/dev/serial/by-id/usb-VictronEnergy_BV_VE_Direct_cable_VE3MQXH-if00-port0'
delay_time = 30 #script interval time in seconds
dataFile_columns = "Time," + "Volts," + "Amps," + "AHr," + "SOC" # layout for csv data log file.  Set to empty "" to prevent datafile logging.
log_dict = OrderedDict()  # Ordered dictionary, as we want to insert the values into the file as listed. Fixed in Python 3.7+?
log_dict.update([("V", 0.001),("I", 0.001),("CE", 0.001),("SOC", 0.1)]) # match dataFile_columns keys and order. Use key names and required multiplier
# End user editable variables

log_path = os.path.dirname(os.path.realpath(__file__)) 
dataFile = log_path + "/" + logger_name + "_data.csv"

# Note 'udevices' and 'script=' in baseURL. This doesn't target a particular device IDX as per normal domoticz json, 
# but just serves to fire the domoticz lua parser, which does the updating
# The json data is added to the URL dynamically
baseURL = domain + "/json.htm?type=command&param=udevices&script=" + parse_script + "&data="
# Set up file for error logging
log_level = getattr(logging, debug_level.upper(), 10)
logging.basicConfig(filename=log_path + "/" + logger_name + ".log", level=log_level, format="%(asctime)s:%(message)s") #format="%(asctime)s:%(name)s:%(levelname)s:%(message)s"
logger = logging.getLogger(__name__)
logger.warning('\r\n')  # Blank line between (re)starts
logger.warning('{}'.format(logger_name + ' (re)started'))

class vedirect:
  def __init__(self, serialport, timeout):
    self.serialport = serialport
    self.ser = serial.Serial(serialport, 19200, timeout=timeout)
    self.header1 = '\r' # Flags end of value
    self.header2 = '\n' # Flags start of key
    self.hexmarker = 'b\'\\x' # Hex values to be ignored
    self.delimiter = '\t' # Flags start of value
    self.key = ''
    self.value = ''
    self.bytes_sum = 0
    self.state = self.WAIT_HEADER
    self.dict = {}  # Starts empty, is filled on first run, then only values are replaced.
    
    # Set up headers for CSV data file
    if dataFile_columns != "" and (not os.path.isfile(dataFile)):
      out = dataFile_columns + "\n"
      try:
        fil = open(dataFile, 'w')
        fil.write(out)
      except IOError as e:
        logger.error("I/O error({}): {}".format(e.errno, e.strerror))
      else:
        fil.close()
      
  (HEX, WAIT_HEADER, IN_KEY, IN_VALUE, IN_CHECKSUM) = range(5)
        
  def input(self, byte):
    # Check for hex coded values
    if str(byte)[0:4] == self.hexmarker and self.state != self.IN_CHECKSUM:
      self.state = self.HEX
      self.bytes_sum = 0
    elif str(byte)[0:4] != self.hexmarker:
      byte = byte.decode('UTF-8')
      self.bytes_sum += ord(byte)
    else:
      # is hexmarker and is IN_CHECKSUM
      self.bytes_sum += ord(byte)
      #logger.debug('is hexmarker and IN_CHECKSUM: {}'.format(byte))
    
    if self.state == self.WAIT_HEADER:
      if byte == self.header1:
        self.state = self.WAIT_HEADER
      elif byte == self.header2:
        self.state = self.IN_KEY
      return None
      
    elif self.state == self.IN_KEY:
      if byte == self.delimiter:
        if (self.key == 'Checksum'):
          self.state = self.IN_CHECKSUM
        else:
          self.state = self.IN_VALUE
      else:
        self.key += byte
      return None
        
    elif self.state == self.IN_VALUE:
      if byte == self.header1:
        self.state = self.WAIT_HEADER
        self.dict[self.key] = self.value
        logger.debug('IN_VALUE, key: {}, value: {}'.format(self.key, self.value))
        self.key = ''
        self.value = ''
      else:
        self.value += byte
      return None
        
    elif self.state == self.IN_CHECKSUM:
      self.key = ''
      self.value = ''
      self.state = self.WAIT_HEADER
      logger.debug('Checksum is: {}'.format(self.bytes_sum))
      if (self.bytes_sum % 256 == 0):
        self.bytes_sum = 0
        return self.dict
      else:
        logger.info('Malformed packet: {}'.format(self.dict))
        self.bytes_sum = 0
        self.dict.clear() # Ensure no invalid keys remain in the dictionary
    
    elif self.state == self.HEX:
      if byte == self.header1:
        self.state = self.WAIT_HEADER
        
    else:
      raise AssertionError()

  def read_data_callback(self, callbackFunction):
    # packet_ready exits to calling routine after packet sent
    packet_ready = False 
    logger.debug('Read started')
    loop = 1
    while not packet_ready:
      byte = self.ser.read(1)
      #logger.debug('byte value: {}'.format(byte))
      if byte:
        packet = self.input(byte)
        if packet != None:
          if loop == 1:
            loop += 1
          elif loop == 2:
            packet_ready = True
            logger.debug('Packet ready:')
            #logger.debug(str(packet))
            callbackFunction(packet)
      else:
        break
    
  def flush_buffers(self):
    self.ser.reset_input_buffer()
    self.ser.reset_output_buffer()
    
def send_json(data):
  # convert dict to string and single quotes to double
  strValue = json.dumps(data, ensure_ascii=False)
  strValue = strValue.replace(" ","") # no spaces allowed
  #logger.debug("json key:value string: {}".format(strValue))
  # Check for nulls
  if not strValue == "{}":
    try:
      # send the get request to domoticz
      response = requests.get(baseURL + strValue)
    except:
      logger.error("Connection failed to {}".format(domain))  

    if dataFile_columns != "":
      # Log data to CSV file as backup if required
      out = time.strftime("%Y-%m-%d %H:%M")
      for key,multiplier in log_dict.items():
        #logger.debug('Key, multiplier: {} {}'.format(key, multiplier))
        try:
          val = int(data.get(key,"")) * multiplier
        except:
          out = out + "," + ""
        else:
          out = out + "," + str("%.3f" % round(val,3))      
      out = out + "\n"
      #logger.debug('Data to be logged: {}'.format(out))
      try:
        fil = open(dataFile, 'a')
        fil.write(out)
      except IOError as e:
        logger.error("I/O error({}): {}".format(e.errno, e.strerror))
      else:
        fil.close()
      
def do_every(period,func,*args):
  def g_tick():
    t = time.time()
    count = 0
    while True:
      count += 1
      yield max(t + count*period - time.time(),0)
      
  g = g_tick()
  while True:
    logger.debug('Callback started')
    func(*args)  # Run the function
    #logger.debug('Flush serial buffers')
    #ve.flush_buffers()
    #time.sleep(1)
    logger.debug('{}'.format('Sleeping for ' + str(delay_time) + 's\r\n'))
    time.sleep(next(g))
    
if __name__ == '__main__':
  ve = vedirect(port,15)  # timeout 15?
  do_every(delay_time, ve.read_data_callback, send_json)

#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Send the BMV values to Domoticz as json
# Adapted from Victron's vedirect.py, thanks also to https://github.com/karioja/vedirect/blob/master/vedirect.py

import os, serial, json, requests, time, logging
import timing   # timing.py is a custom routine for timing script run time. Saved in same folder or usr library folder

# Begin user editable variables
logger_name = "vedirect"  #used for log file names, messages, etc
debug_level='INFO'	# debug options DEBUG, INFO, WARNING, ERROR, CRITICAL
domain="http://rpi3:8080"
parse_script = "ap_bmv.lua"
# Verify port in Windows using Device Manager or in Linux by looking at /var/log/syslog when inserting cable OR ls -l /dev/serial/by-id/  
# See file /etc/udev/rules.d/99_usbdevices.rules for vedirectUSB device:
# SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6015", SYMLINK+="vedirectUSB"
port = '/dev/serial/by-id/usb-VictronEnergy_BV_VE_Direct_cable_VE3MQXH-if00-port0' # Windows i.e. 'COM5', Linux try '/dev/ttyUSB0'
delay_time = 30 #script interval time in seconds
# End user editable variables

# Note 'udevices' and 'script=' in baseURL. This doesn't target a particular device IDX as per normal domoticz json, 
# but just serves to fire the domoticz lua parser, which does the updating
# The domoticz lua parser script goes in /domoticz/scripts/lua_parsers
# The json data is added to the URL dynamically
baseURL = domain + "/json.htm?type=command&param=udevices&script=" + parse_script + "&data="
log_path = os.path.dirname(os.path.realpath(__file__))
log_level = getattr(logging, debug_level.upper(), 10)
logging.basicConfig(filename=log_path + "/" + logger_name + ".log", level=log_level, format="%(asctime)s:%(message)s") #format="%(asctime)s:%(name)s:%(levelname)s:%(message)s"
logger = logging.getLogger(__name__)
#logger.warning('\r\n')  # Blank line between (re)starts
logger.warning('\r\n' + '{}'.format(timing.log(logger_name + ' (re)started')))

class vedirect:
  def __init__(self, serialport, timeout):
      self.serialport = serialport
      self.ser = serial.Serial(serialport, 19200, timeout=timeout)
      self.header1 = '\r'
      self.header2 = '\n'
      self.hexmarker = 'b\'\\x'
      self.delimiter = '\t'
      self.key = ''
      self.value = ''
      self.bytes_sum = 0;
      self.state = self.WAIT_HEADER
      self.dict = {}

  (HEX, WAIT_HEADER, IN_KEY, IN_VALUE, IN_CHECKSUM) = range(5)

  def input(self, byte):
    # Check for hex coded values
    if str(byte)[0:4] == self.hexmarker and self.state != self.IN_CHECKSUM:
      self.state = self.HEX
    elif str(byte)[0:4] != self.hexmarker:
      byte = byte.decode('UTF-8')
    self.bytes_sum += ord(byte)
    
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
            self.dict[self.key] = self.value;
            self.key = '';
            self.value = '';
        else:
            self.value += byte
        return None
        
    elif self.state == self.IN_CHECKSUM:
        self.key = ''
        self.value = ''
        self.state = self.WAIT_HEADER
        if (self.bytes_sum % 256 == 0):
          self.bytes_sum = 0
          return self.dict
        else:
          logger.debug('Malformed packet')
          self.bytes_sum = 0
    
    elif self.state == self.HEX:
        self.bytes_sum = 0
        if byte == self.header2:
          self.state = self.WAIT_HEADER
    else:
        raise AssertionError()

  def read_data(self):
      while True:
          byte = self.ser.read(1)
          packet = self.input(byte)

  def read_data_single(self):
      while True:
          byte = self.ser.read(1)
          packet = self.input(byte)
          if (packet != None):
              return packet

  def read_data_callback(self, callbackFunction):
    # packet_ready flag allows function to return to calling routine after packet sent
    packet_ready = False 
    logger.debug('Read start: {}'.format(time.time()))
    while not packet_ready:
      byte = self.ser.read(1)
      if byte:
        packet = self.input(byte)
        if (packet != None):
          logger.debug(str(packet))
          packet_ready = True
          logger.debug('Packet ready: {}'.format(time.time()))
          callbackFunction(packet)
      else:
        break

  def flush_buffers(self):
    self.ser.reset_input_buffer()
    self.ser.reset_output_buffer()
    
def print_data_callback(data):
    print(data)
    
def send_json(data):
  # convert dict to string and single quotes to double
  strValue = json.dumps(data, ensure_ascii=False)
  strValue = strValue.replace(" ","") # no spaces allowed
  logger.info("json key:value string: {}".format(strValue))
  # Check for nulls
  if not strValue == "{}":
    try:
      # send the get request to domoticz
      logger.debug(baseURL + strValue)
      response = requests.get(baseURL + strValue)
    except:
      logger.error("Connection failed to {}".format(domain))  
    else:
      logger.debug(response)
    
def do_every(period,func,*args):
  def g_tick():
    t = time.time()
    count = 0
    while True:
      count += 1
      yield max(t + count*period - time.time(),0)
      
  g = g_tick()
  while True:
    logger.debug('Func time: {}'.format(time.time()))
    func(*args)  # Run the function before first timer run
    logger.debug('{}'.format(timing.log('Sleeping for ' + str(delay_time) + 's')))
    time.sleep(next(g))
    logger.debug('Flush time: {}'.format(time.time()))
    ve.flush_buffers()
    time.sleep(1)
    
if __name__ == '__main__':
  ve = vedirect(port,15)  # timeout 15?
  do_every(delay_time, ve.read_data_callback, send_json)

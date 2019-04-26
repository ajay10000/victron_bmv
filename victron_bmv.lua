--lua script to parse json data to domoticz devices via their IDs
--belongs in domoticz/scripts/lua_parsers
--called by url generated in python script vedirect_json.py 
--example: http://domoticz_domain_orIP#:port#/json.htm?type=command&param=udevices&script=bmv_json.lua&data={"H2":0,"H3":0,"Alarm":"OFF","H7":46666,"V":54645,"FW":307,"H10":14,"H4":0,"H8":60004,"H11":0,"H12":0,"SOC":1000,"H1":-170364,"AR":0,"BMV":700,"CE":0,"P":29,"Relay":"OFF","I":530,"PID":"0x203","TTG":-1,"H9":0,"H17":26572,"H5":0,"H18":41698,"H6":-7695869}

function parseJsonToDomoticz()
  -- 2D array with format name={Domoticz id,BMV-702 key,BMV multiplier}
  arr = {
  voltage = {60,'.V',0.001};
  current = {61,'.I',0.001};
  power = {62,'.P',1};
  soc = {63,'.SOC',0.1};
  kwhr_in = {64,'.H18',0.01};
  kwhr_out = {65,'.H17',0.01};
  ahr = {66,'.CE',0.001}}
  
  -- Retrieve the json string
  strJson = uri['data']
  --print(strJson) --debug

  for k, v in pairs(arr) do
    val = domoticz_applyJsonPath(strJson,v[2])
    if not isBlank(val) then
      --print(k..": "..val) --debug
      -- command format: domoticz_updateDevice(Domoticz ID,'',BMV value * BMV multiplier)
      domoticz_updateDevice(v[1],'',val * v[3])
    end
  end
  
end

function errorhandler(err)
   print("ERROR:", err)
end

function isBlank(x)
  --tests for "blank" string - either empty, nil, or just spaces/tabs/newlines.
  if x == nil or x == '' then
    return True
  else
    return not not tostring(x):find("^%s*$")
  end
end

status = xpcall(parseJsonToDomoticz, errorhandler)
--print(status) --debug

--[[
Label and Units from BMV-702 
Label	Units	Description
V	mV	Main (battery) voltage
VS	mV	Auxiliary (starter) voltage
VM	mV	Mid-point voltage of the battery bank
DM	‰	Mid-point deviation of the battery bank
I	mA	Battery current
T	°C 5	Battery temperature
P	W	Instantaneous power
CE	mAh 6	Consumed Amp Hours
SOC	‰ 6	State-of-charge
TTG	Minutes 67	Time-to-go
Alarm		Alarm condition active
Relay		Relay state
AR		Alarm reason
H1	mAh	Depth of the deepest discharge
H2	mAh	Depth of the last discharge
H3	mAh	Depth of the average discharge
H4		Number of charge cycles
H5		Number of full discharges
H6	mAh	Cumulative Amp Hours drawn
H7	mV	Minimum main (battery) voltage
H8	mV	Maximum main (battery) voltage
H9	Seconds	Number of seconds since last full charge
H10		Number of automatic synchronizations
H11		Number of low main voltage alarms
H12		Number of high main voltage alarms
H15	mV	Minimum auxiliary (battery) voltage
H16	mV	Maximum auxiliary (battery) voltage
H17	0.01 kWh	Amount of discharged energy
H18	0.01 kWh	Amount of charged energy
BMV		Model description (deprecated)
FW		Firmware version
PID		Product ID
 ]]

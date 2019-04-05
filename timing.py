#!/usr/bin/python3
import atexit
from time import time, strftime, localtime
from datetime import timedelta

divider_line = "="*35

def secondsToStr(elapsed=None):
  if elapsed is None:
    return strftime("%Y-%m-%d %H:%M:%S", localtime())
  else:
    return str(timedelta(seconds=elapsed))

def log(str, elapsed=None):
  print(divider_line)
  t = (secondsToStr() + ' - ' + str)
  print(t)
  if elapsed:
    print("Elapsed time:", elapsed)
  print(divider_line)
  print()
  if elapsed is None:
    return t
  else:
    return elapsed
    
def endlog():
  end = time()
  elapsed = end-start
  log("End Program", secondsToStr(elapsed))

start = time()
atexit.register(endlog)
log("Started")
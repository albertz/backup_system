#!/usr/bin/python

import config

import time
import os
from hashlib import sha1
import json
from datetime import datetime

def convert_unix_time(unixtime):
	return datetime.utcfromtimestamp(unixtime).isoformat(" ")

class SimpleStruct:
	def __init__(self, **kwargs):
		for k,v in kwargs.itervalues():
			setattr(self, k, v)
			
	def __repr__(self):
		stdobjattribs = set(dir(object()))
		stdobjattribs.add("__module__")
		attribs = []
		for a in dir(self):
			if a not in stdobjattribs: attribs += [a]
		return self.__class__.__name__ + "(" + ", ".join(map(
			lambda a: a + "=" + repr(getattr(self, a)), attribs)) + ")"

def get_db_obj(ref):
	pass

def should_we_recheck_dir(d, dbobj):
	pass

def convert_stat_info(s):
	o = SimpleStruct()
	#o.mode = TODO
	o.size = s.st_size
	for a in ["atime", "mtime", "ctime"]:
		setattr(o, a, convert_unix_time(getattr(s, "st_" + a)))
	return o

def checkdir(d):
	if os.path.samefile(d, config.dbdir): return
	obj = get_db_obj(sha1(d))
	print d, convert_stat_info(os.stat(d))
	
def mainloop():
	while True:
		time.sleep(1)
		for d in config.dirs:
			checkdir(d)
		quit()
		
if __name__ == '__main__':
	mainloop()

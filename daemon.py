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
	def __init__(self, *args, **kwargs):
		if len(kwargs) == 0 and len(args) == 1 and type(args[0]) is dict:
			kwargs = args[0]
		for k,v in kwargs.iteritems():
			setattr(self, k, v)
	
	def attribs(self):
		stdobjattribs = set(dir(object()))
		stdobjattribs.add("__module__")
		attribs = []
		for a in dir(self):
			if a in stdobjattribs: continue
			if callable(getattr(self, a)): continue
			attribs += [a]		
		return attribs
	
	def __repr__(self):
		return self.__class__.__name__ + "(" + ", ".join(map(
			lambda a: a + "=" + repr(getattr(self, a)), self.attribs())) + ")"

	def as_dict(self):
		return dict(map(lambda a: (a, getattr(self, a)), self.attribs()))

def json_encode(obj):
	if isinstance(obj, SimpleStruct): return obj.as_dict()
	raise TypeError, repr(obj) + " cannot be serialized"

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

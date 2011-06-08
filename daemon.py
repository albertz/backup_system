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

def _json_encode_obj(obj):
	if isinstance(obj, SimpleStruct): return obj.as_dict()
	raise TypeError, repr(obj) + " cannot be serialized"

def json_encode(obj):
	return json.dumps(obj, default=_json_encode_obj)

def json_decode(s):
	return json.loads(s, object_hook=SimpleStruct)

def get_db_obj(ref):
	pass

def should_we_recheck_dir(d, dbobj):
	pass

def convert_statmode_to_list(m):
	bitlist = []
	import stat
	for b in sorted(dir(stat)):
		if not b.startswith("S_I"): continue
		if b in ["S_IREAD", "S_IWRITE", "S_IEXEC"]: continue # synoyms
		if callable(getattr(stat, b)): continue
		i = getattr(stat, b)
		if m & i == 0: continue
		bitlist += [b[3:]]
	return bitlist

def convert_stat_info__into(s, o):
	o.mode = convert_statmode_to_list(s.st_mode)
	o.size = s.st_size
	for a in ["atime", "mtime", "ctime", "birthtime"]:
		if hasattr(s, "st_" + a):
			setattr(o, a, convert_unix_time(getattr(s, "st_" + a)))
	return o

def convert_stat_info(s):
	return convert_stat_info__into(s, SimpleStruct())

def checkdir(d):
	if os.path.samefile(d, config.dbdir): return
	obj = get_db_obj(sha1(d))
	print d, json_encode(convert_stat_info(os.stat(d)))
	
def mainloop():
	while True:
		time.sleep(1)
		for d in config.dirs:
			checkdir(d)
		quit()
		
if __name__ == '__main__':
	mainloop()

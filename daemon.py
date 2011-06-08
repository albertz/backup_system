#!/usr/bin/python

import config

import time
import os
from hashlib import sha1
import json
from datetime import datetime

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
	
	def get(self, attr, fallback=None): return getattr(self, attr, fallback)

def _json_encode_obj(obj):
	if isinstance(obj, SimpleStruct): return obj.as_dict()
	raise TypeError, repr(obj) + " cannot be serialized"

def json_encode(obj):
	return json.dumps(obj, ensure_ascii=False, indent=4, default=_json_encode_obj, sort_keys=True)

def json_decode(s):
	return json.loads(s, object_hook=SimpleStruct)

def get_db_obj(ref):
	pass

def should_we_recheck_dir(d, dbobj):
	pass

def convert_statmode_to_list(m):
	bitlist = []
	import stat

	hastype = False
	for t in ["LNK", "DIR", "REG", "FIFO", "SOCK", "CHR", "BLK"]:
		if getattr(stat, "S_IS" + t)(m):
			bitlist += ["F" + t]
			hastype = True
			break
		
	for b in sorted(dir(stat)):
		if not b.startswith("S_I"): continue
		if b == "S_IFMT": continue # collection
		if hastype and b.startswith("S_IF"): continue # we already have the type
		if b in ["S_IREAD", "S_IWRITE", "S_IEXEC"]: continue # synoyms
		if callable(getattr(stat, b)): continue
		i = getattr(stat, b)
		if m & i != i: continue
		bitlist += [b[3:]]

	return bitlist

def convert_unix_time(unixtime):
	return datetime.utcfromtimestamp(unixtime).isoformat(" ")

def get_stat_info(fpath):
	s = os.lstat(fpath)
	o = SimpleStruct()
	o.mode = convert_statmode_to_list(s.st_mode)
	o.size = s.st_size
	for a in ["atime", "mtime", "ctime", "birthtime"]:
		if hasattr(s, "st_" + a):
			setattr(o, a, convert_unix_time(getattr(s, "st_" + a)))
	return o

def _file_type_from_statmodelist(s):
	for b in s:
		if b.startswith("F"): return b[1:].lower()

def get_file_info(fpath):
	o = SimpleStruct()
	o.stat = get_stat_info(fpath)
	o.time = SimpleStruct()
	o.time.creation = o.stat.get("birthtime") or o.stat.get("ctime")
	o.time.lastmodification = o.stat.mtime
	o.type = _file_type_from_statmodelist(o.stat.mode)
	if o.type == "lnk": o.symlink = os.readlink(fpath)
	return o

def checkdir(d):
	if os.path.samestat(os.lstat(d), os.stat(config.dbdir)): return
	obj = get_db_obj(sha1(d))
	print d, json_encode(get_file_info(d))
	
def mainloop():
	while True:
		time.sleep(1)
		for d in config.dirs:
			checkdir(d)
		quit()
		
if __name__ == '__main__':
	mainloop()

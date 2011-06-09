#!/usr/bin/python

import config

import codecs
import time
import os
import hashlib
import json
from datetime import datetime

def sha1(s):
	if type(s) is unicode: s = s.encode("utf-8")
	return hashlib.sha1(s).hexdigest()

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
	
	def as_dict(self):
		return dict(map(lambda a: (a, getattr(self, a)), self.attribs()))

	def __repr__(self):
		return self.__class__.__name__ + "(" + ", ".join(map(
			lambda a: a + "=" + repr(getattr(self, a)), self.attribs())) + ")"

	def __eq__(self, other): return self.as_dict() == other.as_dict()
	
	def get(self, attr, fallback=None): return getattr(self, attr, fallback)

	def save_to_db(self):
		dbfilepath = config.dbdir + "/objects/" + self.sha1[:2] + "/" + self.sha1[2:]
		os.makedirs(os.path.dirname(dbfilepath))
		open(dbfilepath, "w").write(json_encode(self).encode("utf-8"))
	
	@staticmethod
	def load_from_db(sha1ref):
		dbfilepath = config.dbdir + "/objects/" + sha1ref[:2] + "/" + sha1ref[2:]
		return json_decode(open(dbfilepath).read())

	
class Time(datetime):
	@classmethod
	def from_unix(cls, unixtime):
		return cls(*datetime.utcfromtimestamp(unixtime).utctimetuple()[0:6])
	@classmethod
	def from_str(cls, s):
		return cls(*datetime.strptime("%Y-%m-%d %H:%M:%S", s).utctimetuple()[0:6])
	def str(self): return self.isoformat(" ")
	
def _json_encode_obj(obj):
	if isinstance(obj, SimpleStruct): return obj.as_dict()
	if isinstance(obj, Time): return str(obj)
	raise TypeError, repr(obj) + " cannot be serialized"

def json_encode(obj):
	return json.dumps(obj, ensure_ascii=False, indent=4, default=_json_encode_obj, sort_keys=True)

def _json_decode_obj(obj):
	if isinstance(obj, (str,unicode)):
		try: return Time.from_str(obj)
		except: pass
	return obj

def _json_decode_dict(d):
	d = dict(map(lambda (k,v): (k,_json_decode_obj(v)), d.iteritems()))
	return SimpleStruct(d)

def json_decode(s):
	return json.loads(s, object_hook=_json_decode_dict)


entries_to_check = []

def get_db_obj(sha1ref):
	return SimpleStruct.load_from_db(sha1ref)

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

def get_stat_info(fpath):
	s = os.lstat(fpath)
	o = SimpleStruct()
	o.mode = convert_statmode_to_list(s.st_mode)
	o.size = s.st_size
	for a in ["atime", "mtime", "ctime", "birthtime"]:
		if hasattr(s, "st_" + a):
			setattr(o, a, Time.from_unix(getattr(s, "st_" + a)))
	return o

def _file_type_from_statmodelist(s):
	for b in s:
		if b.startswith("F"): return b[1:].lower()

def get_file_mimetype(fpath):
	import subprocess
	out = subprocess.Popen(['file', '-b', '--mime-type', fpath], stdout=subprocess.PIPE).communicate()[0]
	out = out.strip()
	return out
	
def get_file_info(fpath):
	assert type(fpath) is unicode
	o = SimpleStruct()
	o.path = fpath
	o.sha1 = sha1(fpath)
	o.stat = get_stat_info(fpath)
	o.time = SimpleStruct()
	o.time.creation = o.stat.get("birthtime") or o.stat.get("ctime")
	o.time.lastmodification = o.stat.mtime
	o.type = "file:" + _file_type_from_statmodelist(o.stat.mode)
	if o.type == "file:reg":
		o.type = "file"
		o.filetype = get_file_mimetype(fpath)
	elif o.type == "file:dir": o.type = "dir"
	elif o.type == "file:lnk": o.symlink = os.readlink(fpath)
	return o

def need_to_check(dbobj, fileinfo):
	if dbobj is None: return True
	assert isinstance(dbobj.time.lastmodification, Time)
	assert isinstance(fileinfo.time.lastmodification, Time)
	return fileinfo.time.lastmodification > dbobj.time.lastmodification

def _check_entry__file(dbobj):
	assert dbobj.type == "file"
	# TODO
	
def _check_entry__dir(dbobj):
	assert dbobj.type == "dir"
	for e in os.listdir(dbobj.path):
		checkfilepath(dbobj.path + "/" + e)

def _check_entry__file_lnk(dbobj):
	# do nothing
	pass

def add_entry_to_check(dbobj):
	global entries_to_check
	entries_to_check += [dbobj]

def check_entry(dbobj):
	print json_encode(dbobj)
	checkfuncname = "_check_entry__" + dbobj.type
	checkfuncname = checkfuncname.replace(":","_")
	f = globals()[checkfuncname]
	f(dbobj)

def checkfilepath(fpath):
	assert type(fpath) is unicode

	if os.path.samestat(os.lstat(fpath), os.stat(config.dbdir)): return

	fileinfo = get_file_info(fpath)
	obj = get_db_obj(fileinfo.sha1)
	if not need_to_check(obj, fileinfo): return
	
	add_entry_to_check(fileinfo)
	
def mainloop():
	global entries_to_check
	import random
	while True:
		if entries_to_check:
			i = random.randint(0, len(entries_to_check) - 1)
			dbobj = entries_to_check[i]
			entries_to_check = entries_to_check[:i] + entries_to_check[i+1:]
			check_entry(dbobj)
		else: # no entries
			time.sleep(1)
			for d in config.dirs:
				if type(d) is str: d = d.decode("utf-8")
				checkfilepath(d)
		
if __name__ == '__main__':
	mainloop()

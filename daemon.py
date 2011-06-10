#!/usr/bin/python

import config

import time, os, sys
import hashlib
import json
from datetime import datetime

import better_exchook
better_exchook.install()

def sha1(s):
	if type(s) is unicode: s = s.encode("utf-8")
	return hashlib.sha1(s).hexdigest()

def db_obj_fpath(sha1ref):
	# Splitting the 160 bit into 8:8:144 bit.
	# For a complete uniform distribution of 10**6 entries, it means that there are
	# 255 sub-directories on the first level,
	# 255 sub-directories on the second level and
	# 15.4 files at the last level.
	# Git just splits 8:152 which means a somewhat worse performance at 10**7 entries and up.
	return config.dbdir + "/objects/" + sha1ref[:2] + "/" + sha1ref[2:4] + "/" + sha1ref[4:]

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

	def dump(self, out=sys.stdout):
		out.write(json_encode(self).encode("utf-8"))
		out.write("\n")
		out.flush()
		
	def save_to_db(self):
		dbfilepath = db_obj_fpath(self.sha1)
		try: os.makedirs(os.path.dirname(dbfilepath))
		except: pass # eg, dir exists or so. doesn't matter, the following will fail if it is more serious
		f = open(dbfilepath, "w")
		self.dump(out=f)
		f.close()
	
	@staticmethod
	def load_from_db(sha1ref):
		dbfilepath = db_obj_fpath(sha1ref)
		return json_decode(open(dbfilepath).read())

	
class Time(datetime):
	@classmethod
	def from_unix(cls, unixtime):
		return cls(*datetime.utcfromtimestamp(unixtime).utctimetuple()[0:6])
	@classmethod
	def from_str(cls, s):
		return cls(*datetime.strptime(s, "%Y-%m-%d %H:%M:%S").utctimetuple()[0:6])
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
	try:
		return SimpleStruct.load_from_db(sha1ref)
	except IOError, e:
		if e.errno == 2: # no such file or dir
			return None
		raise e # reraise, we didn't expected that

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

def _check_entry__file(dbobj):
	assert dbobj.type == "file"
	# TODO
	
def _check_entry__dir(dbobj):
	assert dbobj.type == "dir"
	clean_entries_to_check__with_parentref(dbobj.sha1)
	files = list(os.listdir(dbobj.path))
	dbobj.childs_to_check_count = len(files)
	if len(files) == 0: dbobj.info_completed = True
	dbobj.save_to_db()
	for e in files:
		checkfilepath(dbobj.path + "/" + e, dbobj)

def _check_entry___nop(dbobj):
	# do nothing
	dbobj.info_completed = True
	dbobj.childs_to_check_count = 0
	dbobj.save_to_db()

_check_entry__file_lnk = _check_entry___nop
_check_entry__file_fifo = _check_entry___nop
_check_entry__file_sock = _check_entry___nop
_check_entry__file_chr = _check_entry___nop
_check_entry__file_blk = _check_entry___nop

def db_obj__parent_chain(dbobj):
	if dbobj.parent is None: return []
	parent = get_db_obj(dbobj.parent)
	return db_obj__parent_chain(parent) + [parent]

def db_obj__ref(dbobj): return dbobj.sha1

def db_obj__parentref_chain(dbobj): return map(db_obj__ref, db_obj__parent_chain(dbobj))

def clean_entries_to_check__with_parentref(parentref):
	global entries_to_check
	entries_to_check = filter(lambda obj: parentref not in db_obj__parentref_chain(obj), entries_to_check)

def add_entry_to_check(dbobj):
	global entries_to_check
	entries_to_check += [dbobj]

def _check_entry__handle_completion(dbobj):
	if dbobj.parent is not None:
		parent = get_db_obj(dbobj.parent)
		assert parent is not None
		parent.childs_to_check_count -= 1
		assert parent.childs_to_check_count >= 0
		if parent.childs_to_check_count == 0:
			_check_entry__handle_completion(parent)

def check_entry(dbobj):
	print json_encode(dbobj)
	was_complete = dbobj.info_completed
	
	checkfuncname = "_check_entry__" + dbobj.type
	checkfuncname = checkfuncname.replace(":","_")
	f = globals()[checkfuncname]
	f(dbobj)

	if not was_complete and dbobj.info_completed:
		_check_entry__handle_completion(dbobj)

def need_to_check(dbobj, fileinfo):
	if dbobj is None: return True
	assert isinstance(dbobj.time.lastmodification, Time)
	assert isinstance(fileinfo.time.lastmodification, Time)
	if not fileinfo.info_completed: return True
	if dbobj.childs_to_check_count > 0: return True
	if fileinfo.time.lastmodification > dbobj.time.lastmodification: return True
	if fileinfo.type != dbobj.type: return True
	# we cannot assert fileinfo==dbobj. atime and other stuff might still have changed
	return False

def checkfilepath(fpath, parentobj):
	assert type(fpath) is unicode

	if os.path.samestat(os.lstat(fpath), os.stat(config.dbdir)): return

	fileinfo = get_file_info(fpath)
	fileinfo.parent = parentobj.sha1 if parentobj is not None else None		
	obj = get_db_obj(fileinfo.sha1)
	if not need_to_check(obj, fileinfo):
		print "skipped:", fpath
		return
	
	fileinfo.info_completed = False
	fileinfo.childs_to_check_count = 1 # there is at least one child: the content of this filepath entry
	fileinfo.save_to_db()
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
				checkfilepath(d, None)
		
if __name__ == '__main__':
	mainloop()

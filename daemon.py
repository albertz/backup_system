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

def sha1file(f, close_at_end=True):
	if type(f) in [str,unicode]: f = open(f)
	hash = hashlib.sha1()
	while True:
		buf = f.read(0x1000000) # read 16MB chunks
		if not buf:
			break
		hash.update(buf)
	if close_at_end: f.close()
	return hash.hexdigest()

def db_obj_fpath(sha1ref):
	# Splitting the 160 bit into 8:8:144 bit.
	# For a complete uniform distribution of 10**6 entries, it means that there are
	# 255 sub-directories on the first level,
	# 255 sub-directories on the second level and
	# 15.4 files at the last level.
	# Git just splits 8:152 which means a somewhat worse performance at 10**7 entries and up.
	return config.dbdir + "/objects/" + sha1ref[:2] + "/" + sha1ref[2:4] + "/" + sha1ref[4:]

class SimpleStruct(dict):
	# Note: We cannot do `self.__dict__ = self` because of http://bugs.python.org/issue1469629.
	# But anyway, redefining __getattr__/__setattr__ has also the advantage
	# that `self.__dict__` and `self` are not the same which allows a cleaner separation
	# of implementation stuff and the real data.

	def __init__(self, *args, **kwargs):
		if len(kwargs) == 0 and len(args) == 1 and type(args[0]) is dict:
			kwargs = args[0]
		for k,v in kwargs.iteritems():
			self[k] = v
	
	attribs = dict.keys
	as_dict = lambda self: self

	def __repr__(self):
		return self.__class__.__name__ + "(" + dict.__repr__(self) + ")"
	
	def __getattr__(self, key):
		assert key != "intern" # We shouldn't get here. `_intern` should be in `self.__dict__`.
		try: return self[key]
		except KeyError: raise AttributeError
	def __setattr__(self, key, value):
		if key == "sha1" and "_intern" in self.__dict__:
			# Once we use intern data, we use this as a DB object.
			# This means we should relate to some DB-file already.
			# Don't allow this reassignment.
			assert "sha1" in self # For debugging purpose. This should be True.
			assert False # Fail here because of the reason stated above.
		assert key != "_intern" # We keep this for internal purpose.
		self[key] = value

	def get(self, attr, fallback=None): return getattr(self, attr, fallback)

	def set_initial(self, key, value):
		if type(value) is dict: value = SimpleStruct(value)
		if key in self:
			assert type(self[key]) is type(value)
		else:
			self[key] = value

	@staticmethod
	def normalize_value(value):
		if type(value) is str: value = value.decode("utf-8")
		if type(value) is dict: value = SimpleStruct(value)
		return value
	
	def merge(self, other):
		for key, value in other.iteritems():
			value = self.normalize_value(value)
			selfvalue = self.get(key)
			if selfvalue is None:
				self[key] = value
			else:
				selfvalue = self.normalize_value(selfvalue)
				assert type(value) is type(selfvalue)
				if isinstance(selfvalue, SimpleStruct):
					selfvalue.merge(value)
				else:
					self[key] = value

	def dump(self, out=sys.stdout):
		out.write(json_encode(self).encode("utf-8"))
		out.write("\n")
		out.flush()
	
	def _ensure_intern_data(self):
		if "_intern" not in self.__dict__:
			self.__dict__["_intern"] = SimpleStruct()
		
	def _ensure_open_file(self, load_also):
		loaded_something = False
		self._ensure_intern_data()
		if not self._has_opened_file():
			if not hasattr(self._intern, "filepath"):
				assert hasattr(self, "sha1")
				assert self.sha1 is not None
				self._intern.filepath = db_obj_fpath(self.sha1)
			try: os.makedirs(os.path.dirname(self._intern.filepath))
			except: pass # eg, dir exists or so. doesn't matter, the following will fail if it is more serious
			self._intern.fd = os.open(self._intern.filepath, os.O_CREAT | os.O_RDWR | os.O_EXLOCK, 0644)
			assert self._intern.fd >= 0
			l = os.lseek(self._intern.fd, 0, os.SEEK_END)
			if load_also and l > 0:
				self._load_file()
				loaded_something = True
			else:
				assert l == 0 # We always should load the file if there is some content.
		return loaded_something
	
	def _has_opened_file(self):
		return "_intern" in self.__dict__ and hasattr(self._intern, "fd")

	def _assert_open_file(self):
		assert "_intern" in self.__dict__
		assert self._intern.fd > 0
	
	def _load_file(self):
		self._assert_open_file()
		os.lseek(self._intern.fd, 0, os.SEEK_SET)
		s = ""
		while True:
			buf = os.read(self._intern.fd, 0x1000000) # read 16 MB chunks
			if len(buf) == 0: break
			s += buf
		decodedobj = json_decode(s)
		assert type(decodedobj) is type(self)
		self.merge(decodedobj)
		return decodedobj
	
	def _close_file(self):
		self._assert_open_file()
		os.close(self._intern.fd)
		del self._intern.fd

	def __del__(self):
		if self._has_opened_file():
			self._close_file()

	def save_to_db(self):
		self._ensure_open_file(load_also = False) # Either the file should already be loaded or we should fail here.
		os.lseek(self._intern.fd, 0, os.SEEK_SET)
		os.ftruncate(self._intern.fd, 0)
		s = json_encode(self).encode("utf-8") + "\n"
		while len(s) > 0:
			n = os.write(self._intern.fd, s)
			s = s[n:]
		os.fsync(self._intern.fd)
				
	@staticmethod
	def load_from_db(sha1ref):
		obj = SimpleStruct(sha1 = sha1ref)
		obj._ensure_open_file(load_also = True)
		return obj

	
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

def create_file_content_obj(obj, filetype):
	obj.type = "file content"
	obj.filetype = filetype
	obj.set_initial("paths", {})
	return obj

def _check_entry__file(dbobj):
	assert dbobj.type == "file"
	dbobj.content = sha1file(dbobj.path) # TODO: error handling here. e.g. no access
	dbobj.save_to_db()
	contentobj = get_db_obj(dbobj.content)
	create_file_content_obj(contentobj, dbobj.filetype)
	if dbobj.path not in contentobj.paths: contentobj.paths[dbobj.path] = dbobj.sha1
	contentobj.save_to_db()
	if dbobj.parent is not None:
		parentobj = get_db_obj(dbobj.parent)
		assert parentobj is not None
		parentobj.content[os.path.basename(dbobj.path)].content = dbobj.content
		parentobj.save_to_db()
	_check_entry_finish_entry(dbobj)
	
def _check_entry__dir(dbobj):
	assert dbobj.type == "dir"
	clean_entries_to_check__with_parentref(dbobj.sha1)
	files = list(os.listdir(dbobj.path))
	dbobj.childs_to_check_count = len(files)
	if len(files) == 0: dbobj.info_completed = True
	dbobj.save_to_db()
	dbobj.content = {}
	for e in files:
		ref = checkfilepath(dbobj.path + "/" + e, dbobj)
		dbobj.content[e] = SimpleStruct(path=ref)
	dbobj.save_to_db()	

def _check_entry_finish_entry(dbobj):
	dbobj.info_completed = True
	dbobj.childs_to_check_count = 0
	dbobj.save_to_db()

# do nothing
_check_entry__file_lnk = _check_entry_finish_entry
_check_entry__file_fifo = _check_entry_finish_entry
_check_entry__file_sock = _check_entry_finish_entry
_check_entry__file_chr = _check_entry_finish_entry
_check_entry__file_blk = _check_entry_finish_entry

def db_obj__parent_chain(dbobj):
	if dbobj.parent is None: return []
	parent = get_db_obj(dbobj.parent)
	return db_obj__parent_chain(parent) + [parent]

def db_obj__ref(dbobj): return dbobj.sha1

def db_obj__parentref_chain(dbobj): return map(db_obj__ref, db_obj__parent_chain(dbobj))

def clean_entries_to_check__with_parentref(parentref):
	global entries_to_check
	entries_to_check = filter(lambda ref: parentref not in db_obj__parentref_chain(get_db_obj(ref)), entries_to_check)

def add_entry_to_check(dbobj):
	global entries_to_check
	entries_to_check += [dbobj]

def _check_entry_handle_completion(dbobj):
	if dbobj.parent is not None:
		parent = get_db_obj(dbobj.parent)
		assert parent is not None
		parent.childs_to_check_count -= 1
		assert parent.childs_to_check_count >= 0
		if parent.childs_to_check_count == 0:
			_check_entry_handle_completion(parent)

def check_entry(dbobj):
	print json_encode(dbobj)
	was_complete = dbobj.info_completed
	
	checkfuncname = "_check_entry__" + dbobj.type
	checkfuncname = checkfuncname.replace(":","_")
	f = globals()[checkfuncname]
	f(dbobj)

	if not was_complete and dbobj.info_completed:
		_check_entry_handle_completion(dbobj)

def need_to_check(dbobj, fileinfo):
	if dbobj is None: return True
	if not hasattr(dbobj, "time"): return True
	assert isinstance(dbobj.time.lastmodification, Time)
	assert isinstance(fileinfo.time.lastmodification, Time)
	if not dbobj.info_completed: return True
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
		return fileinfo.sha1
	
	obj.update(fileinfo)
	fileinfo = obj
	fileinfo.info_completed = False
	fileinfo.childs_to_check_count = 1 # there is at least one child: the content of this filepath entry
	fileinfo.save_to_db()
	add_entry_to_check(fileinfo.sha1)
	return fileinfo.sha1

def mainloop():
	global entries_to_check
	import random
	while True:
		if entries_to_check:
			i = random.randint(0, len(entries_to_check) - 1)
			dbobj_ref = entries_to_check[i]
			dbobj = get_db_obj(dbobj_ref)
			entries_to_check = entries_to_check[:i] + entries_to_check[i+1:]
			check_entry(dbobj)
		else: # no entries
			time.sleep(1)
			for d in config.dirs:
				if type(d) is str: d = d.decode("utf-8")
				checkfilepath(d, None)
		
if __name__ == '__main__':
	mainloop()

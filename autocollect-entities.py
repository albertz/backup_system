#!/usr/bin/python

import os, os.path, fnmatch

blacklistdirs = \
	[
	 os.path.expanduser("~/.*"),
	 os.path.expanduser("~/Spiele"),
	 os.path.expanduser("~/Applications"),
	 os.path.expanduser("~/bin"),
	 os.path.expanduser("~/build"),
	 os.path.expanduser("~/Desktop"),
	 os.path.expanduser("~/Downloads"),
	 os.path.expanduser("~/gtk"),
	 os.path.expanduser("~/Source"),
	 os.path.expanduser("~/Wine Files"),
	 os.path.expanduser("~/Public"),
	 ]
	
def find_in_dir(d):
	for _d in blacklistdirs:
		if fnmatch.fnmatch(d, _d): return
	yield { "name":os.path.basename(d), "dir":d }

def find_all():
	userdir = os.path.expanduser("~")
	for d in os.listdir(userdir):
		d = userdir + "/" + d
		if not os.path.isdir(d): continue
		for e in find_in_dir(d):
			yield e

if __name__ == "__main__":
	for e in find_all(): print e

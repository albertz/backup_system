#!/usr/bin/python

import os, os.path, fnmatch

blacklistdirs = \
	[
	 "~/.*",
	 "~/Spiele",
	 "~/Applications",
	 "~/bin",
	 "~/build",
	 "~/Desktop",
	 "~/Downloads",
	 "~/gtk",
	 "~/Source",
	 "~/Wine Files",
	 "~/Public",
	 ]

categorydirs = \
	[
	 "~/Programmierung",
	 "~/Documents",
	 "~/Music",
	 "~/Movies",
	 "~/Library",
	 "~/Library/Application Support",
	 ]

def find_in_dir(d):
	for _d in blacklistdirs:
		if fnmatch.fnmatch(d, os.path.expanduser(_d)): return
	for _d in categorydirs:
		if fnmatch.fnmatch(d, os.path.expanduser(_d)):
			for subdir in os.listdir(d):
				subdir = d + "/" + subdir
				if not os.path.isdir(subdir): continue
				for e in find_in_dir(subdir): yield e
			return

	yield { "name":os.path.basename(d), "dir":d }


def find_all():
	userdir = os.path.expanduser("~")
	for d in os.listdir(userdir):
		d = userdir + "/" + d
		if not os.path.isdir(d): continue
		for e in find_in_dir(d): yield e

if __name__ == "__main__":
	for e in find_all(): print e

#!/usr/bin/python

import os.path

dirs = ["~"]
dbdir = "~/db"

for l in [dirs]:
	for i in xrange(len(l)):
		l[i] = os.path.expanduser(l[i])
dbdir = os.path.expanduser(dbdir)

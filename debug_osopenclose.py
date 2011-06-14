
import os

orig_open = os.open
orig_close = os.close

debug_open_files = {}

def debug_open_file(filename, flags, mode=0644):
	ret = orig_open(filename, flags, mode)
	if ret >= 0:
		import traceback
		debug_open_files[ret] = ret, filename, flags, mode, traceback.extract_stack()
	return ret

def debug_close_file(filedes):
	del debug_open_files[filedes]
	return orig_close(filedes)

import os
os.open = debug_open_file
os.close = debug_close_file


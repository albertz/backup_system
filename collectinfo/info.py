# types of information

def makeSymbolName(name):
	ret = ""
	state = 0
	for c in name:
		if state == 0:
			if c == " ": pass
			else:
				ret += c.upper()
				state = 1
		elif state == 1:
			if c == " ": state = 2
			else: ret += c
		elif state == 2:
			if c == " ": pass
			else:
				ret += c.upper()
				state = 1
	return ret

info = [
"Name",
"Date changed",
"Date accessed",
"Date created",
]

locals().update(map(lambda n: (makeSymbolName(n),n), info))
__all__ = map(makeSymbolName, info)

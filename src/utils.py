def unsigned2signed_16(n: int):
	if n > 0x7FFF: return n - 0x10000
	else:          return n

def signed2unsigned_16(n: int):
	if n < 0: return n + 0x10000
	else:     return n

def unsigned2signed_8(n: int):
	if n > 0x7F: return n - 0x100
	else:          return n

def signed2unsigned_8(n: int):
	if n < 0: return n + 0x100
	else:     return n

def signed2unsigned_3(n: int):
	"""
	This function uses a sign bit, since it's
	designed to be used for the YM2610's FM Operator
	Detune register
	"""
	if n < 0: return -n | 4
	else:     return n

def clamp(n, s, l): return max(s, min(n, l))

def list_top(l: list): return l[len(l)-1]
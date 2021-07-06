def unsigned2signed_16(n: int):
	if n > 0x7FFF: return n - 0x10000
	else:          return n

def signed2unsigned_16(n: int):
	if n < 0: return n + 0x10000
	else:     return n

def clamp(n, s, l): return max(s, min(n, l))
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

def wrap_rom_to_mlm_addr(rom_addr: int) -> int:
	FBANK_SIZE = 0x2000 # The size of the fixed bank used for data
	SBANK_SIZE = 0x8000 # The size of switchable bank windows 0, 1, 2 and 3
	if rom_addr < FBANK_SIZE: return rom_addr
	else:
		rom_addr -= FBANK_SIZE
		return (rom_addr % SBANK_SIZE) + FBANK_SIZE
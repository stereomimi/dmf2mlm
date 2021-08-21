# Thank you neogeo dev wiki!
#	check https://wiki.neogeodev.org/index.php?title=ADPCM_codecs

from math import *

STEP_SIZE = [
	16, 17, 19, 21, 23, 25, 28, 31, 34, 37,
   41, 45, 50, 55, 60, 66, 73, 80, 88, 97,
   107, 118, 130, 143, 157, 173, 190, 209, 230, 253,
   279, 307, 337, 371, 408, 449, 494, 544, 598, 658,
   724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552
]

STEP_ADJ = [
	-1, -1, -1, -1, 2, 5, 7, 9, -1, -1, -1, -1, 2, 5, 7, 9
]

class ADPCMAEncoder:
	# Buffers
	buffer: bytes        # Input buffer
	in_buffer: [int] # Temporary buffer
	out_buffer: bytes    # Output buffer
	
	# Decode stuff
	jedi_table: [int]
	acc: int
	decstep: int

	# Encode stuff
	diff: int
	step: int
	predsample: int
	index: int
	prevsample: int
	previndex: int

	def __init__(self):
		self.acc = 0
		self.decstep = 0
		self.prevsample = 0
		self.previndex = 0
		self._jedi_table_init()

	def _jedi_table_init(self):
		self.jedi_table = [None] * (16 * 49)
		for step in range(49):
			for nib in range(16):
				value = (2 * (nib & 0x07) + 1) * STEP_SIZE[step] / 8
				if (nib & 0x08) != 0:
					self.jedi_table[step * 16 + nib] = -round(value)
				else:
					self.jedi_table[step * 16 + nib] = round(value)

	def _ym2610_adpcma_decode(self, code: int) -> int:
		self.acc += self.jedi_table[self.decstep + code]
		self.acc &= 0xFFF # Accumulator wraps
		if (self.acc & 0x800): self.acc |= ~0xFFF # Sign extend if negative
		self.decstep += STEP_ADJ[code & 7] * 16
		if (self.decstep < 0): self.decstep = 0
		if (self.decstep > (48 * 16)): self.decstep = 48 * 16
		return self.acc

	def _ym2610_adpcma_encode(self, sample: int) -> int:
		tempstep: int
		code: int

		self.predsample = self.prevsample
		self.index = self.previndex
		self.step = STEP_SIZE[self.index]

		self.diff = sample - self.predsample
		if self.diff >= 0:
			code = 0
		else:
			code = 8
			self.diff = -self.diff

		tempstep = self.step
		if (self.diff >= tempstep):
			code |= 4
			self.diff -= tempstep
		tempstep >>= 1
		if (self.diff >= tempstep):
			code |= 2
			self.diff -= tempstep
		tempstep >>= 1
		if (self.diff >= tempstep): code |= 1

		self.predsample = self._ym2610_adpcma_decode(code)
		self.index += STEP_ADJ[code]
		if (self.index < 0): self.index = 0
		if (self.index > 48): self.index = 48

		self.prevsample = self.predsample
		self.previndex = self.index

		return code

	def ym_encode(self):
		i: int

		# reset to initial conditions
		self.acc = 0
		self.decstep = 0
		self.prevsample = 0
		self.previndex = 0

		# watch out for odd data count & allocate buffers
		if ((len(self.buffer) / 2) % 2 != 0):
			self.in_buffer = [None] * (len(self.buffer) // 2 + 1)
			self.in_buffer[len(self.in_buffer) - 1] = 0
		else:
			self.in_buffer = [None] * (len(self.buffer) // 2)
		self.out_buffer= [None] * (len(self.in_buffer) // 2)

		# fix byte order and downscale data to 12 bits
		for i in range(0, len(self.buffer), 2):
			self.in_buffer[i // 2] = (self.buffer[i]) | (self.buffer[i + 1] << 8)
			self.in_buffer[i // 2] = self.in_buffer[i // 2]
			self.in_buffer[i // 2] >>= 4

		# actual encoding
		for i in range(0, len(self.in_buffer), 2):
			self.out_buffer[i // 2] = self._ym2610_adpcma_encode(self.in_buffer[i]) << 4
			self.out_buffer[i // 2] |= self._ym2610_adpcma_encode(self.in_buffer[i+1])
			self.out_buffer[i // 2] = self.out_buffer[i // 2]
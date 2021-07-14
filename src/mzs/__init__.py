from .song import *
from enum import Enum, IntEnum
from .. import dmf

M1ROM_SDATA_MAX_SIZE = 30 * 1024

class SoundData:
	"""
	Contains everything to reproduce music and sound effects.
	Basically anything in the m1rom that isn't code nor LUTs.
	"""

	songs: [Song]

	def __init__(self):
		self.songs = []

	def from_dmf(modules: [dmf.Module]):
		self = SoundData()
		for mod in modules:
			self.songs.append(Song.from_dmf(mod))
		return self

	def compile(self) -> bytearray:
		comp_sdata = bytearray(M1ROM_SDATA_MAX_SIZE)
		head_ofs = 0
		symbols = {} # symbol_name: address

		for _ in range(len(self.songs)):
			comp_sdata[head_ofs]   = 0x00
			comp_sdata[head_ofs+1] = 0x00
			head_ofs += 2
			
		return comp_sdata
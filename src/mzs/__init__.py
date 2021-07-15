from .song import *
from enum import Enum, IntEnum
from .. import dmf
from ..defs import *

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

		comp_sdata[head_ofs] = len(self.songs)
		head_ofs += 1 + (len(self.songs) * 2) # Leave space for MLM header

		for i in range(len(self.songs)):
			comp_song, song_ofs = self.songs[i].compile(head_ofs)
			comp_sdata[1 + i*2]     = song_ofs & 0xFF
			comp_sdata[1 + i*2 + 1] = song_ofs >> 8

		return comp_sdata
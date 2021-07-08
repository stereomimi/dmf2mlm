from .song import *
from enum import Enum, IntEnum
from .. import dmf

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
		
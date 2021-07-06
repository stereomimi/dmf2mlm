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

	def add_song_from_dmf(module: dmf.Module):
		self.songs.append(Song.from_dmf(module))
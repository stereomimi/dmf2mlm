from enum import Enum, IntEnum
from .. import dmf,utils,sfx
from ..defs import *
from .song import *
from .sample import *

class SoundData:
	"""
	Contains everything to reproduce music and sound effects.
	Basically anything in the m1rom that isn't code nor LUTs.
	"""

	songs: [Song]
	sfx: [(Sample, int, int)] # (sample, start_addr, end_addr)
	vrom_ofs: int

	def __init__(self):
		self.songs = []
		self.sfx = []
		self.vrom_ofs = 0

	def add_dmfs(self, modules: [dmf.Module]):
		for mod in modules:
			song = Song.from_dmf(mod, self.vrom_ofs)
			self.songs.append(song)
			self.vrom_ofs = utils.list_top(song.samples)[2]+1
		return self
	
	def add_sfx(self, sfx_smps: sfx.SFXSamples):
		pass


	def compile_sdata(self) -> bytearray:
		header_size = len(self.songs) * 2 + 3
		comp_sdata = bytearray(header_size)
		head_ofs = 0

		comp_sdata[head_ofs+2] = len(self.songs)

		head_ofs += header_size # Leave space for MLM header

		for i in range(len(self.songs)):
			comp_song, song_ofs = self.songs[i].compile(head_ofs)
			comp_sdata[3 + i*2]     = song_ofs & 0xFF
			comp_sdata[3 + i*2 + 1] = song_ofs >> 8
			comp_sdata.extend(comp_song)
			head_ofs += len(comp_song)
		
		return comp_sdata

	def compile_vrom(self) -> bytearray:
		FILL_CHAR = 0x80
		vrom_size = 0
		for song in self.songs: 
			vrom_size += (utils.list_top(song.samples)[2]+1) * 256

		comp_vrom = bytearray([FILL_CHAR] * vrom_size)
		if vrom_size > 16777216:
			raise RuntimeError("VROM size exceeds allowed maximum of 16MiB")

		for song in self.songs:
			for sample in song.samples:
				smp_saddr = sample[1] * 256
				smp_eaddr = sample[2] * 256
				comp_vrom[smp_saddr:smp_eaddr] = sample[0].data
		return comp_vrom

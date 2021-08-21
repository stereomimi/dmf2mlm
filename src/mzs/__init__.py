from enum import Enum, IntEnum
from .. import dmf,utils
from ..defs import *
from .song import *
from .sample import *

class SoundData:
	"""
	Contains everything to reproduce music and sound effects.
	Basically anything in the m1rom that isn't code nor LUTs.
	"""

	songs: [Song]
	samples: [(Sample, int, int)] # (sample, start_addr, end_addr)

	def __init__(self):
		self.songs = []
		self.samples = []
		self.vrom_ofs = 0

	def from_dmf(modules: [dmf.Module]):
		self = SoundData()
		vrom_ofs = 0
		for mod in modules:
			self._samples_from_dmf_mod(mod)
			self.samples = map(lambda x: (x[0], x[1]+vrom_ofs, x[2]+vrom_ofs), self.samples)
			self.samples = list(self.samples)
			self.songs.append(Song.from_dmf(mod, self.samples))
			vrom_ofs = utils.list_top(self.samples)[2]+1
		return self

	def _samples_from_dmf_mod(self, module: dmf.Module):
		start_addr = 0
		if len(self.samples) != 0:
			start_addr = utils.top(self.samples).end_addr + 1

		for dsmp in module.samples:
			smp = Sample.from_dmf_sample(dsmp)
			smp_len = len(smp.data) // 256
			end_addr = start_addr + smp_len

			saddr_page = start_addr >> 12
			eaddr_page = end_addr >> 12
			if saddr_page != eaddr_page:
				start_addr = eaddr_page << 12
				end_addr = start_addr + smp_len

			self.samples.append((smp, start_addr, end_addr))
			start_addr = end_addr+1
				

	def compile_sdata(self) -> bytearray:
		header_size = len(self.songs) * 2 + 1
		comp_sdata = bytearray(header_size)
		head_ofs = 0

		comp_sdata[head_ofs] = len(self.songs)
		head_ofs += header_size # Leave space for MLM header

		for i in range(len(self.songs)):
			comp_song, song_ofs = self.songs[i].compile(head_ofs)
			comp_sdata[1 + i*2]     = song_ofs & 0xFF
			comp_sdata[1 + i*2 + 1] = song_ofs >> 8
			comp_sdata.extend(comp_song)
			head_ofs += len(comp_song)
		
		return comp_sdata

	def compile_vrom(self) -> bytearray:
		FILL_CHAR = 0x80
		vrom_size = (utils.list_top(self.samples)[2]+1) * 256
		comp_vrom = bytearray([FILL_CHAR] * vrom_size)
		if vrom_size > 16777216:
			raise RuntimeError("VROM size exceeds allowed maximum of 16MiB")

		for sample in self.samples:
			smp_saddr = sample[1] * 256
			smp_eaddr = sample[2] * 256
			comp_vrom[smp_saddr:smp_eaddr] = sample[0].data
		return comp_vrom

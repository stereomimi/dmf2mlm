from enum import Enum, IntEnum
from .. import dmf,utils,sfx
from ..defs import *
from .song import *
from .sample import *
from .pa_encoder import *
from .other_data import *

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
			if len(song.samples) > 0:
				self.vrom_ofs = utils.list_top(song.samples)[2]+1
		return self
	
	def add_sfx(self, sfx_smps: sfx.SFXSamples, verbose: bool = False):
		pa_encoder = ADPCMAEncoder()
		start_addr = self.vrom_ofs
		for in_path in sfx_smps.paths:
			if verbose: print(f"Converting SFX '{in_path}'...", end='', flush=True)
			smp = Sample.from_wav(in_path, verbose)
			smp_len = len(smp.data) // 256
			end_addr = start_addr + smp_len

			# ADPCM-A channels can't have samples
			# going through different VROM pages
			saddr_page = start_addr >> 12
			eaddr_page = end_addr >> 12
			if saddr_page != eaddr_page:
				start_addr = eaddr_page << 12
				end_addr = start_addr + smp_len
			
			self.sfx.append((smp, start_addr, end_addr))
			start_addr = end_addr+1
			if verbose: print(" OK")


	def compile_sdata(self) -> bytearray:
		header_size = len(self.songs) * 2 + 3
		comp_sdata = bytearray(header_size)

		# The SFX Sample list will be located immediately 
		# after the header, point to that
		comp_sdata[0] = header_size & 0xFF
		comp_sdata[1] = header_size >> 8
		comp_sdata[2] = len(self.songs)

		sfx_addrs = list(map(lambda x: (x[1], x[2]), self.sfx))
		smp_list = SampleList(sfx_addrs).compile()
		comp_sdata.extend(smp_list)

		comp_songs = []
		for i in range(len(self.songs)):
			comp_songs.append(self.songs[i].compile())

		FBANK_SIZE = 0x4000 # The size of the fixed bank used for data
		SBANK_SIZE = 0x7800 # The size of switchable bank windows 0, 1, 2 and 3
		WRAM_PAD   = 0x800  # Padding inbetween banks
		bank = 0
		for i in range(len(self.songs)):
			csong = comp_songs[i]
			max_csong_size = SBANK_SIZE
			if bank == 0: max_csong_size += FBANK_SIZE - header_size
			if len(csong) > max_csong_size:
				raise RuntimeError(f"Song n°{i+1} is too big (>{max_csong_size}, bank {bank})")
			
			bank_limit = FBANK_SIZE + SBANK_SIZE*(bank+1)
			if len(comp_sdata) + len(csong) > bank_limit:
				next_bank_ofs = bank_limit + WRAM_PAD*bank
				pad = bytearray(next_bank_ofs - (len(comp_sdata) + len(csong)))
				comp_sdata.extend(pad)
				bank += 1

			comp_sdata[3 + i*2]     = len(comp_sdata) & 0xFF
			comp_sdata[3 + i*2 + 1] = len(comp_sdata) >> 8
			csong = self.songs[i].replace_symbols(csong, len(comp_sdata))
			comp_sdata.extend(csong)
		
		return comp_sdata

	def compile_vrom(self) -> bytearray:
		FILL_CHAR = 0x80
		vrom_size = 0
		# Check to see whether the song's top vrom end smp ofs is larger
		# (song samples were added after sfx) or if the opposite is true
		if len(self.sfx) > 0:
			vrom_size = utils.list_top(self.sfx)[2] * 256
		if len(self.songs) > 0:
			last_song = utils.list_top(self.songs)
			if len(last_song.samples) > 0:
				song_vrom_end_ofs = utils.list_top(last_song.samples)[2] * 256
				vrom_size = max(song_vrom_end_ofs, vrom_size)

		comp_vrom = bytearray([FILL_CHAR] * vrom_size)
		if vrom_size > 16777216:
			raise RuntimeError("VROM size exceeds allowed maximum of 16MiB")

		for song in self.songs:
			for sample in song.samples:
				smp_saddr = sample[1] * 256
				smp_eaddr = sample[2] * 256
				comp_vrom[smp_saddr:smp_eaddr] = sample[0].data
		for sample in self.sfx:
			smp_saddr = sample[1] * 256
			smp_eaddr = sample[2] * 256
			comp_vrom[smp_saddr:smp_eaddr] = sample[0].data

		return comp_vrom
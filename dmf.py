# Mainly made to support the Neogeo mode

from enum import Enum
from dataclasses import dataclass
import zlib

######################## INSTRUMENT ########################

class Instrument:
	name = ""

@dataclass
class FMOperator:
	am: bool
	ar: int
	dr: int
	mult: int
	rr: int
	sl: int
	tl: int
	dt2: int
	rs: int
	dt: int
	d2r: int
	ssg_enabled: bool
	ssg_mode: int

class FMInstrument(Instrument):
	algorithm = 0
	feedback = 0
	fms = 0
	ams = 0

	operators: [FMOperator] = [] # should have 4 operators

@dataclass
class STDMacro:
	envelope_values: [int]
	loop_position: int

class STDInstrument(Instrument):
	voluje_macro: STDMacro
	arpeggio_macro: STDMacro
	noise_macro: STDMacro
	wavetable_macro: STDMacro # This is probably a channel mode macro on the neogeo


######################## PATTERN ########################

class Note(Enum):
	EMPTY = 0
	CS = 1
	D  = 2
	DS = 3
	E  = 4
	F  = 5
	FS = 6
	G  = 7
	GS = 8
	A  = 9
	AS = 10
	B  = 11
	C  = 12
	NOTE_OFF = 100

class EffectCode(Enum):
	EMPTY = -1

@dataclass
class Effect:
	effect_code: EffectCode
	effect_value: int

@dataclass
class PatternRow:
	note: Note
	octave: int
	volume: int       # -1 means empty
	effects: [Effect]
	instrument: int   # -1 means empty

@dataclass
class Pattern:
	rows: [PatternRow]


######################## SAMPLE ########################

class SampleWidth(Enum):
	BYTE = 8
	WORD = 16

@dataclass
class Sample:
	size: int
	name = ""
	sample_rate: int # Should always be 18.5Khz for ADPCMA samples
	pitch: int
	amplitude: int
	bits: SampleWidth
	data: [int]

######################## MODULE ########################

class System(Enum):
	GENESIS     = 0x02
	GENESIS_EXT = 0x42
	SMS			= 0x03
	GAMEBOY		= 0x04
	PCENGINE	= 0x05
	NES			= 0x06
	C64_8580	= 0x07
	C64_6581	= 0x47
	YM2151		= 0x08
	NEOGEO		= 0x09
	NEOGEO_EXT	= 0x49

class FramesMode(Enum):
	PAL = 0
	NTSC = 1

# This is not a 1:1 match, some redundant things are simplified
class Module:
	data: bytes   # uncompressed data
	head_ofs = 18 # used to calculate addresses in the DMF data

	# Format flags
	version: int

	# System set
	system: System

	# Visual information
	song_name: str
	song_author: str

	# Module information
	time_base: int
	tick_time_1: int
	tick_time_2: int
	hz_value: int
	rows_per_pattern: int
	rows_in_pattern_matrix: int
	pattern_matrix: [[int]]  = [] # pattern_matrix[channel][row]

	# Instruments data
	instruments: [Instrument] = []

	# Wavetable data (UNUSED)
	# wavetables: []

	# Pattern data
	patterns: [[Pattern]] # patterns[channel][id]

	# Sample data
	samples: [Sample]

	def __init__(self, compressed_data: bytes):
		self.data = zlib.decompress(compressed_data)
		if not self.check_file():
			raise RuntimeError("Corrupted DMF file")

		self.parse_format_flags_and_system()
		self.parse_visual_info()
		self.parse_module_info()
		self.parse_pattern_matrix()

	def check_file(self):
		format_string = self.data[0:16].decode(encoding='ascii')
		return format_string == ".DelekDefleMask."

	def parse_format_flags_and_system(self):
		self.version = self.data[16]
		self.system = System(self.data[17])
		if self.system != System.NEOGEO:
			raise RuntimeError("Unsupported system (must be NeoGeo)")

	def parse_visual_info(self):
		name_len = self.data[self.head_ofs]
		self.song_name = self.data[self.head_ofs+1:self.head_ofs+1+name_len].decode(encoding='ascii')
		self.head_ofs += 1 + name_len

		author_len = self.data[self.head_ofs]
		self.song_author = self.data[self.head_ofs+1:self.head_ofs+1+author_len].decode(encoding='ascii')
		self.head_ofs += 1 + author_len + 2 # Ignore highlight information

	def parse_module_info(self):
		self.time_base = self.data[self.head_ofs]
		self.tick_time_1 = self.data[self.head_ofs+1]
		self.tick_time_2 = self.data[self.head_ofs+2]
		
		frames_mode = FramesMode(self.data[self.head_ofs+3])
		using_custom_hz = bool(self.data[self.head_ofs+4])
		if using_custom_hz:
			self.hz_value = int(str(self.data[self.head_ofs+5]), 16)
		else:
			if frames_mode == FramesMode.PAL: self.hz_value = 50
			else: self.hz_value = 60

		self.rows_per_pattern = self.data[self.head_ofs+8]
		self.rows_per_pattern |= self.data[self.head_ofs+9] << 8
		self.rows_per_pattern |= self.data[self.head_ofs+10] << 16
		self.rows_per_pattern |= self.data[self.head_ofs+11] << 24
		self.rows_in_pattern_matrix = self.data[self.head_ofs+12]
		self.head_ofs += 13

	def parse_pattern_matrix(self):
		SYSTEM_TOTAL_CHANNELS = 13
		for ch in range(SYSTEM_TOTAL_CHANNELS):
			rows = []
			for row in range(self.rows_in_pattern_matrix):
				rows.append(self.data[self.head_ofs])
				self.head_ofs += 1
			self.pattern_matrix.append(rows)

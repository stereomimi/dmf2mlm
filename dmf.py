# Mainly made to support the Neogeo mode

from enum import Enum
from dataclasses import dataclass
import zlib

######################## INSTRUMENT ########################

class InstrumentType(Enum):
	STD = 0
	FM = 1

class Instrument:
	name: str
	size: int
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

	def __init__(self, data: bytes):
		self.am = bool(data[0])
		self.ar = data[1]
		self.dr = data[2]
		self.mult = data[3]
		self.rr = data[4]
		self.sl = data[5]
		self.tl = data[6]
		self.dt2 = data[7]
		self.rs = data[8]
		self.dt = data[9] - 3
		self.d2r = data[10]
		self.ssg_enabled = bool(data[11] & 8)
		self.ssg_mode = data[11] & 7

class FMInstrument(Instrument):

	algorithm: int
	feedback: int
	fms: int
	ams: int

	operators: [FMOperator] = [] # should have 4 operators

	def __init__(self, data: bytes):
		OP_COUNT = 4
		OP_SIZE = 12

		self.operators = []

		head_ofs = 0
		name_len = data[head_ofs]
		self.name = data[head_ofs+1:head_ofs+1+name_len].decode(encoding='ascii')
		head_ofs += name_len+2 # Skip instrument mode, it must be FM

		self.algorithm = data[head_ofs]
		self.feedback = data[head_ofs+1]
		self.fms = data[head_ofs+2]
		self.ams = data[head_ofs+3]
		head_ofs += 4

		for i in range(OP_COUNT):
			self.operators.append(FMOperator(data[head_ofs:]))
			head_ofs += OP_SIZE

		self.size = head_ofs

class STDMacro:
	envelope_values: [int]
	loop_position: int
	loop_enabled: bool
	size: int

	def __init__(self, data: bytes, value_ofs: int = 0):
		head_ofs = 0
		envelope_size = data[head_ofs]
		if envelope_size > 127:
			raise RuntimeError(f"Corrupted envelope size (valid range is 0-127; envelope size is {envelope_size}")
		head_ofs += 1

		self.envelope_values = []
		for i in range(envelope_size):
			print("\t",i)
			value = data[head_ofs]
			value |= data[head_ofs+1] << 8
			value |= data[head_ofs+2] << 16
			value |= data[head_ofs+3] << 24
			self.envelope_values.append(value+value_ofs)
			head_ofs += 4

		self.loop_position = data[head_ofs]
		self.loop_enabled = self.loop_position >= 0 and self.loop_position < envelope_size
		self.size = head_ofs+1

class STDArpeggioMode(Enum):
	NORMAL = 0
	FIXED = 1

class STDInstrument(Instrument):
	volume_macro: STDMacro
	arpeggio_macro: STDMacro
	arpeggio_mode: STDArpeggioMode
	noise_macro: STDMacro
	chmode_macro: STDMacro # This is probably a channel mode macro on the neogeo

	def __init__(self, data: bytes):
		head_ofs = 0
		name_len = data[head_ofs]
		self.name = data[head_ofs+1:head_ofs+1+name_len].decode(encoding='ascii')
		head_ofs += name_len+2 # Skip instrument mode, it must be STD

		self.volume_macro = STDMacro(data[head_ofs:])
		head_ofs += self.volume_macro.size
		self.arpeggio_macro = STDMacro(data[head_ofs:], -12)
		head_ofs += self.arpeggio_macro.size
		self.arpeggio_mode = STDArpeggioMode(data[head_ofs])
		self.noise_macro = STDMacro(data[head_ofs+1:])
		head_ofs += self.noise_macro.size+1
		self.chmode_macro = STDMacro(data[head_ofs:])
		head_ofs += self.chmode_macro.size

		self.size = head_ofs

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
		self.parse_instruments()
		self.parse_wavetables()

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

	def parse_instruments(self):
		FM_INSTRUMENT_SIZE = 52
		instrument_count = self.data[self.head_ofs]
		self.head_ofs += 1

		for i in range(instrument_count):
			name_len = self.data[self.head_ofs]
			instrument_type = InstrumentType(self.data[self.head_ofs+1+name_len])
			instrument: Instrument

			if instrument_type == InstrumentType.FM:
				instrument = FMInstrument(self.data[self.head_ofs:])
			else: # STD instrument
				instrument = STDInstrument(self.data[self.head_ofs:])

			self.instruments.append(instrument)
			self.head_ofs += instrument.size

	def parse_wavetables(self):
		wavetable_count = self.data[self.head_ofs]
		if wavetable_count != 0:
			raise RuntimeError("Wavetables aren't supported")
		self.head_ofs += 1
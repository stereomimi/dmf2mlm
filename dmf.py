# Mainly made to support the Neogeo mode

from enum import Enum
from dataclasses import dataclass

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

# This is not a 1:1 match, some redundant things are simplified
class Module:
	# Format flags
	version: int

	# System set
	system: System

	# Visual information
	song_name = ""
	song_author = ""

	# Module information
	time_base: int
	tick_time_1: int
	tick_time_2: int
	hz_value: int
	rows_per_pattern: int
	rows_in_pattern_matrix: int
	pattern_matrix: [[int]] # pattern_matrix[channel][row]

	# Instruments data
	instruments: [Instrument] = []

	# Wavetable data (UNUSED)
	# wavetables: []

	# Pattern data
	patterns: [[Pattern]] # patterns[channel][id]

	# Sample data
	samples: [Sample]
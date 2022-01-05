# Mainly made to support the Neogeo mode

from enum import Enum, IntEnum
from dataclasses import dataclass
from typing import Optional
from itertools import groupby
from copy import deepcopy
import zlib
from .utils import *
from .defs import *

######################## CONSTANTS ########################

SYSTEM_TOTAL_CHANNELS = 13 # NEOGEO
FM_OP_COUNT = 4
FM_OP_SIZE = 12
BASE_ROW_SIZE = 8 # Without effects
EFFECT_SIZE = 4

FM_CH1 = 0
FM_CH2 = 1
FM_CH3 = 2
FM_CH4 = 3
SSG_CH1 = 4
SSG_CH2 = 5
SSG_CH3 = 6
PA_CH1 = 7
PA_CH2 = 8
PA_CH3 = 9
PA_CH4 = 10
PA_CH5 = 11
PA_CH6 = 12

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
		OP_INDEX = [0, 2, 1, 3]
		self.operators = [[], [], [], []]

		head_ofs = 0
		name_len = data[head_ofs]
		self.name = data[head_ofs+1:head_ofs+1+name_len].decode(encoding='ascii')
		head_ofs += name_len+2 # Skip instrument mode, it must be FM

		self.algorithm = data[head_ofs]
		self.feedback = data[head_ofs+1]
		self.fms = data[head_ofs+2]
		self.ams = data[head_ofs+3]
		head_ofs += 4

		for i in range(FM_OP_COUNT):
			self.operators[OP_INDEX[i]] = FMOperator(data[head_ofs:])
			head_ofs += FM_OP_SIZE
		self.size = head_ofs

class STDMacro:
	envelope_values: [int]
	loop_position: int
	loop_enabled: bool
	size: int

	def __init__(self, data: bytes, value_ofs: int = 0):
		head_ofs = 0
		envelope_size = data[head_ofs]
		head_ofs += 1

		if envelope_size > 127:
			raise RuntimeError(f"Corrupted envelope size (valid range is 0-127; envelope size is {envelope_size}")

		self.envelope_values = []
		for i in range(envelope_size):
			value = data[head_ofs]
			value |= data[head_ofs+1] << 8
			value |= data[head_ofs+2] << 16
			value |= data[head_ofs+3] << 24
			self.envelope_values.append(value+value_ofs)
			head_ofs += 4

		if envelope_size > 0:
			self.loop_position = data[head_ofs]
			self.loop_enabled = self.loop_position >= 0
			head_ofs += 1
		else:
			self.loop_enabled = False
			self.loop_position = None

		self.size = head_ofs


class STDArpeggioMode(Enum):
	NORMAL = 0
	FIXED = 1

class STDInstrument(Instrument):
	volume_macro: STDMacro
	arpeggio_macro: STDMacro
	arpeggio_mode: STDArpeggioMode
	noise_macro: STDMacro
	chmode_macro: STDMacro

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

class Note(IntEnum):
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

class EffectCode(IntEnum):
	EMPTY                       = 0xFFFF
	ARPEGGIO                    = 0x00
	PORTAMENTO_UP               = 0x01
	PORTAMENTO_DOWN             = 0x02
	PORTA_TO_NOTE               = 0x03
	VIBRATO                     = 0x04
	PORTA_TO_NOTE_AND_VOL_SLIDE = 0x05
	VIBRATO_AND_VOL_SLIDE       = 0x06
	TREMOLO                     = 0x07
	PANNING                     = 0x08
	SET_SPEED_1                 = 0x09
	VOL_SLIDE                   = 0x0A
	POS_JUMP                    = 0x0B
	RETRIG                      = 0x0C
	PATTERN_BREAK               = 0x0D
	SET_SPEED_2                 = 0x0F
	LFO_CONTROL                 = 0x10
	FEEDBACK_CONTROL            = 0x11
	FM_TL_OP1_CONTROL           = 0x12
	FM_TL_OP2_CONTROL           = 0x13
	FM_TL_OP3_CONTROL           = 0x14
	FM_TL_OP4_CONTROL           = 0x15
	FM_MULT_CONTROL             = 0x16
	FM_DAC_ENABLE               = 0x17
	FM_ECT_CH2_ENABLE           = 0x18
	FM_GLOBAL_AR_CONTROL        = 0x19
	FM_AR_OP1_CONTROL           = 0x1A
	FM_AR_OP2_CONTROL           = 0x1B
	FM_AR_OP3_CONTROL           = 0x1C
	FM_AR_OP4_CONTROL           = 0x1D
	SSG_SET_CHANNEL_MODE        = 0x20
	SSG_SET_NOISE_TONE          = 0x21
	ARPEGGIO_TICK_SPEED         = 0xE0
	NOTE_SLIDE_UP               = 0xE1
	NOTE_SLIDE_DOWN             = 0xE2
	SET_VIBRATO_MODE            = 0xE3
	SET_FINE_VIBRATO_DEPTH      = 0xE4
	SET_FINE_TUNE               = 0xE5
	SET_LEGATO_MODE             = 0xEA
	SET_SAMPLES_BANK            = 0xEB
	NOTE_CUT                    = 0xEC
	NOTE_DELAY                  = 0xED
	SYNC_SIGNAL                 = 0xEE
	SET_GLOBAL_FINE_TUNE        = 0xEF

class Effect:
	code: EffectCode
	value: Optional[int]

	def __init__(self, code: EffectCode, value: int):
		self.code = code
		if value == 0xFFFF: self.value = None
		else:               self.value = value 

	def __eq__(self, other):
		return self.code == other.code and self.value == other.value

class PatternRow:
	note: Optional[Note]
	octave: Optional[int]
	volume: Optional[int]      
	effects: [Effect]
	instrument: Optional[int] 

	def __init__(self):
		self.note       = None
		self.octave     = None
		self.volume     = None
		self.effects    = []
		self.instrument = None
		

	def from_data(data: bytes, effect_count: int):
		row = PatternRow()
		row.note = Note(data[0] | (data[1] << 8))
		row.octave = data[2] | (data[3] << 8)
		row.volume = data[4] | (data[5] << 8)
		head_ofs = 6

		for i in range(effect_count):
			code = EffectCode(data[head_ofs] | (data[head_ofs+1] << 8))
			value = data[head_ofs+2] | (data[head_ofs+3] << 8)
			if code != EffectCode.EMPTY:
				row.effects.append(Effect(code, value))
			head_ofs += 4
			
		row.instrument = data[head_ofs] | (data[head_ofs+1] << 8)
		if row.note == Note.EMPTY and row.octave == 0:
			row.note = None
			row.octave = None
		if row.volume == 0xFFFF: row.volume = None
		if row.instrument == 0xFFFF: row.instrument = None

		return row

	def is_empty(self):
		is_empty = (self.note == None) & (self.octave == None)
		is_empty &= (self.volume == None) & (self.instrument == None)

		for effect in self.effects:
			if effect.code != EffectCode.EMPTY:
				is_empty = False
			else:
				is_empty &= effect.value == None

		return is_empty

	def get_hashable_data(self):
		data = []

		if self.note == None:
			data.append(None)
		else:
			data.append(int(self.note))

		data.append(self.octave)
		data.append(self.volume)
		data.append(self.instrument)

		for effect in self.effects:
			if effect.code == None:
				data.append(None)
			else:
				data.append(int(effect.code))
			data.append(effect.value)
		return tuple(data)

class Pattern:
	rows: [PatternRow]

	def __init__(self):
		self.rows = []

	def from_data(data: bytes, rows_per_pattern: int, effect_count: int):
		pat = Pattern()
		head_ofs = 0

		for i in range(rows_per_pattern):
			pat.rows.append(PatternRow.from_data(data[head_ofs:], effect_count))
			head_ofs += BASE_ROW_SIZE + EFFECT_SIZE*effect_count
		
		return pat

	def __hash__(self):
		row_data = []
		for row in self.rows:
			row_data.append(row.get_hashable_data())
		return hash(tuple(row_data))

	def __eq__(self, other):
		self_hash = hash(self)
		other_hash = hash(other)

		#print(self_hash, "\t", other_hash, "\tself == other\t", self_hash == other_hash)
		return self_hash == other_hash

	def __lt__(self, other):
		self_hash = hash(self)
		other_hash = hash(other)

		#print(self_hash, "\t", other_hash, "\tself < other\t", self_hash < other_hash)
		return self_hash < other_hash

	def is_empty(self) -> bool:
		for row in self.rows:
			if not row.is_empty(): return False
		return True

class PatternMatrix:
	rows_per_pattern: int
	rows_in_pattern_matrix: int
	matrix: [[int]] # pattern_matrix[channel][row]

	def __init__(self):
		self.rows_per_pattern = 0
		self.rows_in_pattern_matrix = 0
		self.matrix = [] # pattern_matrix[channel][row]

######################## SAMPLE ########################

class SampleWidth(IntEnum):
	BYTE = 8
	WORD = 16

class Sample:
	name: str
	#rate: int # Should always be 18.5Khz for ADPCMA samples; ignored
	pitch: int
	amplitude: int
	bits: SampleWidth
	data: [int]
	dmf_size: Optional[int] # Size in the DMF samples data, including name, rate, pitch, etc...
	
	def from_dmf_data(data: bytes):
		"""
		Creates Sample from DMF module sample data
		
		Parameters
		----------
		data
			DMF sample data, should start exactly where the sample data starts
		"""
		s = Sample()

		head_ofs = 0
		sample_size = int.from_bytes(data[head_ofs:head_ofs+3], byteorder='little', signed=False)
		name_len = data[head_ofs+4]
		s.name = data[head_ofs+5:head_ofs+5+name_len].decode(encoding='ascii')
		head_ofs += 6+name_len # ignore sample rate

		s.pitch = data[head_ofs] - 5
		s.amplitude = (data[head_ofs+1] - 50) * 2
		s.bits = SampleWidth(data[head_ofs+2])
		head_ofs += 3

		s.data = []
		for _ in range(sample_size):
			value = data[head_ofs] | (data[head_ofs+1] << 8)
			value = unsigned2signed_16(value)
			s.data.append(value)
			head_ofs += 2

		s.dmf_size = head_ofs
		return s

	def apply_pitch(self):
		"""
		Returns sample with pitch modification applied
		and pitch attribute reset.
		
		Returns
		-------
		Sample
			The original sample, but pitched differently
		"""

		new_sample = Sample()
		new_sample.name = self.name
		new_sample.amplitude = self.amplitude
		new_sample.bits = self.bits
		new_sample.dmf_size = self.dmf_size
		new_sample.data = []
		new_sample.pitch = 0

		sample_count = len(self.data)

		if self.pitch > 0:
			for i in range(0, sample_count, self.pitch+1):
				new_sample.data.append(self.data[i])
		elif self.pitch < 0:
			for i in range(sample_count):
				for _ in range(self.pitch*-1 + 1):
					new_sample.data.append(self.data[i])
		else:
			new_sample.data = self.data

		return new_sample

	def apply_amplitude(self):
		"""
		Returns sample with amplitude modification 
		applied and amplitude attribute reset.
		
		Returns
		-------
		Sample
			The original sample, but pitched differently
		"""

		new_sample = Sample()
		new_sample.name = self.name
		new_sample.pitch = self.pitch
		new_sample.bits = self.bits
		new_sample.dmf_size = self.dmf_size
		new_sample.data = []
		new_sample.amplitude = 0

		multiplier = (self.amplitude + 100.0) / 100.0

		for s in self.data:
			new_s = clamp(s * multiplier, -32768, 32767)
			new_sample.data.append(int(new_s))

		return new_sample
		
	def __str__(self):
		string = f"DMF.Sample {self.name} (\n"
		string += f"\tbit width: {int(self.bits)}\n"
		string += f"\tpitch:     {self.pitch}\n"
		string += f"\tamplitude: {self.amplitude}\n"
		string += f"\tdata size: {len(self.data)}\n)"
		return string

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

class TimeInfo():
	time_base: int
	tick_time_1: int
	tick_time_2: int
	hz_value: int

# This is not a 1:1 match, some redundant things are simplified
class Module:
	data: bytes   # uncompressed data
	head_ofs: int # used to calculate addresses in the DMF data

	# Format flags
	version: int

	# System set
	system: System

	# Visual information
	song_name: str
	song_author: str

	# Module information
	time_info: TimeInfo
	pattern_matrix: PatternMatrix

	# Instruments data
	instruments: [Instrument]

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
		self.parse_patterns()
		self.parse_samples()

	def check_file(self):
		format_string = self.data[0:16].decode(encoding='ascii')
		return format_string == ".DelekDefleMask."

	def parse_format_flags_and_system(self):
		self.version = self.data[16]
		self.system = System(self.data[17])
		if self.system != System.NEOGEO:
			raise RuntimeError("Unsupported system (must be NeoGeo)")
		self.head_ofs = 18

	def parse_visual_info(self):
		name_len = self.data[self.head_ofs]
		self.song_name = self.data[self.head_ofs+1:self.head_ofs+1+name_len].decode(encoding='ascii')
		self.head_ofs += 1 + name_len

		author_len = self.data[self.head_ofs]
		self.song_author = self.data[self.head_ofs+1:self.head_ofs+1+author_len].decode(encoding='ascii')
		self.head_ofs += 1 + author_len + 2 # Ignore highlight information

	def parse_module_info(self):
		self.time_info = TimeInfo()
		self.time_info.time_base = self.data[self.head_ofs]+1
		self.time_info.tick_time_1 = self.data[self.head_ofs+1]
		self.time_info.tick_time_2 = self.data[self.head_ofs+2]
		
		frames_mode = FramesMode(self.data[self.head_ofs+3])
		using_custom_hz = bool(self.data[self.head_ofs+4])
		if using_custom_hz:
			self.time_info.hz_value = self.data[self.head_ofs+5:self.head_ofs+8].decode('ascii').rstrip('\x00')
			self.time_info.hz_value = int(self.time_info.hz_value)
		else:
			if frames_mode == FramesMode.PAL: self.time_info.hz_value = 50
			else:                             self.time_info.hz_value = 60

		self.pattern_matrix = PatternMatrix()
		self.pattern_matrix.rows_per_pattern = self.data[self.head_ofs+8]
		self.pattern_matrix.rows_per_pattern |= self.data[self.head_ofs+9] << 8
		self.pattern_matrix.rows_per_pattern |= self.data[self.head_ofs+10] << 16
		self.pattern_matrix.rows_per_pattern |= self.data[self.head_ofs+11] << 24
		self.pattern_matrix.rows_in_pattern_matrix = self.data[self.head_ofs+12]
		self.head_ofs += 13

	def parse_pattern_matrix(self):
		for ch in range(SYSTEM_TOTAL_CHANNELS):
			rows = []
			for row in range(self.pattern_matrix.rows_in_pattern_matrix):
				rows.append(self.data[self.head_ofs])
				self.head_ofs += 1
			self.pattern_matrix.matrix.append(rows)

	def parse_instruments(self):
		FM_INSTRUMENT_SIZE = 52
		self.instruments = []
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

	def parse_patterns(self):
		self.patterns = []

		for i in range(SYSTEM_TOTAL_CHANNELS):
			channel_patterns = []
			effect_count = self.data[self.head_ofs]
			self.head_ofs += 1

			for j in range(self.pattern_matrix.rows_in_pattern_matrix):
				pattern = Pattern.from_data(self.data[self.head_ofs:], self.pattern_matrix.rows_per_pattern, effect_count)
				channel_patterns.append(pattern)
				self.head_ofs += self.pattern_matrix.rows_per_pattern * (BASE_ROW_SIZE + EFFECT_SIZE*effect_count)
			self.patterns.append(channel_patterns)

	def parse_samples(self):
		sample_count = self.data[self.head_ofs]
		self.samples = []
		self.head_ofs += 1

		for _ in range(sample_count):
			sample = Sample.from_dmf_data(self.data[self.head_ofs:])
			sample = sample.apply_pitch().apply_amplitude()
			self.samples.append(sample)
			self.head_ofs += sample.dmf_size
			#print("\n====", _, "====")
			#print(sample)

	# Take steps to make the DMF module MLM-compatible,
	# used to make encoding algorithms easier
	def patch_for_mzs(self):
		for i in range(SYSTEM_TOTAL_CHANNELS):
			self.patch_unoptimize_pat_matrix(i)
			for j in range(len(self.patterns[i])):
				self.patch_extend_pattern(i, j)

			for j in range(self.pattern_matrix.rows_in_pattern_matrix):
				self.patch_0B_fx(i, j)
		self.time_info.tick_time_base = 1
		self.time_info.tick_time_1 = 1
		self.time_info.tick_time_2 = 1


	def patch_unoptimize_pat_matrix(self, ch: int):
		"""
		Eliminates pattern repetition, this makes other patches much easier.
		Pattern usage is optimized again afterwards, no space is wasted.
		This works because the .DMF format repeats patterns regardless.
		"""
		for i in range(self.pattern_matrix.rows_in_pattern_matrix):
			self.pattern_matrix.matrix[ch][i] = i

	def patch_extend_pattern(self, ch: int, pat_idx: int):
		"""
		Extends the pattern as much as possible.
		|C1 |C2 |D3#|                 (bspd: 2, spdA: 2, spdB: 1)
		|C1 |---|---|---|C2 |---|D3#| (bspd: 1, spdA: 1, spdB: 1)
		DOESN'T SET SPEEDS. That should be done after extending all patterns.
		"""
		old_pat = self.patterns[ch][pat_idx]
		extended_pat = Pattern()
		speed1 = self.time_info.tick_time_1 * self.time_info.time_base
		speed2 = self.time_info.tick_time_2 * self.time_info.time_base

		for i in range(len(old_pat.rows)):
			row = old_pat.rows[i]
			end_of_row_fx_idxs = []
			end_of_row_fxs = []

			# Some pattern are executed at the *end* of a tick, not
			# the start. Those need to be appropiately dealt with.
			#   Find all the indexes of said effects.
			for i in range(len(row.effects)):
				fx = row.effects[i]
				if fx.code == EffectCode.POS_JUMP:
					end_of_row_fx_idxs.append(i)

			# Reverse the index list as to not have to deal with
			# needed element indexes changing. Pop away all the indexes
			# into a different array
			end_of_row_fx_idxs.sort(reverse=True)
			for idx in end_of_row_fx_idxs:
				fx = row.effects.pop(idx)
				end_of_row_fxs.append(fx)

			extended_pat.rows.append(row)
			if i%2 == 0: 
				for _ in range(speed1-1): extended_pat.rows.append(PatternRow())
			else:
				for _ in range(speed2-1): extended_pat.rows.append(PatternRow())
			extended_pat.rows[-1].effects.extend(end_of_row_fxs)

		self.patterns[ch][pat_idx] = extended_pat
		self.pattern_matrix.rows_per_pattern = len(extended_pat.rows)
		
	def patch_0B_fx(self, ch: int, patmat_row: int):
		"""
		If there's a $0B (Position Jump) effect, add one
		to every nonempty channel in the same row. 
		|C1 0B02|D4 ----|E2 0400| -> |C1 0B02|D4 0B02|E2 0400 0B02|

		ONLY WORKS WITH AN UNOPTIMIZED PATTERN MATRIX!
		"""
		pat_idx = self.pattern_matrix.matrix[ch][patmat_row]
		pat = self.patterns[ch][pat_idx]
		for i in range(len(pat.rows)):
			for j in range(len(pat.rows[i].effects)):
				if pat.rows[i].effects[j].code == EffectCode.POS_JUMP:
					self.apply_0B_fx_patch(patmat_row, i, pat.rows[i].effects[j].value)

	def apply_0B_fx_patch(self, patmat_row: int, row_idx: int, fx_val: int):
		for i in range(SYSTEM_TOTAL_CHANNELS):
			if not self.is_channel_empty(i):
				pat_idx = self.pattern_matrix.matrix[i][patmat_row]
				row = self.patterns[i][pat_idx].rows[row_idx]
				chrow_has_0b = False
				for j in range(len(self.patterns[i][pat_idx].rows[row_idx].effects)):
					if row.effects[j].code == EffectCode.POS_JUMP:
						chrow_has_0b = True
						if row.effects[j].value != fx_val:
							raise RuntimeError(f"Clashing $0B effect at ch {i}, matrix row {patmat_row}, row {row_idx}")
				if not chrow_has_0b:
					fx = Effect(EffectCode.POS_JUMP, fx_val)
					self.patterns[i][pat_idx].rows[row_idx].effects.append(fx)

	def optimize(self):
		for ch in range(SYSTEM_TOTAL_CHANNELS):
			self.optimize_equal_patterns(ch)
			self.optimize_empty_channels(ch)

	def optimize_equal_patterns(self, ch: int):
		"""
		Merges equal patterns and updates the pattern matrix accordingly
		"""
		patterns_with_ids = [] # [(pattern, id); ...]
		new_pattern_list = []

		# Arranges patterns in a easy to group format
		for i in range(len(self.patterns[ch])):
			patterns_with_ids.append((self.patterns[ch][i], i))
		patterns_with_ids.sort(key=lambda tup: tup[0])

		# Finds group of equal patterns, adds to the new pattern list
		# a single pattern (doesn't matter which they're all the same)
		# and then also updates the pattern matrix accordingly.
		for _, eq_pats_iter in groupby(patterns_with_ids, key=lambda tup: tup[0]):
			eq_pats = list(eq_pats_iter)
			merged_pat_idx = eq_pats[0][1]
			new_pattern_list.append(self.patterns[ch][merged_pat_idx])
			for pat, idx in eq_pats:
				self.pattern_matrix.matrix[ch][idx] = len(new_pattern_list)-1
		
		self.patterns[ch] = new_pattern_list

	def optimize_empty_channels(self, ch: int):
		"""
		If the channel is completely empty, it sets its
		pattern matrix to None
		"""
		#unique_patterns = set(self.pattern_matrix.matrix[ch])
		#is_empty = True

		#for pat_idx in unique_patterns:
		#	if not self.patterns[ch][pat_idx].is_empty():
		#		is_empty = False
		#		break
		#if is_empty: self.pattern_matrix.matrix[ch] = None
		if self.is_channel_empty(ch):
			self.pattern_matrix.matrix[ch] = None

	def is_channel_empty(self, ch: int):
		unique_patterns = set(self.pattern_matrix.matrix[ch])
		for pat_idx in unique_patterns:
			if not self.patterns[ch][pat_idx].is_empty():
				return False
		return True

def get_channel_kind(channel: int):
	if channel <= FM_CH4:    return ChannelKind.FM
	elif channel <= SSG_CH3: return ChannelKind.SSG
	return ChannelKind.ADPCMA

def note_to_pitch(channel: int, note: int, octave: int):
	"""
	Converts a note and an octave to a pitch usable by the YM2610.
	(This uses the same algorithms as the MZS driver)
	"""
	kind = get_channel_kind(channel)
	if note == 12: # C is expressed as 12 instead than 0
		note = 0
		if isinstance(octave, int): 
			octave += 1
	if kind == ChannelKind.FM:
		return _note_to_pitch_fm(note, octave)
	elif kind == ChannelKind.SSG:
		return _note_to_pitch_ssg(note, octave)
	else:
		raise RuntimeError("ADPCM-A channels don't have a pitch")

def _note_to_pitch_fm(note: int, octave: int):
	pitch_LUT = [
		#  C     C#     D      D#     E      F      F#     G     
		0x269, 0x28E, 0x2B5, 0x2DE, 0x30A, 0x338, 0x369, 0x39D,
		#  G#    A      A#     B
		0x3D4, 0x40E, 0x44C, 0x48D
	]
	return pitch_LUT[note] | (octave << 11) # --BBBFFF'FFFFFFFF

def _note_to_pitch_ssg(note: int, octave: int):
	if octave < 2:
		return 0
	if not hasattr(_note_to_pitch_ssg, "pitch_LUT"):
		_note_to_pitch_ssg.pitch_LUT = _calculate_ssg_pitch_LUT()
	return _note_to_pitch_ssg.pitch_LUT[(octave-2)*12 + note]

def _calculate_ssg_pitch_LUT():
	"""
	Calculate LUT from C2 to B7 (for SSG OPNBs)
	"""
	number_of_octaves = 6
	base_pitches = [
		# C2     C#2    D2     D#2    E2     F2
		65.41, 69.30, 73.42,  77.78, 82.41,  87.31,
		# F#2    G2     G#2    A2     A#2    B2
		92.50, 98.00, 103.83, 110.0, 116.54, 123.47
	]
	LUT = []

	for octave in range(1, number_of_octaves+1):
		for base_pitch in base_pitches:
			pitch = base_pitch * pow(2,octave)
			SSG_pitch = round(250000 / pitch)
			LUT.append(SSG_pitch)
	return LUT

def _convert_fmpitch_to_block(old_pitch: int, new_block: int):
	"""
	FNum = 11 * freq * 1048576 / 8000000 / 2^(block-1)
	thus...
	k = 294912 / 15625
	FNum = k * freq / 2^(block-1)
	freq = 1/k * FNum * 2^(block-1) 
	"""
	if new_block < 0 or new_block >= 8: 
		raise RuntimeError("Invalid block")
	if pitch < 0 or pitch > 0x7FF:
		raise RuntimeError("Invalid pitch")
	K = 294912.0 / 15625.0

	old_block = old_pitch >> 11
	old_fnum = old_pitch & 0x7FF
	freq = 1/K * old_fnum * 2**(old_block - 1)
	new_fnum = K * freq / 2**(new_block - 1)

	if new_fnum < 0 or new_fnum > 0x7FF:
		raise RuntimeError("Frequency is outside of block range")
		
	return new_fnum | (new_block<<11)
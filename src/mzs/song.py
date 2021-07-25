from .instrument import *
from .other_data import *
from .event import *
from .. import dmf
from ..defs import *

class EventList:
	events: [SongEvent]
	is_sub: bool

	def __init__(self, kind = "main"):
		self.events = []
		if kind == "sub":
			self.is_sub = True
		else:
			self.is_sub = False

	def get_sym_name(self, ch: int, idx: int = 0):
		if self.is_sub:
			return "SUBEL:CH{0:01X};{1:02X}".format(ch, idx)
		else:
			return "EL:{0:02X}".format(ch)

	def compile(self, ch: int, symbols: dict) -> bytearray:
		comp_data = bytearray()
		for event in self.events:
			comp_event = event.compile(ch, symbols)
			comp_data.extend(comp_event)
			#print(type(event).__name__.ljust(32), list(comp_event))

		return comp_data

	def print(self):
		for event in self.events:
			if self.is_sub:
				print("\t", str(event.timing).ljust(5), event)
			else:
				print("0x{0:04X} ".format(event.timing), event)

class Song:
	channels: [EventList]
	sub_event_lists: [[EventList]] # sub_event_lists[channel][sub_el]
	instruments: [Instrument]
	other_data: [OtherData]
	tma_counter: int

	sub_el_idx_matrix: [[int]] # sub_el_idx_matrix[channel][id]

	def __init__(self):
		self.channels = []
		self.sub_event_lists = []
		self.instruments = []
		self.other_data = []
		self.tma_counter = 0
		self.sub_el_idx_matrix = []
		for _ in range(dmf.SYSTEM_TOTAL_CHANNELS):
			self.channels.append(EventList())
			self.sub_event_lists.append([])
			self.sub_el_idx_matrix.append([])

	def from_dmf(module: dmf.Module):
		self = Song()
		hz_value = module.time_info.hz_value * module.time_info.time_base
		self.tma_counter = Song.calculate_tma_cnt(hz_value)
		self._instruments_from_dmf(module)

		for ch in range(len(module.pattern_matrix.matrix)):
			if module.pattern_matrix.matrix[ch] == None:
				self.channels[ch] = None
				self.sub_event_lists[ch] = None
			else:
				self._ch_event_lists_from_dmf_pat_matrix(module.pattern_matrix, ch)
				self._sub_event_lists_from_dmf(module, ch)

		self._ch_reorder()
		return self

	def calculate_tma_cnt(frequency: int):
		cnt = 1024.0 - (1.0 / frequency / 72.0 * 4000000.0)
		if cnt < 0 or cnt > 0x3FF:
			raise RuntimeError("Invalid timer a counter value")
		return round(cnt)

	def _instruments_from_dmf(self, module: dmf.Module):
		"""
		DMF Instruments are offset by 1, since Instrument 0
		is used for ADPCM-A samples. This function also
		assumes self.other_data is empty
		"""

		if len(module.instruments) > 255:
			raise RuntimeError("Maximum supported instrument count is 255")

		for dinst in module.instruments:
			mzs_inst = None
			if isinstance(dinst, dmf.FMInstrument):
				mzs_inst = FMInstrument.from_dmf_inst(dinst)
			else: # Is SSG Instrument
				mzs_inst, new_odata = SSGInstrument.from_dmf_inst(dinst, len(self.other_data))
				self.other_data.extend(new_odata)
			self.instruments.append(mzs_inst)

		self.instruments.append(ADPCMAInstrument(len(self.other_data)))
		self.other_data.append(SampleList())

	def _ch_event_lists_from_dmf_pat_matrix(self, pat_mat: dmf.PatternMatrix, ch: int):
		unique_patterns = list(set(pat_mat.matrix[ch]))
		unique_patterns.sort()

		for row in range(pat_mat.rows_in_pattern_matrix):
			pattern = pat_mat.matrix[ch][row]
			sub_el_idx = unique_patterns.index(pattern)
			self.channels[ch].events.append(SongComJumpToSubEL(sub_el_idx))
			self.sub_el_idx_matrix[ch].append(sub_el_idx)
		self.channels[ch].events.append(SongComEOEL())

	def _sub_event_lists_from_dmf(self, module: dmf.Module, ch: int):
		converted_sub_els = set()

		for i in range(len(self.sub_el_idx_matrix[ch])):
			sub_el_idx = self.sub_el_idx_matrix[ch][i]
			dmf_pat = module.patterns[ch][i]

			if sub_el_idx not in converted_sub_els:
				sub_el = self._sub_el_from_pattern(dmf_pat, ch, module.time_info)
				self.sub_event_lists[ch].insert(sub_el_idx, sub_el)
				converted_sub_els.add(sub_el_idx)

	def _sub_el_from_pattern(self, pattern: dmf.Pattern, ch: int, time_info: dmf.TimeInfo):
		STARTING_VOLUMES = [
			0x7F, 0x7F, 0x7F, 0x7F,            # FM
			0x0F, 0x0F, 0x0F,                  # SSG
			0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F # ADPCMA
		]
		sub_el = EventList("sub")
		sub_el.events.append(SongComWaitTicks())

		ch_kind = dmf.get_channel_kind(ch)
		ticks_since_last_com = 0
		current_instrument = 0
		current_volume = STARTING_VOLUMES[ch]

		for i in range(len(pattern.rows)):
			row = pattern.rows[i]

			if not row.is_empty():
				last_com = utils.list_top(sub_el.events)
				last_com.timing = ticks_since_last_com
				ticks_since_last_com = 0

				if row.instrument != None and row.instrument != current_instrument:
					current_instrument = row.instrument
					sub_el.events.append(SongComChangeInstrument(current_instrument))

				if row.volume != None and row.volume != current_volume:
					#volume_difference = 
					current_volume = row.volume
					mlm_volume = Song.ymvol_to_mlmvol(ch_kind, current_volume)
					sub_el.events.append(SongComSetChannelVol(mlm_volume))
				
				if row.note == dmf.Note.NOTE_OFF:
					sub_el.events.append(SongComNoteOff())
				elif row.note != None and ch_kind == ChannelKind.ADPCMA:
					sub_el.events.append(SongNote(row.note))
				elif row.note != None and row.octave != None:
					mlm_note = Song.dmfnote_to_mlmnote(ch_kind, row.note, row.octave)
					sub_el.events.append(SongNote(mlm_note))

			if i % 2 == 0: ticks_since_last_com += time_info.tick_time_1
			else:          ticks_since_last_com += time_info.tick_time_2

		utils.list_top(sub_el.events).timing = ticks_since_last_com
		
		sub_el.events.append(SongComReturnFromSubEL())
		return sub_el

	def _ch_reorder(self):
		DMF2MLM_CH_ORDER = [
			6, 7, 8, 9,      # FM channels
			10, 11, 12,      # SSG channels
			0, 1, 2, 3, 4, 5 # ADPCMA channels
		]

		ch_els = self.channels.copy()
		ch_subels = self.sub_event_lists.copy()

		for i in range(len(DMF2MLM_CH_ORDER)):
			self.channels[DMF2MLM_CH_ORDER[i]]        = ch_els[i]
			self.sub_event_lists[DMF2MLM_CH_ORDER[i]] = ch_subels[i]


	def ymvol_to_mlmvol(ch_kind: ChannelKind, va: int):
		"""
		Takes a volume in YM2610 register ranges (they depend on the channel
		kind) and converts it into the global MLM volume (0x00 ~ 0xFF)
		"""
		YM_VOL_MAXS = [ 0x1F, 0x7F, 0x1F ] # ADPCMA, FM, SSG
		MLM_VOL_MAX = 0xFF
		return round(MLM_VOL_MAX * va / YM_VOL_MAXS[ch_kind])

	def dmfnote_to_mlmnote(ch_kind: ChannelKind, note: int, octave: int):
		"""
		Only used for FM and SSG channels
		"""
		if note == 12: # C is be expressed as 12 instead than 0
			note = 0 
			octave += 1
			
		if ch_kind == ChannelKind.FM:
			return (note | (octave<<4)) & 0xFF
		elif ch_kind == ChannelKind.SSG:
			return octave*12 + note
		else:
			raise RuntimeError("Unsupported channel kind")

	def compile(self, head_ofs: int) -> (bytearray, int):
		"""
		Returns the compiled address and the song offset
		in a tuple, in that order.
		"""
		comp_data = bytearray()
		symbols = {} # symbol_name: address

		comp_odata, odata_sym = self.compile_other_data(head_ofs)
		comp_data.extend(comp_odata)
		symbols |= odata_sym
		head_ofs += len(comp_odata)

		symbols["INSTRUMENTS"] = head_ofs
		comp_inst_data = self.compile_instruments(symbols)
		comp_data.extend(comp_inst_data)
		head_ofs += len(comp_inst_data)

		for i in range(dmf.SYSTEM_TOTAL_CHANNELS):
			if self.channels[i] != None:
				comp_subel_data, subel_syms = self.compile_sub_els(i, head_ofs)
				comp_data.extend(comp_subel_data)
				symbols |= subel_syms
				head_ofs += len(comp_subel_data)

				symbols[self.channels[i].get_sym_name(i)] = head_ofs
				comp_el_data = self.channels[i].compile(i, symbols)
				comp_data.extend(comp_el_data)
				head_ofs += len(comp_el_data)
		
		symbols["HEADER"] = head_ofs
		comp_header_data = self.compile_header(symbols)
		comp_data.extend(comp_header_data)
		head_ofs += len(comp_header_data)

		if head_ofs >= M1ROM_SDATA_MAX_SIZE:
			raise RuntimeError("Compiled sound data overflow")
		
		#for s in symbols: print(s.ljust(16), "0x{0:04X}".format(symbols[s]))
		
		return comp_data, symbols["HEADER"]

	def compile_other_data(self, head_ofs: int) -> (bytearray, dict):
		"""
		Returns compiled other data and a symbol table
		"""
		symbols = {}
		comp_data = bytearray()

		for i in range(len(self.other_data)):
			symbols[OtherDataIndex(i).get_sym_name()] = head_ofs

			comp_odata = self.other_data[i].compile()
			comp_data.extend(comp_odata)
			head_ofs += len(comp_odata)

		return comp_data, symbols

	def compile_instruments(self, symbols: dict) -> bytearray:
		comp_data = bytearray()

		for inst in self.instruments:
			inst_data = inst.compile(symbols)
			comp_data.extend(inst_data)

		return comp_data

	def compile_sub_els(self, ch: int, head_ofs: int) -> (bytearray, dict):
		"""
		Returns compiled other data and a new symbol table
		"""
		comp_data = bytearray()
		symbols = {}

		for i in range(len(self.sub_event_lists[ch])):
			subel = self.sub_event_lists[ch][i]
			symbols[subel.get_sym_name(ch, i)] = head_ofs

			comp_subel = subel.compile(ch, symbols)
			comp_data.extend(comp_subel)
			head_ofs += len(comp_subel)

		return (comp_data, symbols)

	def compile_header(self, symbols: dict) -> bytearray:
		comp_data = bytearray()
		
		for i in range(len(self.channels)):
			if self.channels[i] == None:
				comp_data.append(0x00) # LSB
				comp_data.append(0x00) # MSB
			else:
				channel_ofs = symbols[self.channels[i].get_sym_name(i)]
				comp_data.append(channel_ofs & 0xFF) # LSB
				comp_data.append(channel_ofs >> 8)   # MSB

		comp_data.append(self.tma_counter & 0xFF)       # TMA LSB
		comp_data.append(self.tma_counter >> 8)         # TMA MSB
		comp_data.append(1)                             # Base time
		comp_data.append(symbols["INSTRUMENTS"] & 0xFF) # Inst. LSB
		comp_data.append(symbols["INSTRUMENTS"] >> 8)   # Inst. MSB

		return comp_data
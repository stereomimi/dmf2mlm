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

		total_count = 0

		for ch in range(len(module.pattern_matrix.matrix)):
			self._ch_event_lists_from_dmf_pat_matrix(module.pattern_matrix, ch)
			self._sub_event_lists_from_dmf(module, ch)

			for subel in self.sub_event_lists[ch]:
				total_count += len(subel.events)
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
		
		self.instruments.append(ADPCMAInstrument(0))
		self.other_data.append(SampleList())

		for dinst in module.instruments:
			mzs_inst = None
			if isinstance(dinst, dmf.FMInstrument):
				mzs_inst = FMInstrument.from_dmf_inst(dinst)
			else: # Is SSG Instrument
				mzs_inst, new_odata = SSGInstrument.from_dmf_inst(dinst, len(self.other_data))
				self.other_data.extend(new_odata)
			self.instruments.append(mzs_inst)

	def _ch_event_lists_from_dmf_pat_matrix(self, pat_mat: dmf.PatternMatrix, ch: int):
		unique_patterns = list(set(pat_mat.matrix[ch]))
		unique_patterns.sort()

		for row in range(pat_mat.rows_in_pattern_matrix):
			pattern = pat_mat.matrix[ch][row]
			sub_el_idx = unique_patterns.index(pattern)
			self.channels[ch].events.append(SongComJumpToSubEL(sub_el_idx))
			self.sub_el_idx_matrix[ch].append(sub_el_idx)

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

			if row.is_empty():
				if i % 2 == 0: ticks_since_last_com += time_info.tick_time_1
				else:          ticks_since_last_com += time_info.tick_time_2
			else:
				last_com = utils.list_top(sub_el.events)
				last_com.timing = ticks_since_last_com
				ticks_since_last_com = 0

				if row.instrument != None and row.instrument != current_instrument:
					current_instrument = row.instrument
					sub_el.events.append(SongComChangeInstrument(current_instrument))

				if row.volume != None and row.volume != current_volume:
					current_volume = row.volume
					mlm_volume = Song.ymvol_to_mlmvol(ch_kind, current_volume)
					sub_el.events.append(SongComChangeInstrument(current_instrument))
				
				if row.note == dmf.Note.NOTE_OFF:
					sub_el.events.append(SongComNoteOff())
				elif row.note != None and ch_kind == ChannelKind.ADPCMA:
					sub_el.events.append(SongNote(row.note))
				elif row.note != None and row.octave != None:
					mlm_note = Song.dmfnote_to_mlmnote(ch_kind, row.note, row.octave)
					sub_el.events.append(SongNote(mlm_note))

		if i % 2 == 0: 
			utils.list_top(sub_el.events).timing = time_info.tick_time_1 + ticks_since_last_com
		else:          
			utils.list_top(sub_el.events).timing = time_info.tick_time_2 + ticks_since_last_com
		
		sub_el.events.append(SongComReturnFromSubEL())
		return sub_el

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
		if ch_kind == ChannelKind.FM:
			return (note | (octave<<4)) & 0xFF
		elif ch_kind == ChannelKind.SSG:
			return octave*12 + note
		else:
			raise RuntimeError("Unsupported channel kind")
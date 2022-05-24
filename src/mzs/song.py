from .instrument import *
from .other_data import *
from .event import *
from .sample import *
from ..defs import *
from ..sym_table import *
from .. import dmf

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

	def ceompile(self, ch: int, symbols: dict, idx: int = 0) -> (bytearray, dict):
		comp_data = bytearray()
		for event in self.events:
			comp_event = event.compile(ch, symbols)
			comp_data.extend(comp_event)

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
	time_base: int
	samples: [(Sample, int, int)] # (sample, start_addr, end_addr)
	notes_below_b2_present: bool
	sub_el_idx_matrix: [[int]] # sub_el_idx_matrix[channel][id]
	symbols: SymbolTable

	def __init__(self):
		self.channels = []
		self.sub_event_lists = []
		self.instruments = []
		self.other_data = []
		self.tma_counter = 0
		self.time_base = 1
		self.sub_el_idx_matrix = []
		self.samples = []
		self.notes_below_b2_present = False
		self.symbols = SymbolTable()
		
		for _ in range(dmf.SYSTEM_TOTAL_CHANNELS):
			self.channels.append(EventList())
			self.sub_event_lists.append([])
			self.sub_el_idx_matrix.append([])

	def from_dmf(module: dmf.Module, vrom_ofs: int):
		TMA_MAX_FREQ = 55560.0
		TMA_MIN_FREQ = 54.25
		MAX_TIME_BASE = 255
		MIN_FREQ = TMA_MIN_FREQ / MAX_TIME_BASE
		self = Song()
		hz_value = module.time_info.hz_value

		# There's probably a better way to do this, but I'd really
		# like using the base time feature in the driver eventually
		if hz_value > TMA_MAX_FREQ:
			raise RuntimeError("Invalid frequency (higher than 55.56kHz)")
		elif hz_value < TMA_MIN_FREQ:
			for i in range(2, MAX_TIME_BASE+1):
				if hz_value*i > TMA_MAX_FREQ:
					raise RuntimeError("Invalid frequency")
				elif hz_value*i > TMA_MIN_FREQ:
					self.time_base = i
					hz_value *= i
					break
			if hz_value < TMA_MIN_FREQ:
				raise RuntimeError(f"Invalid frequency (lower than {MIN_FREQ}Hz)")

		self.tma_counter = Song.calculate_tma_cnt(hz_value)

		self._samples_from_dmf_mod(module, vrom_ofs)
		#self.samples = map(lambda x: (x[0], x[1], x[2]), self.samples)
		#self.samples = list(self.samples)
		self._instruments_from_dmf(module, self.samples)

		for ch in range(len(module.pattern_matrix.matrix)):
			if module.pattern_matrix.matrix[ch] == None:
				self.channels[ch] = None
				self.sub_event_lists[ch] = None
			else:
				self._ch_event_lists_from_dmf_pat_matrix(module.pattern_matrix, ch)
				self._sub_event_lists_from_dmf(module, ch)

		self._ch_reorder()
		if self.notes_below_b2_present:
			print("\n[WARNING] SSG NOTES LOWER THAN C2 PRESENT. THEY HAVE BEEN SET TO C2")
		return self

	def calculate_tma_cnt(frequency: int):
		cnt = 1024.0 - (1.0 / frequency / 72.0 * 4000000.0)
		if cnt < 0 or cnt > 0x3FF:
			raise RuntimeError("Invalid timer a counter value")
		return round(cnt)

	def _instruments_from_dmf(self, module: dmf.Module, samples: [(Sample, int, int)]):
		"""
		This function assumes self.other_data is empty
		"""

		if len(module.instruments) > 255:
			raise RuntimeError("Maximum supported instrument count is 254")

		for dinst in module.instruments:
			mzs_inst = None
			if isinstance(dinst, dmf.FMInstrument):
				mzs_inst = FMInstrument.from_dmf_inst(dinst)
			else: # Is SSG Instrument
				mzs_inst, new_odata = SSGInstrument.from_dmf_inst(dinst, len(self.other_data))
				self.other_data.extend(new_odata)
			self.instruments.append(mzs_inst)

		self.instruments.append(ADPCMAInstrument(len(self.other_data)))
		sample_addresses = list(map(lambda x: (x[1], x[2]), samples))
		self.other_data.append(SampleList(sample_addresses))

	def _samples_from_dmf_mod(self, module: dmf.Module, vrom_ofs: int):
		start_addr = vrom_ofs

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


	def _ch_event_lists_from_dmf_pat_matrix(self, pat_mat: dmf.PatternMatrix, ch: int):
		"""
		Here the main event lists, that jump to the sub-event
		lists that contain the actual patterns, are created.
		"""
		unique_patterns = list(set(pat_mat.matrix[ch]))
		unique_patterns.sort()

		ch_kind = dmf.get_channel_kind(ch)
		if ch_kind == dmf.ChannelKind.ADPCMA:
			pa_inst = len(self.instruments) - 1
			self.channels[ch].events.append(SongComChangeInstrument(pa_inst))

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
			dmf_pat_idx = module.pattern_matrix.matrix[ch][i]
			dmf_pat = module.patterns[ch][dmf_pat_idx]

			if sub_el_idx not in converted_sub_els:
				sub_el = self._sub_el_from_pattern(dmf_pat, ch, module.time_info)
				self.sub_event_lists[ch].insert(sub_el_idx, sub_el)
				converted_sub_els.add(sub_el_idx)

	def _sub_el_from_pattern(self, pattern: dmf.Pattern, ch: int, time_info: dmf.TimeInfo):
		"""
		Here DMF patterns get converted into MLM sub-event lists
		"""
		if not hasattr(Song._sub_el_from_pattern, "warned_uncomp_fxs"):
			Song._sub_el_from_pattern.warned_uncomp_fxs = []

		df_fx_to_mlm_event_map = {
			1:  SongComPitchUpwardSlide,
			2:  SongComPitchDownwardSlide,
			8:  SongComSetPanning,
			11: SongComPositionJump,
			18: SongComFMTL1Set,
			19: SongComFMTL2Set,
			20: SongComFMTL3Set,
			21: SongComFMTL4Set
		}

		sub_el = EventList("sub")
		sub_el.events.append(SongComWaitTicks())

		ch_kind = dmf.get_channel_kind(ch)
		ticks_since_last_com = 0
		current_instrument = None
		current_volume = None
		current_note   = None
		current_octave = None
		current_fine_tune = 0
		sample_bank = 0

		for i in range(len(pattern.rows)):
			row = pattern.rows[i]
			do_end_pattern = False

			if not row.is_empty():
				last_com = utils.list_top(sub_el.events)
				last_com.timing += ticks_since_last_com
				ticks_since_last_com = 0

				# Check for sample bank switches before
				# possibly using samples
				for effect in row.effects:
					if effect.code == dmf.EffectCode.SET_SAMPLES_BANK:
						if effect.value < ceil(len(self.samples) / 12.0): # If bank actually exists
							sample_bank = effect.value

				if row.note == dmf.Note.NOTE_OFF:
					sub_el.events.append(SongComNoteOff())
					current_note = None
					current_octave = None

				if row.volume != None and row.volume != current_volume:
					use_vol_ofs = False # Use the shortened set volume command?
					#if current_volume != None and ch_kind != ChannelKind.SSG: 
					#	use_vol_ofs = abs(current_volume - row.volume) <= 8
					
					if use_vol_ofs:
						volume_offset = current_volume - row.volume
						sub_el.events.append(SongComOffsetChannelVol(volume_offset))
					else:
						mlm_volume = Song.ymvol_to_mlmvol(ch_kind, row.volume)
						sub_el.events.append(SongComSetChannelVol(mlm_volume))
					current_volume = row.volume
					
				if row.instrument != None and row.instrument != current_instrument and ch_kind != dmf.ChannelKind.ADPCMA:
					current_instrument = row.instrument
					sub_el.events.append(SongComChangeInstrument(current_instrument))

				if row.note != dmf.Note.NOTE_OFF and row.note != None and row.octave != None:
					current_note = row.note
					current_octave = row.octave
					current_fine_tune = 0
					mlm_note = self.dmfnote_to_mlmnote(ch_kind, row.note, row.octave)
					if ch_kind == ChannelKind.ADPCMA: mlm_note += sample_bank * 12
					sub_el.events.append(SongNote(mlm_note))

				# Check all other effects here
				for effect in row.effects:
					if effect.code == dmf.EffectCode.SET_FINE_TUNE and effect.value != None:
						if current_note != None and current_octave != None: # Vibrato should go on after a note is stopped?
							PM = 0 # Middle Pitch idx
							PL = 1 # Lower Pitch idx
							PH = 2 # Higher pitch idx
							prange = self.dmfnote_to_ympitch_range(ch_kind, current_note, current_octave)
							new_ftune = 0
							if effect.value > 0x80:
								new_ftune = (prange[PH] - prange[PM]) * (effect.value - 128) / 127
							elif effect.value < 0x80:
								new_ftune = (prange[PL] - prange[PM]) * (128 - effect.value) / -128
							new_ftune = round(new_ftune)
							ftune_ofs = new_ftune - current_fine_tune
							current_fine_tune = new_ftune
							sub_el.events.append(SongComIncPitchOfs(ftune_ofs))

					elif effect.code != dmf.EffectCode.SET_SAMPLES_BANK and effect.value != None:
						if effect.code in df_fx_to_mlm_event_map:
							mlm_event = df_fx_to_mlm_event_map[effect.code]
							sub_el.events.append(mlm_event.from_dffx(effect.value))
							if effect.code == dmf.EffectCode.POS_JUMP:
								do_end_pattern = True
						else:
							sub_el.events.append(SongComWaitTicks()) # a NOP, avoids timing issues.
							if not (effect.code in Song._sub_el_from_pattern.warned_uncomp_fxs):
								Song._sub_el_from_pattern.warned_uncomp_fxs.append(effect.code)
								print(f"\nWARNING: {effect.code.name} effect conversion isn't implemented and will be ignored")
									

			if i % 2 == 0: ticks_since_last_com += time_info.tick_time_1*time_info.time_base
			else:          ticks_since_last_com += time_info.tick_time_2*time_info.time_base
			if do_end_pattern: break

		utils.list_top(sub_el.events).timing += ticks_since_last_com
		
		# do_not_end_pattern is enabled by effects that
		# end the current pattern, in those cases adding
		# a return command would be useless
		if not do_end_pattern:
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
		Takes a volume in the YM2610 register range (they depend on the channel
		kind) and converts it into the global MLM volume range (0x00 ~ 0xFF)
		"""
		YM_VOL_SHIFTS = [3, 1, 4] # ADPCMA, FM, SSG
		return va << YM_VOL_SHIFTS[ch_kind]

	def mlmvol_to_ymvol(ch_kind: ChannelKind, va: int):
		"""
		Takes a volume in the global MLM volume range (0x00 ~ 0xFF) and 
		converts it into the YM2610 register range (depends on the channel)
		"""
		YM_VOL_SHIFTS = [3, 1, 4] # ADPCMA, FM, SSG
		return va >> YM_VOL_SHIFTS[ch_kind]

	def dmfnote_to_mlmnote(self, ch_kind: ChannelKind, note: int, octave: int):
		if note == 12: # C is expressed as 12 instead than 0
			note = 0
			if isinstance(octave, int): 
				octave += 1
			
		if ch_kind == ChannelKind.FM:
			return (note | (octave<<4)) & 0xFF
		elif ch_kind == ChannelKind.SSG:
			if octave < 2:
				self.notes_below_b2_present = True
				return 0
			return (octave-2)*12 + note
		else: # Channel kind is ADPCMA
			return note

	def dmfnote_to_ympitch(self, ch_kind: ChannelKind, note: int, octave: int):
		FM_PITCH_LUT = [
		#   C     C#     D      D#     E      F      F#     G    
			0x269, 0x28E, 0x2B5, 0x2DE, 0x30A, 0x338, 0x369, 0x39D,
		#   G#    A      A#     B
			0x3D4, 0x40E, 0x44C, 0x48D
		]
		SSG_BASE_PITCHES = [
		#   C2     C#2    D2     D#2    E2     F2
			65.41, 69.30, 73.42, 77.78, 82.41, 87.31,
		#   F#2    G2     G#2     A2     A#2     B2
			92.50, 98.00, 103.83, 110.0, 116.54, 123.47
		]

		if note == 12: # C is expressed as 12 instead than 0
			note = 0
			if isinstance(octave, int): 
				octave += 1
				
		if ch_kind == ChannelKind.FM:
			return FM_PITCH_LUT[note] | (octave << 1)
		elif ch_kind == ChannelKind.SSG:
			if octave < 2:
				self.notes_below_b2_present = True
				return 0
			pitch = base_pitch * pow(2,octave-2)
			return round(250000 / pitch)
		else: # Channel kind is ADPCMA
			return 0

	# Get pitch of the current note, the one below it and the one above it by 1 semitone
	def dmfnote_to_ympitch_range(self, ch_kind: ChannelKind, note: int, octave: int):
		lower_note = note - 1
		lower_octave = octave
		if lower_note < 0: 
			lower_note = 12 + lower_note
			lower_octave -= 1
		if octave < 0:
			lower_note = 0
			lower_octave = 0

		higher_note = note + 1
		higher_octave = octave
		if higher_note > 11: 
			higher_note = higher_note - 12
			higher_octave += 1

		middle_pitch = self.dmfnote_to_ympitch(ch_kind, note, octave)
		lower_pitch  = self.dmfnote_to_ympitch(ch_kind, lower_note, lower_octave)
		higher_pitch = self.dmfnote_to_ympitch(ch_kind, higher_note, higher_octave)

		return (middle_pitch, lower_pitch, higher_pitch)

	def compile(self) -> bytearray:
		"""
		Returns the compiled address and the song offset
		in a tuple, in that order.
		"""
		comp_data = bytearray()

		self.symbols.define_sym("HEADER", len(comp_data))
		comp_header_data = self.compile_header(len(comp_data))
		comp_data.extend(comp_header_data)

		self.symbols.define_sym("INSTRUMENTS", len(comp_data))
		comp_inst_data = self.compile_instruments(len(comp_data))
		comp_data.extend(comp_inst_data)

		comp_odata = self.compile_other_data(len(comp_data))
		comp_data.extend(comp_odata)

		for i in range(dmf.SYSTEM_TOTAL_CHANNELS):
			if self.channels[i] != None:
				el_sym_name = self.channels[i].get_sym_name(i)
				jsel_count = 0

				self.symbols.define_sym(el_sym_name, len(comp_data))
				for event in self.channels[i].events:
					if isinstance(event, SongComJumpToSubEL):
						sym_name = "JSEL:CH{0:01X};{1:02X}".format(i, jsel_count)
						self.symbols.define_sym(sym_name, len(comp_data))
						jsel_count += 1
					comp_data.extend(event.compile(i, self.symbols, len(comp_data)))

				comp_subel_data = self.compile_sub_els(i, len(comp_data))
				comp_data.extend(comp_subel_data)
		
		return comp_data

	def compile_other_data(self, head_ofs: int) -> (bytearray, dict):
		"""
		Returns compiled other data and a symbol table
		"""
		comp_data = bytearray()

		for i in range(len(self.other_data)):
			sym_name = OtherDataIndex(i).get_sym_name()
			self.symbols.define_sym(sym_name, head_ofs)

			comp_odata = self.other_data[i].compile()
			comp_data.extend(comp_odata)
			head_ofs += len(comp_odata)

		return comp_data

	def compile_instruments(self, head_ofs: int) -> bytearray:
		comp_data = bytearray()

		for inst in self.instruments:
			inst_data = inst.compile(self.symbols, head_ofs + len(comp_data))
			comp_data.extend(inst_data)

		return comp_data

	def compile_sub_els(self, ch: int, head_ofs: int) -> (bytearray, dict):
		"""
		Returns compiled other data and a new symbol table
		"""
		comp_data = bytearray()
		pos_jump_count = 0

		for i in range(len(self.sub_event_lists[ch])):
			subel = self.sub_event_lists[ch][i]
			sym_name = subel.get_sym_name(ch, i)
			self.symbols.define_sym(sym_name, head_ofs + len(comp_data))

			# Compile SubEL
			for event in subel.events:
				comp_event = event.compile(ch, self.symbols, head_ofs + len(comp_data))
				comp_data.extend(comp_event)

		return comp_data

	def compile_header(self, head_ofs: int) -> bytearray:
		comp_data = bytearray()

		for i in range(len(self.channels)):
			if self.channels[i] == None:
				comp_data.append(0x00) # LSB
				comp_data.append(0x00) # MSB
			else:
				sym_name = self.channels[i].get_sym_name(i)
				self.symbols.add_sym_ref(sym_name, head_ofs + len(comp_data))
				comp_data.append(0xFF) # LSB (Placeholder)
				comp_data.append(0xFF) # MSB (Placeholder)

		comp_data.append(self.tma_counter & 0xFF) # TMA LSB
		comp_data.append(self.tma_counter >> 8)   # TMA MSB
		comp_data.append(self.time_base)          # Base time

		self.symbols.add_sym_ref("INSTRUMENTS", head_ofs + len(comp_data))
		comp_data.append(0xFF) # Inst. LSB (Placeholder)
		comp_data.append(0xFF) # Inst. MSB (Placeholder)

		return comp_data

	def replace_symbols(self, comp_song: bytearray, def_addr_ofs = 0) -> bytearray:
		for sym_name, addrs in self.symbols.items():
			for ref_addr in addrs[1]:
				offset_def_addr = utils.wrap_rom_to_mlm_addr(addrs[0] + def_addr_ofs)
				comp_song[ref_addr]   = offset_def_addr & 0xFF
				comp_song[ref_addr+1] = offset_def_addr >> 8
		return comp_song
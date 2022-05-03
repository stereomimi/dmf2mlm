import itertools
from ..defs import *
from ..sym_table import *
from .. import utils
from dataclasses import dataclass
from typing import Optional

######################## EVENT & NOTES ########################

class SongEvent:
	timing: int = 0

	def _compile_timing(self, ticks = None) -> bytearray:
		comp_data = bytearray()
		if ticks == None:
			t = self.timing
		else:
			t = ticks
			
		while (t > 0):
			if t > 0x10:
				comp_data.append(0x03)         # Wait byte command
				comp_data.append((t-1) & 0xFF) # ticks 
				t -= 0x100
			elif t > 0:
				comp_data.append(0x10 | ((t-1) & 0x0F)) # Wait nibble command
				t -= 0x10

		return comp_data

	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = self._compile_timing()
		return comp_data

@dataclass
class SongNote(SongEvent):
	note: int # Can also be a sample id in ADPCM channels

	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray(2)
		t = self.timing

		comp_data[0] = 0x80 | utils.clamp(t, 0, 0x7F)
		comp_data[1] = self.note
		t -= 0x7F
		comp_data.extend(self._compile_timing(t))

		return comp_data

######################## COMMANDS ########################

@dataclass
class SongCommand(SongEvent):
	pass

@dataclass
class SongComEOEL(SongCommand):
	"""
	Song Command End of Event List
	------------------------------
	ends the playback for the current channel
	"""
	
	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray()

		comp_data.extend(self._compile_timing())
		comp_data.append(0x00) # End of EL command
		return comp_data

@dataclass
class SongComNoteOff(SongCommand):
	"""
	Song Command Note Off
	------------------------------
	Stops the channel's playing note/sample
	"""
	
	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray(2)
		t = self.timing

		comp_data[0] = 0x01     # Note off command
		comp_data[1] = t & 0xFF
		t -= 0xFF
		comp_data.extend(self._compile_timing(t))

		return comp_data

@dataclass
class SongComChangeInstrument(SongCommand):
	"""
	Song Command Change Instrument
	------------------------------
	Changes selected instrument
	"""
	instrument: int

	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray(2)

		comp_data[0] = 0x02            # Change instrument command
		comp_data[1] = self.instrument
		comp_data.extend(self._compile_timing())

		return comp_data

@dataclass
class SongComWaitTicks(SongCommand):
	"""
	Song Command Wait Ticks
	------------------------------
	Just waits the specified amount,
	it will occupy 1, 2 or 3 bytes depending 
	on how much ticks need to be waited
	"""

@dataclass
class SongComSetChannelVol(SongCommand):
	"""
	Song Command Set Channel Volume
	------------------------------
	Sets the channel's volume
	"""
	volume: int

	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray()

		if ch < 0x0A: # FM & ADPCMA
			comp_data.append(0x05)        # Set channel volume command
			comp_data.append(self.volume)
			comp_data.extend(self._compile_timing())
		else:
			comp_data.append(0x30 | (self.volume >> 4))
			comp_data.extend(self._compile_timing())

		return comp_data

@dataclass
class SongComSetPanning(SongCommand):
	"""
	Song Command Set Panning
	------------------------------
	Set's the ADPCM-A master volume
	"""
	panning: int

	def from_dffx(value: int):
		p = 0
		if   value == 0x01: p = int(Panning.RIGHT)
		elif value == 0x10: p = int(Panning.LEFT)
		elif value == 0x11: p = int(Panning.CENTER)
		return SongComSetPanning(p)

	def compile(self, ch, _symbols, _head_ofs):
		comp_data = bytearray(2)
		t = self.timing
		
		comp_data[0] = 0x06           # Set panning command
		comp_data[1] = (t & 0x3F) | self.panning
		t -= 0x3F
		comp_data.extend(self._compile_timing(t))

		return comp_data

@dataclass
class SongComJumpToSubEL(SongCommand):
	"""
	Song Command Jump to Sub Event List
	------------------------------
	Jumps to sub event list. Doesn't allow nesting.
	"""
	sub_el_idx: int # index to Song.sub_event_lists

	def compile(self, ch: int, symbols: SymbolTable, head_ofs: int) -> bytearray:
		comp_data = bytearray()
		comp_data.extend(self._compile_timing())
		comp_data.append(0x09) # Jump to SubEL command

		sym_name = "SUBEL:CH{0:01X};{1:02X}".format(ch, self.sub_el_idx)
		symbols.add_sym_ref(sym_name, head_ofs + len(comp_data))
		comp_data.append(0xFF) # SubEL addr LSB (Placeholder)
		comp_data.append(0xFF) # SubEL addr MSB (Placeholder)
		return comp_data

@dataclass
class SongComPositionJump(SongCommand):
	"""
	Song Command Position Jump
	------------------------------
	Jumps to a specific event in the current event list.
	It can be 2 bytes long (using an offset) or 3 bytes
	long (using a fixed address) depending on the size
	of the jump.
	"""
	jsel_idx: int # Which Jump To SubEL command it jumps to

	def from_dffx(value: int):
		return SongComPositionJump(value)

	def compile(self, ch: int, symbols: SymbolTable, head_ofs: int) -> bytearray:
		comp_data = bytearray()
		comp_data.extend(self._compile_timing())
		comp_data.append(0x23) # Reset pitch slide
		comp_data.append(0x0B) # Position jump command
		
		sym_name = "JSEL:CH{0:01X};{1:02X}".format(ch, self.jsel_idx)
		symbols.add_sym_ref(sym_name, head_ofs + len(comp_data))
		comp_data.append(0xFF) # Dest. Addr LSB (Placeholder)
		comp_data.append(0xFF) # Dest. Addr MSB (Placeholder)
		return comp_data

class SongComYM2610PortWriteA(SongCommand):
	"""
	Song Command YM2610 Port Write A
	------------------------------
	Directly writes to the YM2610 registers
	using port A
	"""
	address: int
	data: int

class SongComYM2610PortWriteB(SongCommand):
	"""
	Song Command YM2610 Port Write B
	------------------------------
	Directly writes to the YM2610 registers
	using port B
	"""
	address: int
	data: int

class SongComSetTimerAFreq(SongCommand):
	"""
	Song Command Set Timer A Frequency
	------------------------------
	Sets the frequency of timer a
	"""
	frequency: int

@dataclass
class SongComReturnFromSubEL(SongCommand):
	"""
	Song Command Return from Sub Event List
	------------------------------
	Returns from Sub event list
	"""
	
	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray()

		comp_data.extend(self._compile_timing())
		comp_data.append(0x20) # Return from SubEL command
		return comp_data

@dataclass
class SongComPitchUpwardSlide(SongCommand):
	"""
	Song Command Pitch Upward Slide
	------------------------------
	Sets Upward Pitch slide
	"""
	ofs: int

	def from_dffx(value: int):
		return SongComPitchUpwardSlide(value)

	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray()

		if self.ofs > 0:
			comp_data.append(0x21) # Pitch upward slide command
			comp_data.append(self.ofs)
		else:
			comp_data.append(0x23) # Reset pitch slide command

		comp_data.extend(self._compile_timing())
		return comp_data

@dataclass
class SongComPitchDownwardSlide(SongCommand):
	"""
	Song Command Pitch Downward Slide
	------------------------------
	Sets Downward Pitch slide
	"""
	ofs: int

	def from_dffx(value: int):
		return SongComPitchDownwardSlide(value)

	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray()

		if self.ofs > 0:
			comp_data.append(0x22) # Pitch downward slide command
			comp_data.append(self.ofs)
		else:
			comp_data.append(0x23) # Reset pitch slide command

		comp_data.extend(self._compile_timing())
		return comp_data

@dataclass
class SongComFMTL1Set(SongCommand):
	"""
	Song Command FM TL OP1 Set
	------------------------------
	Sets FM OP1's TL 
	"""
	tl: int

	def from_dffx(value: int):
		return SongComFMTL1Set(value)

	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray(2)

		comp_data[0] = 0x24 # Set FM OP1 TL Command
		comp_data[1] = self.tl
		comp_data.extend(self._compile_timing())

		return comp_data

@dataclass
class SongComFMTL2Set(SongCommand):
	"""
	Song Command FM TL OP2 Set
	------------------------------
	Sets FM OP2's TL 
	"""
	tl: int

	def from_dffx(value: int):
		return SongComFMTL2Set(value)
		
	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray(2)

		comp_data[0] = 0x25 # Set FM OP2 TL Command
		comp_data[1] = self.tl
		comp_data.extend(self._compile_timing())

		return comp_data

@dataclass
class SongComFMTL3Set(SongCommand):
	"""
	Song Command FM TL OP3 Set
	------------------------------
	Sets FM OP3's TL 
	"""
	tl: int

	def from_dffx(value: int):
		return SongComFMTL3Set(value)
		
	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray(2)

		comp_data[0] = 0x26 # Set FM OP3 TL Command
		comp_data[1] = self.tl
		comp_data.extend(self._compile_timing())

		return comp_data

@dataclass
class SongComFMTL4Set(SongCommand):
	"""
	Song Command FM TL OP4 Set
	------------------------------
	Sets FM OP4's TL 
	"""
	tl: int

	def from_dffx(value: int):
		return SongComFMTL4Set(value)
		
	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray(2)

		comp_data[0] = 0x27 # Set FM OP4 TL Command
		comp_data[1] = self.tl
		comp_data.extend(self._compile_timing())

		return comp_data
	
@dataclass
class SongComOffsetChannelVol(SongCommand):
	"""
	Song Command Set Channel Volume
	------------------------------
	Offsets the channel's volume in ranges
	inbetween -8~-1 and 1~8. It's shorter than
	setting the volume directly.
	"""
	volume_offset: int

	def compile(self, ch: int, _symbols, _head_ofs) -> bytearray:
		comp_data = bytearray()

		if ch >= 0x0A:
			raise RuntimeError("SongComOffsetChannelVol is incompatible with SSG")
		if self.volume_offset < -8 or self.volume_offset > 8 or self.volume_offset == 0:
			raise RuntimeError("Invalid volume offset")
		ofs_nibble = utils.clamp(abs(self.volume_offset), 1, 8) - 1
		if self.volume_offset < 0: ofs_nibble |= 8 # Set sign bit to negative
		comp_data.append(0x30 | ofs_nibble)

		comp_data.extend(self._compile_timing())
		return comp_data
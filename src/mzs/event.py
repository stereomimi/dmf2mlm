from ..defs import *
from dataclasses import dataclass

######################## EVENT & NOTES ########################

class SongEvent:
	timing: int = 0

@dataclass
class SongNote(SongEvent):
	note: int # Can also be a sample id in ADPCM channels


######################## COMMANDS ########################

@dataclass
class SongCommand(SongEvent):
	pass

class SongComEOEL(SongCommand):
	"""
	Song Command End of Event List
	------------------------------
	ends the playback for the current channel
	"""
	pass

@dataclass
class SongComNoteOff(SongCommand):
	"""
	Song Command Note Off
	------------------------------
	Stops the channel's playing note/sample
	"""
	pass

@dataclass
class SongComChangeInstrument(SongCommand):
	"""
	Song Command Change Instrument
	------------------------------
	Changes selected instrument
	"""
	instrument: int

@dataclass
class SongComWaitTicks(SongCommand):
	"""
	Song Command Wait Ticks
	------------------------------
	Just waits the specified amount,
	it will occupy 1, 2 or 3 bytes depending 
	on how much ticks need to be waited
	"""
	pass

class SongComSetChannelVol(SongCommand):
	"""
	Song Command Set Channel Volume
	------------------------------
	Sets the channel's volume
	"""
	volume: int

class SongComSetPanning(SongCommand):
	"""
	Song Command Set Panning
	------------------------------
	Set's the ADPCM-A master volume
	"""
	panning: Panning

@dataclass
class SongComJumpToSubEL(SongCommand):
	"""
	Song Command Jump to Sub Event List
	------------------------------
	Jumps to sub event list. Doesn't allow nesting.
	"""
	sub_el_idx: int # index to Song.sub_event_lists

class SongComPositionJump(SongCommand):
	"""
	Song Command Position Jump
	------------------------------
	Jumps to a specific event in the current event list.
	It can be 2 bytes long (using an offset) or 3 bytes
	long (using a fixed address) depending on the size
	of the jump
	"""
	event_idx: int

class SongComPortamentoSlide(SongCommand):
	"""
	Song Command Portamento Slide
	------------------------------
	Still not implemented
	"""
	pitch_offset: int

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
	pass

from event import *
from enum import Enum, IntEnum

######################## SONGS ########################

class SongChannel:
	event_list: [SongEvent]

class Song:
	channels: [SongChannel]
	sub_event_lists: [[SongEvent]]


######################## OTHER DATA ########################

class OtherDataIndex(int):
	pass

class OtherData:
	pass

class SampleList(OtherData):
	start_addresses: [int]
	end_addresses: [int]

class SSGMacro(OtherData):
	length: int
	loop_point: int
	data: bytearray
	
######################## INSTRUMENTS ########################

class Instrument:
	pass

class ADPCMAInstrument(Instrument):
	sample_list: OtherDataIndex

class FMOperator:
	dtmul: int
	tl: int
	ksar: int
	amdr: int
	sr: int
	slrr: int
	eg: int

class FMInstrument(Instrument):
	fbalgo: int
	amspms: int
	op_enable: [bool] # [OP1, OP2, OP3, OP4] Enable
	operators: [FMOperator]

class SSGMixing(IntEnum):
	NONE  = 0
	TONE  = 1
	NOISE = 2
	BOTH  = 3

class SSGInstrument(Instrument):
	mixing: SSGMixing
	eg_enable: bool
	volenv_period_fine_tune: int
	volenv_period_coarse_tune: int
	volenv_shape: int
	mix_macro: OtherDataIndex
	vol_macro: OtherDataIndex
	arp_macro: OtherDataIndex

######################## SOUND DATA ########################

class SoundData:
	"""
	Contains everything to reproduce music and sound effects.
	Basically anything in the m1rom that isn't code nor LUTs.
	"""

	songs: [Song]
	instruments: [Instrument]
	other_data: [OtherData]
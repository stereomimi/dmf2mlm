from enum import Enum, IntEnum

MLM_INSTRUMENT_SIZE = 32

class Panning(IntEnum):
	NONE   = 0x00
	RIGHT  = 0x40
	LEFT   = 0x80
	CENTER = 0xC0

class ChannelKind(IntEnum):
	ADPCMA = 0
	FM     = 1
	SSG    = 2
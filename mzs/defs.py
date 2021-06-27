from enum import Enum, IntEnum

class Panning(IntEnum):
	NONE   = 0x00
	RIGHT  = 0x40
	LEFT   = 0x80
	CENTER = 0xC0
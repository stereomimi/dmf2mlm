from event import *

######################## SONGS ########################


class SongChannel:
	event_list: [SongEvent]

class Song:
	channels: [SongChannel]
	sub_event_lists: [[SongEvent]]

######################## SOUND DATA ########################

class SoundData:
	"""
	Contains everything to reproduce music and sound effects.
	Basically anything in the m1rom that isn't code nor LUTs.
	"""

	songs: [Song]
	instruments: [Instrument]
	other_data: [OtherData]
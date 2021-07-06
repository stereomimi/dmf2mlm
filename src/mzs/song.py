from .instrument import *
from .other_data import *
from .event import *
from .. import dmf

class EventList:
	events: [SongEvent]
	is_sub: bool
	
class Song:
	channels: [EventList]
	sub_event_lists: [EventList]
	instruments: [Instrument]
	other_data: [OtherData]
	tma_counter: int

	def __init__(self):
		self.channels = []
		self.sub_event_lists = []
		self.instruments = []
		self.other_data = []
		self.tma_counter = 0
		for _ in range(dmf.SYSTEM_TOTAL_CHANNELS):
			self.channels.append([])

	def from_dmf(module: dmf.Module):
		self = Song()

		return self
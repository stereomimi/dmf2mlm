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
		self._instruments_from_dmf(module)
		return self

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
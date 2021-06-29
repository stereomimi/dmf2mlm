from dmf import *
from mzs.defs import *

class MultiModule:
	"""
	Class containing the data of various DMF Modules.
	"""

	# system: System # runs on the NeoGeo by default
	pattern_matrixes: [PatternMatrix]
	instruments: [Instrument]
	patterns: [[Pattern]] # patterns[channel_kind][id]
	samples: [Sample]

	def __init__(self, modules: [Module]):
		pass

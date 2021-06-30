from dmf import *
from mzs.defs import *

class MultiModule:
	"""
	Class containing the data of various DMF Modules.
	"""

	# system: System # runs on the NeoGeo by default
	time_infos: [TimeInfo]
	pattern_matrixes: [PatternMatrix]
	instruments: [Instrument]
	patterns: [[Pattern]] # patterns[channel][id]
	samples: [Sample]

	pattern_ofs_matrix: [[int]] # pattern_ofs_matrix[module][channel]

	def __init__(self, modules: [Module]):
		self.merge_time_infos(modules)
		self.merge_patterns(modules)

	def merge_time_infos(self, modules: [Module]):
		self.time_infos = []
		for mod in modules:
			self.time_infos.append(mod.time_info)

	def merge_patterns(self, modules: [Module]):
		self.patterns = []
		self.pattern_ofs_matrix = []
		pattern_counts = []

		for _ in range(SYSTEM_TOTAL_CHANNELS):
			self.patterns.append([])
			pattern_counts.append(0)

		for mod in modules:
			mod_pattern_offsets = []

			for ch in range(SYSTEM_TOTAL_CHANNELS):
				mod_pattern_offsets.append(pattern_counts[ch])
				for pat in mod.patterns[ch]:
					self.patterns[ch].append(pat)
					pattern_counts[ch] += 1

			self.pattern_ofs_matrix.append(mod_pattern_offsets)

		print(self.pattern_ofs_matrix)
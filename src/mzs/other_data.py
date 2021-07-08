from .. import dmf, utils

class OtherDataIndex(int):
	pass

class OtherData:
	pass

class SampleList(OtherData):
	start_addresses: [int]
	end_addresses: [int]

	def __init__(self):
		self.start_addresses = []
		self.end_addresses = []

	def print(self):
		print("start_addresses:", self.start_addresses)
		print("end_addresses:", self.end_addresses)

class SSGMacro(OtherData):
	data: bytearray
	loop_position: int

	def from_dmf_macro(dmacro: dmf.STDMacro, el_size: str):
		macro_val_count = len(dmacro.envelope_values)
		if macro_val_count == 0:
			return None

		self = SSGMacro()
		if not dmacro.loop_enabled:
			self.loop_position = 0xFF
		else:
			self.loop_position = dmacro.loop_position

		if el_size == "byte" or macro_val_count == 1:
			self.data = bytearray(map(utils.signed2unsigned_8, dmacro.envelope_values))
		elif el_size == "nibble":
			self.data = bytearray()
			for i in range(0, macro_val_count, 2):
				byte = dmacro.envelope_values[i]
				byte |= dmacro.envelope_values[i+1] << 4
				self.data.append(byte)
		else:
			raise RuntimeError("Invalid MZS SSG Macro element size")

		return self

	def print(self):
		print("data:", list(self.data))
		print("loop_position:", self.loop_position)
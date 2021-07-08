from .. import dmf

class OtherDataIndex(int):
	pass

class OtherData:
	pass

class SampleList(OtherData):
	start_addresses: [int]
	end_addresses: [int]

class SSGMacro(OtherData):
	data: bytearray
	loop_position: int

	def from_dmf_macro(dmacro: dmf.STDMacro, el_size: str):
		macro_val_count = len(dmacro.envelope_values)
		if macro_val_count == 0:
			return None

		self = SSGMacro()
		if not dmacro.loop_enabled:
			self.loop_point = 0xFF
		else:
			self.loop_point = dmacro.loop_position

		if el_size == "nibble":
			self.data = bytearray()
			for i in range(0, macro_val_count, 2):
				byte = dmacro.envelope_values[i]
				byte |= dmacro.envelope_values[i+1] << 4
				self.data.append(byte)

		elif el_size == "byte":
			self.data = bytearray(dmacro.envelope_values)

		else:
			raise RuntimeError("Invalid MZS SSG Macro element size")

		return self
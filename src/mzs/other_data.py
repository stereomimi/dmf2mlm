from .. import dmf, utils

class OtherDataIndex(int):
	def get_sym_name(self):
		return "ODATA:{0:08X}".format(self)

class OtherData:
	pass

class SampleList(OtherData):
	addresses: [(int, int)]

	def __init__(self, sample_addresses=[]):
		self.addresses = sample_addresses # [(start_addr, end_addr), ...]

	def compile(self) -> bytearray:
		smp_count = len(self.addresses)
		comp_data: bytearray

		if smp_count > 0:
			comp_data = bytearray(smp_count * 4 + 1)
			comp_data[0] = smp_count
			for i in range(smp_count):
				comp_data[i*4 + 1] = self.addresses[i][0] & 0xFF # Start LSB
				comp_data[i*4 + 2] = self.addresses[i][0] >> 8   # Start MSB
				comp_data[i*4 + 3] = self.addresses[i][1] & 0xFF # End LSB
				comp_data[i*4 + 4] = self.addresses[i][1] >> 8   # End MSB
		else: 
			comp_data = bytearray([0x00]) # zero-filled

		return comp_data

class SSGMacro(OtherData):
	length: int
	loop_position: int
	data: bytearray

	def from_dmf_macro(dmacro: dmf.STDMacro, kind: str):
		macro_val_count = len(dmacro.envelope_values)
		if macro_val_count == 0:
			return None

		self = SSGMacro()
		if not dmacro.loop_enabled:
			self.loop_position = 0xFF
		else:
			self.loop_position = dmacro.loop_position

		if kind == "arp" or macro_val_count == 1:
			self.data = bytearray(map(utils.signed2unsigned_8, dmacro.envelope_values))
			self.length = len(self.data)

		elif kind == "vol":
			self.data = bytearray()
			for i in range(0, macro_val_count, 2):
				byte = dmacro.envelope_values[i]
				byte |= dmacro.envelope_values[i+1] << 4
				self.data.append(byte)
			self.length = len(self.data) * 2

		elif kind == "mix":
			self.data = bytearray()
			for i in range(0, macro_val_count, 2):
				byte = dmacro.envelope_values[i] + 1
				byte |= (dmacro.envelope_values[i+1] + 1) << 4
				self.data.append(byte)
			self.length = len(self.data) * 2
			
		else:
			raise RuntimeError("Invalid MZS SSG Macro element size")

		return self

	def compile(self) -> bytearray:
		comp_data = bytearray(2)
		comp_data[0] = self.length - 1
		comp_data[1] = self.loop_position
		comp_data.extend(self.data)
		return comp_data
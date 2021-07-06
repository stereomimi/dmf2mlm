class OtherDataIndex(int):
	pass

class OtherData:
	pass

class SampleList(OtherData):
	start_addresses: [int]
	end_addresses: [int]

class SSGMacro(OtherData):
	length: int
	loop_point: int
	data: bytearray
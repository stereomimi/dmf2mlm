# Thank you Freem for the ADPCMA tool that can be found
# here https://github.com/freem/adpcma

import os

class ADPCMAEncoder:
	# Buffers
	buffer: bytes        # Input buffer
	out_buffer: bytes    # Output buffer
	
	cmd_name: str
	def __init__(self, cmd_name="adpcma"):
		self.cmd_name = cmd_name

	def ym_encode(self):
		with open("tmp.pcm", "wb") as file:
			file.write(self.buffer)
			code = os.system(f"{self.cmd_name} {file.name} tmp.pcma")
			if code != 0x00:
				raise RuntimeError("Error while running ADPCM-A Encoder")
		
		with open("tmp.pcma", "rb") as file:
			self.out_buffer = file.read()

		os.remove("tmp.pcm")
		os.remove("tmp.pcma")

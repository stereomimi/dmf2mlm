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
		PCM_FILE_NAME  = "tmp.pcm"
		PCMA_FILE_NAME = "tmp.pcma"

		with open(PCM_FILE_NAME, "wb") as file:
			file.write(self.buffer)
			file.flush()
			code = os.system(f"{self.cmd_name} {PCM_FILE_NAME} {PCMA_FILE_NAME} > /dev/null")
			if code != 0x00:
				raise RuntimeError("Error while running ADPCM-A Encoder")
		
		with open(PCMA_FILE_NAME, "rb") as file:
			self.out_buffer = file.read()

		os.remove(PCM_FILE_NAME)
		os.remove(PCMA_FILE_NAME)

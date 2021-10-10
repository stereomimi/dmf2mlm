from math import *
from .pa_encoder import *
from .. import dmf,utils

class Sample:
	data: bytearray # Size is always divisible by 256 bytes

	def from_dmf_sample(dsmp: dmf.Sample):
		#PA_PAD_CHAR = b'\x80'
		#if dsmp.bits != 16: 
		#	raise RuntimeError("Uncompatible sample (sample width isn't 16)")
		if dsmp.pitch != 0:     dsmp.apply_pitch()
		if dsmp.amplitude != 0: dsmp.apply_amplitude()

		pa_encoder = ADPCMAEncoder()
		in_buffer = bytearray()
		for short in dsmp.data:
			short = utils.signed2unsigned_16(short)
			in_buffer.append(short & 0xFF)
			in_buffer.append(short >> 8)
		out_buffer = pa_encoder.ym_encode_pcm(in_buffer)

		sample = Sample()
		sample.data = out_buffer # The sample data is already padded by the converter
		#sample.data = sample.data.ljust(ceil(len(sample.data) / 256), PA_PAD_CHAR)
		return sample

	def from_wav(wav_path):
		pa_encoder = ADPCMAEncoder()
		sample = Sample()
		sample.data = bytearray(pa_encoder.ym_encode_path(wav_path))
		return sample

	def __str__(self):
		return f"Sample (size: {len(self.data)})"
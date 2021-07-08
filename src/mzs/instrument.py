from .other_data import *
from enum import Enum, IntEnum
from typing import Optional
from .. import dmf, utils

class Instrument:
	pass

class ADPCMAInstrument(Instrument):
	sample_list: OtherDataIndex

class FMOperator:
	dtmul: int
	tl: int
	ksar: int
	amdr: int
	sr: int
	slrr: int
	eg: int

	def from_dmf_op(dmfop: dmf.FMOperator):
		self = FMOperator()
		self.dtmul = dmfop.mult | (utils.signed2unsigned_3(dmfop.dt)<<4)
		self.tl = dmfop.tl
		self.ksar = dmfop.ar | (dmfop.rs<<6)
		self.amdr = dmfop.dr | (int(dmfop.am)<<7)
		self.sr = dmfop.d2r
		self.slrr = dmfop.rr | (dmfop.sl<<4)
		self.eg = dmfop.ssg_mode | (int(dmfop.ssg_enabled)<<3)
		return self

	def print(self):
		print("\tdtmul: 0x{0:02X}".format(self.dtmul))
		print("\ttl:    0x{0:02X}".format(self.tl))
		print("\tksar:  0x{0:02X}".format(self.ksar))
		print("\tamdr:  0x{0:02X}".format(self.amdr))
		print("\tsr:    0x{0:02X}".format(self.sr))
		print("\tslrr:  0x{0:02X}".format(self.slrr))
		print("\teg:    0x{0:02X}".format(self.eg))

class FMInstrument(Instrument):
	fbalgo: int
	amspms: int
	op_enable: [bool] # [OP1, OP2, OP3, OP4] Enable
	operators: [FMOperator]

	def __init__(self):
		self.operators = []

	def from_dmf_inst(dinst: dmf.FMInstrument):
		self = FMInstrument()
		self.fbalgo = dinst.algorithm | (dinst.feedback<<3)
		self.amspms = dinst.fms | (dinst.ams<<4)
		self.op_enable = [True, True, True, True] # All enabled by default

		for dop in dinst.operators:
			self.operators.append(FMOperator.from_dmf_op(dop))
		return self

	def print(self):
		print("fbalgo: 0x{0:02X}".format(self.fbalgo))
		print("amspms: 0x{0:02X}".format(self.amspms))
		print("op_enable:", self.op_enable)
		print("operators:")

		for i in range(len(self.operators)):
			print(f"Operator {i+1}:")
			self.operators[i].print()


class SSGMixing(IntEnum):
	NONE  = 0
	TONE  = 1
	NOISE = 2
	BOTH  = 3

class SSGInstrument(Instrument):
	mixing: SSGMixing
	#eg_enable: bool             
	#volenv_period_fine_tune: int
	#volenv_period_coarse_tune: int
	#volenv_shape: int
	mix_macro: Optional[OtherDataIndex]
	vol_macro: Optional[OtherDataIndex]
	arp_macro: Optional[OtherDataIndex]

	def __init__(self):
		self.mix_macro = None
		self.vol_macro = None
		self.arp_macro = None

	def from_dmf_inst(dinst: dmf.STDInstrument, odata_count: int):
		self = SSGInstrument()
		self.mixing = SSGInstrument._get_mix_from_dinst(dinst)
		mix_odata = SSGMacro.from_dmf_macro(dinst.chmode_macro, "nibble")
		vol_odata = SSGMacro.from_dmf_macro(dinst.volume_macro, "nibble")
		arp_odata = SSGMacro.from_dmf_macro(dinst.arpeggio_macro, "byte")

		new_odata = []
		if mix_odata != None:
			new_odata.append(mix_odata)
			self.mix_macro = odata_count
			odata_count += 1
		if vol_odata != None:
			new_odata.append(vol_odata)
			self.vol_macro = odata_count
			odata_count += 1
		if arp_odata != None:
			new_odata.append(arp_odata)
			self.arp_macro = odata_count
			odata_count += 1

		return (self, new_odata)
		
	def _get_mix_from_dinst(dinst: dmf.STDInstrument):
		mix_macro_len = len(dinst.chmode_macro.envelope_values)
		if mix_macro_len == 0:
			return SSGMixing.TONE
		base_mix = SSGMixing(dinst.chmode_macro.envelope_values[0]+1)
		return base_mix

	def print(self):
		print("mix:", self.mixing)
		print("mix macro:", self.mix_macro)
		print("vol macro:", self.vol_macro)
		print("arp macro:", self.arp_macro)
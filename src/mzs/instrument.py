from .other_data import *
from enum import Enum, IntEnum
from typing import Optional
from .. import dmf, utils
from ..defs import *

class Instrument:
	pass

class ADPCMAInstrument(Instrument):
	sample_list: OtherDataIndex

	def __init__(self, sample_list=None):
		if sample_list != None:
			self.sample_list = OtherDataIndex(sample_list)

	def compile(self, symbols: dict) -> bytearray:
		comp_data = bytearray(MLM_INSTRUMENT_SIZE)
		smp_list_addr = symbols[self.sample_list.get_sym_name()]

		comp_data[0] = smp_list_addr & 0xFF
		comp_data[1] = smp_list_addr >> 8
		return comp_data

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

	def compile(self) -> bytearray:
		FM_OPERATOR_SIZE = 7
		comp_data = bytearray(FM_OPERATOR_SIZE)

		comp_data[0] = self.dtmul 
		comp_data[1] = self.tl 
		comp_data[2] = self.ksar 
		comp_data[3] = self.amdr 
		comp_data[4] = self.sr 
		comp_data[5] = self.slrr 
		comp_data[6] = self.eg 

		return comp_data

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

	def compile(self, symbols: dict) -> bytearray:
		comp_data = bytearray(3) # FBALGO, AMSPMS, OP ENABLE
		comp_data[0] = self.fbalgo
		comp_data[1] = self.amspms

		for i in range(len(self.op_enable)):
			comp_data[2] |= self.op_enable[i] << (i+4)
		for op in self.operators:
			comp_data.extend(op.compile())

		comp_data.append(0) # Padding
		return comp_data

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
			self.mix_macro = OtherDataIndex(odata_count)
			odata_count += 1
		if vol_odata != None:
			new_odata.append(vol_odata)
			self.vol_macro = OtherDataIndex(odata_count)
			odata_count += 1
		if arp_odata != None:
			new_odata.append(arp_odata)
			self.arp_macro = OtherDataIndex(odata_count)
			odata_count += 1

		return (self, new_odata)
		
	def _get_mix_from_dinst(dinst: dmf.STDInstrument):
		mix_macro_len = len(dinst.chmode_macro.envelope_values)
		if mix_macro_len == 0:
			return SSGMixing.TONE
		base_mix = SSGMixing(dinst.chmode_macro.envelope_values[0]+1)
		return base_mix

	def compile(self, symbols: dict) -> bytearray:
		comp_data = bytearray(MLM_INSTRUMENT_SIZE)
		comp_data[0] = int(self.mixing)
		comp_data[1] = 0 # EG Enable

		macros = [self.mix_macro, self.vol_macro, self.arp_macro]
		for i in range(len(macros)):
			if macros[i] == None:
				comp_data[5 + i*2]     = 0x00 # Macro ptr LSB (NULL)
				comp_data[5 + i*2 + 1] = 0x00 # Macro ptr MSB (NULL)
			else:
				macro_ptr = symbols[macros[i].get_sym_name()]
				comp_data[5 + i*2]     = macro_ptr & 0xFF # Macro ptr LSB 
				comp_data[5 + i*2 + 1] = macro_ptr >> 8   # Macro ptr MSB
		
		return comp_data
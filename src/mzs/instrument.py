from .other_data import *
from enum import Enum, IntEnum
from .. import dmf

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
		self.dtmul = dmfop.mul | (dmfop.dt<<4)
		self.tl = dmfop.tl
		self.ksar = dmfop.ar | (dmfop.rs<<6)
		self.amdr = dmfop.dr | (int(dmfop.am)<<7)
		self.sr = dmfop.d2r
		self.slrr = dmfop.rr | (dmfop.sl<<4)
		self.eg = dmfop.ssg_mode | (int(dmfop.ssg_enabled)<<3)
		return self

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
		self.amspms = dinst.pms | (dinst.ams<<4)
		self.op_enable = [True, True, True, True] # All enabled by default

		for dop in dinst.operators:
			self.operators.append(FMOperator.from_dmf_op(dop))
		return self


class SSGMixing(IntEnum):
	NONE  = 0
	TONE  = 1
	NOISE = 2
	BOTH  = 3

class SSGInstrument(Instrument):
	mixing: SSGMixing
	eg_enable: bool
	volenv_period_fine_tune: int
	volenv_period_coarse_tune: int
	volenv_shape: int
	mix_macro: OtherDataIndex
	vol_macro: OtherDataIndex
	arp_macro: OtherDataIndex
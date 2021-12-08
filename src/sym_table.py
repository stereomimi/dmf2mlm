class SymbolTable:
	_symbols: {}

	def __init__(self):
		self._symbols = {}

	def __contains__(self, key):
		return key in self._symbols

	def define_sym(self, sym_name: str, def_addr: int):
		if sym_name in self._symbols:
			if self._symbols[sym_name][0] == None:
				self._symbols[sym_name] = (def_addr, self._symbols[sym_name][1])
			else:
				raise RuntimeError(f"'{sym_name}' is already defined")
		else:
			self._symbols[sym_name] = (def_addr, [])

	def add_sym_ref(self, sym_name: str, ref_addr: int):
		if not sym_name in self._symbols:
			self._symbols[sym_name] = (None, [])
		self._symbols[sym_name][1].append(ref_addr)

	def print(self):
		print()
		for k in self._symbols:
			print(f"{k.ljust(20)}{self._symbols[k]}")

	def items(self):
		return self._symbols.items()
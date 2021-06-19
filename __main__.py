import dmf
import sys

def print_std_macro(macro: dmf.STDMacro):
	print("\t\t[ ", end='', flush=True)
	for value in macro.envelope_values:
		print(f"{value}, ", end="", flush=True)
	print("]")
	if macro.loop_enabled: print("\t\tloop:", macro.loop_position)
	else:                  print("\t\tloop: no")

def print_debug_info(module: dmf.Module):
	print("========= Format flags & System =========")
	print("version:", module.version)
	print("system:", module.system)
	print("")

	print("========== Visual information ==========")
	print("name:", module.song_name)
	print("author:", module.song_author)
	print("")

	print("========== Module information ==========")
	print("time base:", module.time_base)
	print("tick time 1:", module.tick_time_1)
	print("tick time 2:", module.tick_time_2)
	print("hz value:", module.hz_value)
	print("rows per pattern:", module.rows_per_pattern)
	print("rows in pattern matrix:", module.rows_in_pattern_matrix)
	print("")

	print("=========== Pattern matrix ===========")
	for ch in range(13):
		print("[ ", end='', flush=True)
		for row in range(module.rows_in_pattern_matrix):
			print("${0:02x}, ".format(module.pattern_matrix[ch][row]), end="", flush=True)
		print("]")
	print("")

	print("=========== Instruments ===========")
	for i in range(len(module.instruments)):
		instrument = module.instruments[i]

		if isinstance(instrument, dmf.FMInstrument):
			print("${0:02x}: {1} [FM]".format(i, instrument.name))
			print("\talg:", instrument.algorithm)
			print("\tfb:", instrument.feedback)
			print("\tfms:", instrument.fms)
			print("\tams:", instrument.ams)
			for j in range(len(instrument.operators)):
				operator = instrument.operators[j]
				print(f"\tOperator {j+1}")
				print("\t\tam:", operator.am)
				print("\t\tar:", operator.ar)
				print("\t\tdr:", operator.dr)
				print("\t\tmult:", operator.mult)
				print("\t\trr:", operator.rr)
				print("\t\tsl:", operator.sl)
				print("\t\ttl:", operator.tl)
				print("\t\tdt2:", operator.dt2)
				print("\t\trs:", operator.rs)
				print("\t\tdt:", operator.dt)
				print("\t\td2r:", operator.d2r)
				print("\t\tssg:", f"{operator.ssg_mode} [{operator.ssg_enabled}]")

		else:
			print("${0:02x}: {1} [STD]".format(i, instrument.name))
			print("\tVolume Macro")
			print_std_macro(instrument.volume_macro)
			print("\tArpeggio Macro")
			print_std_macro(instrument.arpeggio_macro)
			print("\t\tmode:", instrument.arpeggio_mode.name)
			print("\tNoise Macro")
			print_std_macro(instrument.noise_macro)
			print("\tChannel Mode Macro")
			print_std_macro(instrument.chmode_macro)

def print_pattern(pattern: dmf.Pattern):
	note_labels = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-", "C-"]
	for row in pattern.rows:
		if row.note == 100:
			print("OFF", end=" ", flush=True)
		else:
			if row.note == None:
				print("--", end="", flush=True)
			else:
				print(note_labels[row.note], end="", flush=True)
			
			if row.octave == None:
				print("-", end=" ", flush=True)
			else:
				print(row.octave, end=" ", flush=True)

		if row.volume == None:
			print("--", end=" ", flush=True)
		else:
			print("{0:02X}".format(row.volume), end=" ", flush=True)

		if row.instrument == None:
			print("--", end=" ", flush=True)
		else:
			print("{0:02X}".format(row.instrument), end=" ", flush=True)

		for effect in row.effects:
			if effect.code == dmf.EffectCode.EMPTY:
				print("--", end="", flush=True)
			else:
				print("{0:02X}".format(effect.code), end="", flush=True)

			if effect.value == None:
				print("--", end=" ", flush=True)
			else:
				print("{0:02X}".format(effect.value), end=" ", flush=True)
		print("")

module: dmf.Module

with open(sys.argv[1], "rb") as file:
	module = dmf.Module(file.read())

channel = int(sys.argv[2])
pat_id  = int(sys.argv[3])

print_pattern(module.patterns[channel][pat_id])
#print_debug_info(module)
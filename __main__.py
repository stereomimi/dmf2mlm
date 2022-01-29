from src import dmf,mzs,utils,sfx
from pathlib import Path
import argparse

def print_info(mlm_sdata):
	if len(mlm_sdata.songs) <= 0: return
	for i in range(len(mlm_sdata.songs[0].channels)):
		channel = mlm_sdata.songs[0].channels[i]
		print("\n================[ {0:01X} ]================".format(i))

		if channel == None: 
			print("Empty")
			continue

		for event in channel.events:
			print(event)
			if isinstance(event, mzs.SongComJumpToSubEL):
				sub_el = mlm_sdata.songs[0].sub_event_lists[i][event.sub_el_idx]
				sub_el.print()
				print("\t--------")
				
def print_df_info(mod, channels: [int]):
	for ch in channels:
		if mod.pattern_matrix.matrix[ch] == None: continue
		print("|#########[${0:02X}]#########".format(ch), end='')
	print("|")

	for i in range(mod.pattern_matrix.rows_in_pattern_matrix):
		for ch in channels:
			if mod.pattern_matrix.matrix[ch] == None: continue
			subel_idx = mod.pattern_matrix.matrix[ch][i]
			print("|=========(${0:02X})=========".format(subel_idx), end='')
		print("|")

		for j in range(mod.pattern_matrix.rows_per_pattern):
			for ch in channels:
				if mod.pattern_matrix.matrix[ch] == None: continue
				pat_idx = mod.pattern_matrix.matrix[ch][i]
				row = mod.patterns[ch][pat_idx].rows[j]
				note_lbl = "--"
				oct_lbl  = "-"
				vol_lbl  = "--"
				inst_lbl = "--"
				fx_lbl  = ""
				if row.octave != None:
					oct_lbl = str(row.octave)
				if row.note == dmf.Note.NOTE_OFF:
					note_lbl = "OF"
					oct_lbl  = "F"
				elif row.note != None:
					note_lbl = row.note.name.ljust(2, '-').replace('S', '#')
				if row.volume != None:
					vol_lbl = "{:02X}".format(row.volume)
				if row.instrument != None:
					inst_lbl = "{:02X}".format(row.instrument)
				for k in range(3):
					if k >= len(row.effects):
						fx_lbl += " ----"
					else:
						fx = row.effects[k]
						if fx.code == dmf.EffectCode.EMPTY:
							fx_lbl += " ~~"
						else:
							fx_lbl += " {:02X}".format(fx.code.value)
						if fx.value == None:
							fx_lbl += "~~"
						else:
							fx_lbl += "{:02X}".format(fx.value)


				"""
				if len(row.effects) > 0:
					fx0 = row.effects[0]
					if fx0.code == dmf.EffectCode.EMPTY:
						fx0_lbl = "--"
					else:
						fx0_lbl = "{:02X}".format(fx0.code.value)
					if fx0.value == None:
						fx0_lbl += "--"
					else:
						fx0_lbl += "{:02X}".format(fx0.value)
				"""
				print("|{0}{1} {2}{3}{4}".format(note_lbl, oct_lbl, vol_lbl, inst_lbl, fx_lbl), end='')
			print("|")	

parser = argparse.ArgumentParser(description='Convert DMF modules and SFX to an MLM driver compatible format')
parser.add_argument('dmf_module_paths', type=str, nargs='*', help="The paths to the input DMF files")
parser.add_argument('--sfx-directory', type=Path, help="Path to folder containing .raw files (Only absolute paths; Must be 18500Hz 16bit mono)")
parser.add_argument('--sfx-header', type=Path, help="Where to save the generated SFX c header (Only absolute paths)")

args = parser.parse_args()
dmf_modules = []
sfx_samples = None

if args.sfx_directory != None:
	print("Parsing SFX... ", end='', flush=True)
	sfx_samples = sfx.SFXSamples(args.sfx_directory)
	print("OK")

	if args.sfx_header != None:
		print("Generating SFX Header... ", end='', flush=True)
		c_header = sfx_samples.generate_c_header()
		print("OK")
		print(f"Saving SFX Header as '{args.sfx_header}'... ", end='', flush=True)
		with open(args.sfx_header, "w") as file:
			file.write(c_header)
		print("OK")
			

for i in range(len(args.dmf_module_paths)):
	with open(args.dmf_module_paths[i], "rb") as file:
		print(f"Parsing '{args.dmf_module_paths[i]}'... ", end='', flush=True)
		mod = dmf.Module(file.read())
		print("OK")

		print(f"Patching '{args.dmf_module_paths[i]}'... ", end='', flush=True)
		mod.patch_for_mzs()
		print("OK")
		
		print(f"Optimizing '{args.dmf_module_paths[i]}'... ", end='', flush=True)
		mod.optimize()
		print("OK")
		dmf_modules.append(mod)

mlm_sdata = mzs.SoundData()
print(f"Converting DMFs... ", end='', flush=True)
mlm_sdata.add_dmfs(dmf_modules)
print("OK")

if sfx_samples != None:
	print(f"Converting SFX... ", end='', flush=True)
	mlm_sdata.add_sfx(sfx_samples, False)
	print("OK")

"""
print("{")
print_df_info(dmf_modules[0], list(range(0, 13)))
print("}\n{")
print_info(mlm_sdata)
print("}")
"""

print(f"Compiling... ", end='', flush=True)
mlm_compiled_sdata = mlm_sdata.compile_sdata()
mlm_compiled_vrom = mlm_sdata.compile_vrom()
print("OK")

with open("m1_sdata.bin", "wb") as file:
	file.write(mlm_compiled_sdata)

with open("vrom.bin", "wb") as file:
	file.write(mlm_compiled_vrom)
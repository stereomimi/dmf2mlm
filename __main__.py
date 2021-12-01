from src import dmf,mzs,utils,sfx
from pathlib import Path
import argparse

def print_info(mlm_sdata):
	for i in range(len(mlm_sdata.songs[0].channels)):
		channel = mlm_sdata.songs[0].channels[i]
		print("\n================[ {0:01X} ]================".format(i))

		if channel == None: 
			print("Empty")
			continue

		for event in channel.events:
			if isinstance(event, mzs.SongComJumpToSubEL):
				sub_el = mlm_sdata.songs[0].sub_event_lists[i][event.sub_el_idx]
				sub_el.print()
				print("\t--------")
			else:
				print(event)

parser = argparse.ArgumentParser(description='Convert DMF modules and SFX to an MLM driver compatible format')
parser.add_argument('dmf_module_paths', type=str, nargs='*', help="The paths to the input DMF files")
parser.add_argument('--sfx-directory', type=Path, help="Path to folder containing .raw files (Only absolute paths; Must be 18500Hz 16bit mono)")
parser.add_argument('--sfx-header', type=Path, help="Where to save the generated SFX c header (Only absolute paths)")
parser.add_argument('--patch-pos-jumps', action='store_true', help="Patches module to remove the need to repeat $0B effects for every channel, ONLY WORKS WITH MODULES THAT DON'T REUSE PATTERNS EVER")

args = parser.parse_args()
dmf_modules = []
sfx_samples = None

if args.patch_pos_jumps: 
	print("POS. JUMP PATCHING ENABLED")
if args.sfx_directory != None:
	print("Parsing SFX... ", end='', flush=True)
	sfx_samples = sfx.SFXSamples(args.sfx_directory)
	print(" OK")

	if args.sfx_header != None:
		print("Generating SFX Header...", end='', flush=True)
		c_header = sfx_samples.generate_c_header()
		print(" OK")
		print(f"Saving SFX Header as '{args.sfx_header}'...", end='', flush=True)
		with open(args.sfx_header, "w") as file:
			file.write(c_header)
		print(" OK")
			

for i in range(len(args.dmf_module_paths)):
	with open(args.dmf_module_paths[i], "rb") as file:
		print(f"Parsing '{args.dmf_module_paths[i]}'...", end='', flush=True)
		mod = dmf.Module(file.read())
		print(" OK")

		print(f"Optimizing '{args.dmf_module_paths[i]}'...", end='', flush=True)
		mod.patch_for_mzs(args.patch_pos_jumps)
		mod.optimize()
		print(" OK")
		dmf_modules.append(mod)

mlm_sdata = mzs.SoundData()
print(f"Converting DMFs...", end='', flush=True)
mlm_sdata.add_dmfs(dmf_modules)
print(" OK")

if sfx_samples != None:
	print(f"Converting SFX...", end='', flush=True)
	mlm_sdata.add_sfx(sfx_samples, False)
	print(" OK")

print_info(mlm_sdata)

print(f"Compiling...", end='', flush=True)
mlm_compiled_sdata = mlm_sdata.compile_sdata()
mlm_compiled_vrom = mlm_sdata.compile_vrom()
print(" OK")

with open("m1_sdata.bin", "wb") as file:
	file.write(mlm_compiled_sdata)

with open("vrom.bin", "wb") as file:
	file.write(mlm_compiled_vrom)
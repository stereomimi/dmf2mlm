from src import dmf,mzs,utils
import sys, argparse

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
parser.add_argument('--sfx-directory', type=str, help="Path to folder containing wav files (0.wav ... 255.wav)")
parser.add_argument('dmf_module_paths', type=str, nargs='+', help="The paths to the input DMF files")
args = parser.parse_args(sys.argv)
dmf_modules = []

for i in range(1, len(args.dmf_module_paths)):
	with open(args.dmf_module_paths[i], "rb") as file:
		print(f"Parsing '{args.dmf_module_paths[i]}'...", end='', flush=True)
		mod = dmf.Module(file.read())
		print(" OK")

		print(f"Optimizing '{args.dmf_module_paths[i]}'...", end='', flush=True)
		mod.optimize()
		print(" OK")
		dmf_modules.append(mod)

print(f"Converting...", end='\n', flush=True)
mlm_sdata = mzs.SoundData.from_dmf(dmf_modules)
print(" OK")

#print_info(mlm_sdata)

print(f"Compiling...", end='', flush=True)
mlm_compiled_sdata = mlm_sdata.compile_sdata()
mlm_compiled_vrom = mlm_sdata.compile_vrom()
print(" OK")

with open("m1_sdata.bin", "wb") as file:
	file.write(mlm_compiled_sdata)

with open("vrom.bin", "wb") as file:
	file.write(mlm_compiled_vrom)
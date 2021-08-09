from src import dmf,mzs
import sys

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

dmf_modules = []

for i in range(1, len(sys.argv)):
	with open(sys.argv[i], "rb") as file:
		print(f"Parsing '{sys.argv[i]}'...", end='', flush=True)
		mod = dmf.Module(file.read())
		print(" OK")

		print(f"Optimizing '{sys.argv[i]}'...", end='', flush=True)
		mod.optimize()
		print(" OK")
		dmf_modules.append(mod)

print(f"Converting...", end='\n', flush=True)
mlm_sdata = mzs.SoundData.from_dmf(dmf_modules)
print(" OK")

#print_info(mlm_sdata)

print(f"Compiling...", end='', flush=True)
mlm_compiled_sdata = mlm_sdata.compile()
print(" OK")

with open("m1_sdata.bin", "wb") as file:
	file.write(mlm_compiled_sdata)
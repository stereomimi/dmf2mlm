from src import dmf,mzs
import sys

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

print(f"Converting...", end='', flush=True)
mlm_sdata = mzs.SoundData.from_dmf(dmf_modules)
print(" OK")

print(f"Compiling...", end='', flush=True)
mlm_compiled_sdata = mlm_sdata.compile()
print(" OK")

with open("m1_sdata.bin", "wb") as file:
	file.write(mlm_compiled_sdata)
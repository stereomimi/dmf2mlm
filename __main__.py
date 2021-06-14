import dmf
import sys

module: dmf.Module

with open(sys.argv[1], "rb") as file:
	module = dmf.Module(file.read())

print("========= Format flags & System =========")
print("\tversion:", module.version)
print("\tsystem:", module.system)
print("")

print("========== Visual information ==========")
print("\tname:", module.song_name)
print("\tauthor:", module.song_author)
print("")

print("========== Module information ==========")
print("\ttime base:", module.time_base)
print("\ttick time 1:", module.tick_time_1)
print("\ttick time 2:", module.tick_time_2)
print("\thz value:", module.hz_value)
print("\trows per pattern:", module.rows_per_pattern)
print("\trows in pattern matrix:", module.rows_in_pattern_matrix)
print("")

print("=========== Pattern matrix ===========")
for ch in range(13):
	print("[ ", end='', flush=True)
	for row in range(module.rows_in_pattern_matrix):
		print("${0:02x}, ".format(module.pattern_matrix[ch][row]), end="", flush=True)
	print("]")
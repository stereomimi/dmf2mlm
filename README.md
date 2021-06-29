# dmf2mlm
Program that converts deflemask project files to a neogeo M1ROM running the Mezz'Estate audio driver

## Conversion steps

1. Parse the DMF modules (dmf.py)

2. Merge the parsed DMF modules (multi_dmf.py)

3. Convert the merged modules into a mlm.SoundData instance (????)

4. Compile said instance into an m1rom (mzs/\*.py)
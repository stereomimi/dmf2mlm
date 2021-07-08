# dmf2mlm
Program that converts deflemask project files to a neogeo M1ROM running the Mezz'Estate audio driver

## Conversion steps

1. Parse the DMF modules (dmf.py)

3. Convert the merged modules into a mlm.SoundData instance (mzs/\*.py)

4. Compile said instance into an m1rom (????)

## Limitations

- Only 255 instruments per song can be used, since Instrument 0 is used for
ADPCM-A samples

- SSG Noise tone macros will be ignored since I don't know how they'd work, since there's a single Noise channel shared inbetween all three channels
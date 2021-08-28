# dmf2mlm
Program that converts deflemask project files to a neogeo M1ROM running the Mezz'Estate audio driver

[freem's adpcma encoder](https://github.com/freem/adpcma) MUST be in $PATH as `adpcma`. 

## Conversion steps

1. Parse the DMF modules (dmf.py)

3. Convert the merged modules into a mlm.SoundData instance (mzs/\*.py)

4. Compile said instance into an m1rom (mzs/\*.py)

## Limitations

- Only 255 instruments per song can be used, since one instrument is used for
ADPCM-A samples

- SSG Noise tone macros will be ignored since I don't know how they'd work, since there's a single Noise channel shared inbetween all three channels

## Conversion info

- Each pattern is converted into a sub event list, and the pattern matrix is converted into a series of "Jump to sub event list" commands.

- If the used patterns in a pattern matrix channel are $00, $01, $10, and $03
then they will be respectively converted into the channel's sub-EL 0, 1, 3, and 2. first the unique used patterns are found (`list(set(pat_matrix))`), then they're sorted (`unique_pats.sort()`); the sub-EL id is found from said unique pattern list (`unique_pats.find(pattern)`)

## TODO

- Find a way to merge samples, since it's likely that the songs will share samples
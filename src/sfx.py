from pathlib import Path

class SFXSamples:
    MAX_SAMPLE_COUNT = 128
    paths: [Path]

    def __init__(self, sfx_dir_path: Path):
        self.paths = list(sfx_dir_path.glob('*.wav'))
        if len(self.paths) == 0:
            self = None
            return
        elif len(self.paths) > SFXSamples.MAX_SAMPLE_COUNT:
            raise RuntimeError("Too many samples")

    def generate_c_header(self) -> str:
        CONST_PREFIX = "SFX_"
        c_header = "/*\n  [SFX CONSTANTS]\n  Header generated using 'dmf2mlm'\n  https://github.com/GbaCretin/dmf2mlm\n*/\n\n"

        for i in range(len(self.paths)):
            sfx_name = self.paths[i].name.removesuffix(".wav")
            const_name = "_".join(sfx_name.upper().split()) # Convert to Constant Case
            const_name = CONST_PREFIX + const_name
            c_header += f"#define {const_name} ({i})\n"

        return c_header
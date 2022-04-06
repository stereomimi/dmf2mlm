from pathlib import Path

C_HEADER_BEGIN = """/*
    ==============[SFX CONSTS]==============
        Header generated using 'dmf2mlm'  
      https://github.com/GbaCretin/dmf2mlm
    ========================================
*/

#ifndef DMF2MLM_Z80_CODE_H
#define DMF2MLM_Z80_CODE_H

#define Z80_UCOM_PLAY_SONG(song)              Z80_send_user_command(0x01, song)
#define Z80_UCOM_STOP()                       Z80_send_user_command(0x02, 0)
#define Z80_UCOM_BUFFER_SFXPS_CVOL(pan, cvol) Z80_send_user_command(0x03, (pan) | ((cvol) & 0x1F))
#define Z80_UCOM_BUFFER_SFXPS_PRIO(prio)      Z80_send_user_command(0x04, prio)
#define Z80_UCOM_PLAY_SFXPS_SMP(smp)          Z80_send_user_command(0x05, smp)
#define Z80_UCOM_RETRIG_SFXPS_SMP(smp)        Z80_send_user_command(0x0B, smp)
#define Z80_UCOM_FADE_IN(tmb_ldcnt)           Z80_send_user_command(0x06 | (tmb_ldcnt & 1), tmb_ldcnt>>1)
#define Z80_UCOM_FADE_OUT(tmb_ldcnt)          Z80_send_user_command(0x08 | (tmb_ldcnt & 1), tmb_ldcnt>>1)
#define Z80_UCOM_BUFFER_FADE_OFS(ofs)         Z80_send_user_command(0x0A, ofs)

typedef enum {
    PAN_NONE   = 0x00,
    PAN_LEFT   = 0x40,
    PAN_RIGHT  = 0x20,
    PAN_CENTER = 0x60,
} Panning;

// Both the command's and the
// parameter's MSB is always
// set to 1
void Z80_send_user_command(u8 command, u8 parameter);
#endif // DMF2MLM_Z80_CODE_H

#ifdef DMF2MLM_Z80_IMPLEMENTATION
void __attribute__((optimize("O0"))) Z80_wait_loop(int loops)
{
    for(u16 i = 0; i < loops; ++i);
}

void Z80_send_user_command(u8 command, u8 parameter)
{
	const u8 user_com_mask = 0x80;
	command |= user_com_mask;
	parameter |= user_com_mask;

	*REG_SOUND = command;
    u8 neg_command = command ^ 0xFF;
	while (*REG_SOUND != neg_command);
	wait_loop(64);

	*REG_SOUND = parameter;
    u8 neg_parameter = parameter ^ 0xFF;
	while (*REG_SOUND != neg_parameter);
	wait_loop(64);
}
#endif // DMF2MLM_Z80_IMPLEMENTATION

"""
class SFXSamples:
    MAX_SAMPLE_COUNT = 128
    paths: [Path]

    def __init__(self, sfx_dir_path: Path):
        self.paths = list(sfx_dir_path.glob('*.raw'))
        self.paths.sort(key=lambda x: x.name)
        if len(self.paths) == 0:
            self = None
            return
        elif len(self.paths) > SFXSamples.MAX_SAMPLE_COUNT:
            raise RuntimeError("Too many samples")

    def generate_c_header(self) -> str:
        CONST_PREFIX = "SFX_"
        c_header = C_HEADER_BEGIN

        for i in range(len(self.paths)):
            sfx_name = self.paths[i].name.removesuffix(".raw")
            const_name = "_".join(sfx_name.upper().split()) # Convert to Constant Case
            const_name = CONST_PREFIX + const_name
            c_header += f"#define {const_name} ({i})\n"

        return c_header
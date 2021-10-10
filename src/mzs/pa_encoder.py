import os

class ADPCMAEncoder:
    # Buffers
    cmd_name: str

    def __init__(self, cmd_name="adpcma"):
        self.cmd_name = cmd_name

    def call_encoder(self, in_path: str, out_path: str, verbose: bool = False):
        cmd = f"{self.cmd_name} {in_path} {out_path}"
        if not verbose: 
            cmd += " > /dev/null"
        code = os.system(cmd)
        if code != 0x00:
            raise RuntimeError("Error while running ADPCM-A Encoder")

    def ym_encode_pcm(self, buffer: bytes) -> bytes:
        PCM_FILE_NAME  = "tmp.pcm"
        PCMA_FILE_NAME = "tmp.pcma"
        out_buffer: bytes

        with open(PCM_FILE_NAME, "wb") as file:
            file.write(buffer)
            file.flush()
            self.call_encoder(PCM_FILE_NAME, PCMA_FILE_NAME)
        
        with open(PCMA_FILE_NAME, "rb") as file:
            out_buffer = file.read()

        os.remove(PCM_FILE_NAME)
        os.remove(PCMA_FILE_NAME)
        return out_buffer
import os

class ADPCMAEncoder:
    # Buffers
    cmd_name: str

    def __init__(self, cmd_name="adpcma"):
        self.cmd_name = cmd_name

    def _call_encoder(self, in_path, out_path, verbose: bool = False):
        cmd = f"{self.cmd_name} '{in_path}' '{out_path}'"
        if not verbose: 
            cmd += " > /dev/null"
        else:
            print(cmd)
        code = os.system(cmd)
        if code != 0x00:
            raise RuntimeError("Error while running ADPCM-A Encoder")

    def ym_encode_pcm(self, buffer: bytes, verbose: bool = False) -> bytes:
        PCM_FILE_NAME  = "tmp.pcm"
        PCMA_FILE_NAME = "tmp.pcma"
        out_buffer: bytes
        with open(PCM_FILE_NAME, "wb") as file:
            file.write(buffer)
            file.flush()
            self._call_encoder(PCM_FILE_NAME, PCMA_FILE_NAME, verbose)
        
        with open(PCMA_FILE_NAME, "rb") as file:
            out_buffer = file.read()

        os.remove(PCM_FILE_NAME)
        os.remove(PCMA_FILE_NAME)
        return out_buffer

    def ym_encode_path(self, in_path: bytes, verbose: bool = False) -> bytes:
        PCMA_FILE_NAME = "tmp.pcma"
        out_buffer: bytes

        self._call_encoder(in_path, PCMA_FILE_NAME, verbose)
        with open(PCMA_FILE_NAME, "rb") as file:
            out_buffer = file.read()
        os.remove(PCMA_FILE_NAME)

        return out_buffer
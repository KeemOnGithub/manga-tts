import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    device_map="cuda:0",
    dtype=torch.bfloat16
    # attn_implementation="flash_attention_2",
)

def generate_tts(text, instruct):
    wavs, sr = model.generate_voice_design(
        text=text,
        language=["English"],
        instruct=instruct
    )

    # save below for as many texts that exist.
    sf.write("output_voice_design_1.wav", wavs[0], sr)
    sf.write("output_voice_design_2.wav", wavs[1], sr)
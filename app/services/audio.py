from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path


def assemble_mp3(audio_files: list[Path], output_path: Path) -> None:
    if not audio_files:
        raise ValueError("There are no generated audio segments to assemble.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized: list[Path] = []
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        for index, source in enumerate(audio_files):
            target = output_path.parent / f"normalized-{index:05d}.wav"
            subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(source), "-ar", "24000", "-ac", "1", str(target)],
                           check=True, capture_output=True)
            normalized.append(target)
        with wave.open(str(output_path.parent / "joined.wav"), "wb") as destination:
            with wave.open(str(normalized[0]), "rb") as first:
                destination.setparams(first.getparams())
            for source in normalized:
                with wave.open(str(source), "rb") as segment:
                    destination.writeframes(segment.readframes(segment.getnframes()))
        subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(output_path.parent / "joined.wav"),
                        "-codec:a", "libmp3lame", "-q:a", "4", str(output_path)], check=True, capture_output=True)
        for item in normalized + [output_path.parent / "joined.wav"]:
            item.unlink(missing_ok=True)
        return
    if len(audio_files) == 1 and audio_files[0].suffix.lower() == ".mp3":
        shutil.copyfile(audio_files[0], output_path)
        return
    raise RuntimeError("MP3 assembly requires ffmpeg installed and available on PATH.")

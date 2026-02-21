"""
generate_assets.py — Creates placeholder WAV sound files and PNG icons for PostureGuard.
Run once before launching the application: python generate_assets.py
"""

import struct, wave, math, os
from pathlib import Path

BASE = Path(__file__).resolve().parent


def _write_wav(path: Path, freq: float, duration: float = 0.6, volume: float = 0.5):
    """Generate a simple sine-wave WAV file."""
    sample_rate = 44100
    n_samples   = int(sample_rate * duration)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = []
        for i in range(n_samples):
            t   = i / sample_rate
            val = int(32767 * volume * math.sin(2 * math.pi * freq * t))
            frames.append(struct.pack("<h", val))
        wf.writeframes(b"".join(frames))
    print(f"  Created: {path.relative_to(BASE)}")


def _write_png_icon(path: Path, size: int = 32, r=137, g=180, b=250):
    """Generate a minimal single-colour square PNG icon using only stdlib."""
    import zlib

    path.parent.mkdir(parents=True, exist_ok=True)

    def _png_chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    # Header
    signature = b"\x89PNG\r\n\x1a\n"
    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    ihdr = _png_chunk(b"IHDR", ihdr_data)
    # IDAT: raw scanlines (filter byte 0x00 + RGB * size)
    raw_row = bytes([0]) + bytes([r, g, b] * size)
    raw     = raw_row * size
    idat = _png_chunk(b"IDAT", zlib.compress(raw))
    # IEND
    iend = _png_chunk(b"IEND", b"")

    with open(path, "wb") as f:
        f.write(signature + ihdr + idat + iend)
    print(f"  Created: {path.relative_to(BASE)}")


def main():
    print("Generating PostureGuard assets …\n")

    # Sounds
    sounds_dir = BASE / "assets" / "sounds"
    _write_wav(sounds_dir / "posture_alert.wav",    freq=880, duration=0.5)   # high beep
    _write_wav(sounds_dir / "drowsiness_alert.wav", freq=440, duration=0.8)   # low beep

    # Icons
    icons_dir = BASE / "assets" / "icons"
    _write_png_icon(icons_dir / "app_icon.png",       r=137, g=180, b=250)   # blue
    _write_png_icon(icons_dir / "good_posture.png",   r=166, g=227, b=161)   # green
    _write_png_icon(icons_dir / "bad_posture.png",    r=243, g=139, b=168)   # red
    _write_png_icon(icons_dir / "drowsy_alert.png",   r=249, g=226, b=175)   # yellow

    print("\nAll assets generated successfully.")


if __name__ == "__main__":
    main()

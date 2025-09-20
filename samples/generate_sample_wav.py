#!/usr/bin/env python3
"""
Generate a small WAV sample (440Hz sine) for manual QA.
Outputs: samples/sample_5s.wav (mono, 16kHz)
"""
import math
import wave
import struct
import os

SAMPLE_RATE = 16000
DURATION_SEC = 5
FREQUENCY_HZ = 440.0
AMPLITUDE = 0.5

def main():
    base_dir = os.path.dirname(__file__)
    out_dir = os.path.join(base_dir, 'out')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'sample_5s.wav')
    total_frames = SAMPLE_RATE * DURATION_SEC
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        for n in range(total_frames):
            t = float(n) / SAMPLE_RATE
            sample = AMPLITUDE * math.sin(2.0 * math.pi * FREQUENCY_HZ * t)
            val = int(sample * 32767.0)
            wf.writeframes(struct.pack('<h', val))
    print(f"Wrote {path}")

if __name__ == '__main__':
    main()


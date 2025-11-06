# flynapse_music_align.py
from pydub import AudioSegment, generators
import os

# --- Paths ---
folder = "flynapse_audio"
voice_path = os.path.join(folder, "flynapse_full_voiceover.mp3")
output_path = os.path.join(folder, "flynapse_final_mix.mp3")

# --- Scene timing guide (seconds) ---
#   0:00–0:04   Problem intro  → low drone
#   0:04–0:08   Ripple impact  → rising tension pulse
#   0:08–0:14   Engineering chaos → rhythmic urgency
#   0:14–0:48   Product demo   → steady tech pulse
#   0:48–0:54   Ramp optimism  → warm pad lift
#   0:54–1:00   Finale         → orchestral swell
scene_timing = [
    ("intro", 0, 4, "dark_low"),
    ("ripple", 4, 8, "tension"),
    ("chaos", 8, 14, "rhythmic"),
    ("product", 14, 48, "steady"),
    ("ramp", 48, 54, "warm"),
    ("finale", 54, 60, "swell")
]

# --- helper: simple synthetic tone beds ---
def make_pad(freq, duration_ms, gain_db=-10):
    tone = generators.Sine(freq).to_audio_segment(duration=duration_ms)
    tone = tone.low_pass_filter(400)
    return tone - abs(gain_db)

def make_pulse(freq, duration_ms, gain_db=-10, bpm=90):
    beat_ms = int(60000 / bpm)
    pulse = make_pad(freq, beat_ms, gain_db)
    seq = AudioSegment.silent(duration=0)
    for _ in range(int(duration_ms / beat_ms)):
        seq += pulse.fade_out(100) + AudioSegment.silent(duration=beat_ms // 2)
    return seq

# --- build ambient bed by scene ---
layers = AudioSegment.silent(duration=0)
for name, start, end, mood in scene_timing:
    dur = int((end - start) * 1000)
    if mood == "dark_low":
        seg = make_pad(55, dur, -12)
    elif mood == "tension":
        seg = make_pad(65, dur, -10).overlay(make_pulse(130, dur, -16, 100))
    elif mood == "rhythmic":
        seg = make_pulse(110, dur, -12, 105)
    elif mood == "steady":
        seg = make_pulse(100, dur, -14, 95)
    elif mood == "warm":
        seg = make_pad(220, dur, -12).fade_in(500)
    elif mood == "swell":
        seg = make_pad(260, dur, -10).fade_in(500).fade_out(1000)
    else:
        seg = AudioSegment.silent(duration=dur)

    # Add gentle reverb-like overlap between scenes
    seg = seg.fade_in(500).fade_out(700)
    layers += seg

# --- overlay with actual voice track ---
voice = AudioSegment.from_mp3(voice_path)

# Match duration
if len(layers) < len(voice):
    loops = (len(voice) // len(layers)) + 1
    layers = layers * loops
layers = layers[:len(voice)]

# Balance levels
voice_gain = 0
music_gain = -15
mix = layers + music_gain
mix = mix.overlay(voice + voice_gain)

# Normalize to -14 LUFS equivalent
target_dbfs = -14
mix = mix.apply_gain(-mix.dBFS - abs(target_dbfs))

# Export
mix.export(output_path, format="mp3")
print(f"✅ Final aligned music mix saved: {output_path}")

from openai import OpenAI
from pydub import AudioSegment
import os
import sys
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# Install ffmpeg from winget
# winget install --id=Gyan.FFmpeg -e
# Get Azure OpenAI settings from environment
API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = "https://flynapse-ai-foundry.cognitiveservices.azure.com"
AZURE_OPENAI_API_VERSION = "2025-03-01-preview"
AZURE_OPENAI_DEPLOYMENT = "gpt-4o-mini-tts"

missing = []
if not API_KEY:
    missing.append("AZURE_OPENAI_API_KEY")
if not AZURE_OPENAI_ENDPOINT:
    missing.append("AZURE_OPENAI_ENDPOINT")
if not AZURE_OPENAI_API_VERSION:
    missing.append("AZURE_OPENAI_API_VERSION")
if not AZURE_OPENAI_DEPLOYMENT:
    missing.append("AZURE_OPENAI_DEPLOYMENT")
if missing:
    print(f"Error: Missing required environment variables: {', '.join(missing)}")
    sys.exit(1)

# Initialize Azure OpenAI-compatible client
# Note: Azure uses deployment in the path and requires api-version and api-key header

client = OpenAI(
    api_key=API_KEY,
    base_url=f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}",
    default_query={"api-version": AZURE_OPENAI_API_VERSION},
    default_headers={"api-key": API_KEY},
)

# Folder setup
os.makedirs("flynapse_audio", exist_ok=True)

# Choose voice
VOICE = "alloy"   # Try also: "shimmer", "breeze", "verse", "coral"

# --- 1️⃣ Voiceover segments with mood and pacing cues ---
voiceover_segments = {
    "overall": """
[Tone: serious, cinematic, with gravity]
Every minute an aircraft stays on the ground… airlines lose millions ...

Delays ripple through schedules — drain utilization… and erode passenger trust.

...
[Tone: tense, fast-paced, empathetic]
Behind those moments… are engineering teams buried in data .. — manuals, fault codes, dashboards — all racing to find the one answer that gets the aircraft flying again.  

Sometimes, it’s not even a complex fault… just something like — low hydraulic pump pressure ...

Yet finding the right fix still means jumping between systems… diagrams… and old logbooks — .. precious minutes lost… while the aircraft waits on the ground...

[Tone: confident, reassuring, optimistic]
That’s where Flynapse comes in... — your AI Engineering Copilot… for every aircraft.  

It understands your technical documentation instantly — every system… every fault… every scenario —  
so engineers can focus on solving problems… not searching through PDFs...

[Tone: conversational, clear, helpful]
Just ask… and it delivers clear, verified answers — drawn directly from the right manuals… tailored to your aircraft type...  
It surfaces the root cause… recommended action… and the exact page in the maintenance manual — all in one view.  
As it learns across fleets… it reveals patterns early — helping prevent tomorrow’s AOG before it happens.

[Tone: inspiring, rising, cinematic finale]
Because smarter decisions on the ramp… mean stronger schedules in the sky.  
..
Flynapse. …  
Fly more. …  
Fix faster. …  
Schedule your demo… at flynapse.ai.
"""
}


# --- 2️⃣ Generate TTS audio for each segment ---
for key, text in voiceover_segments.items():
    out_path = f"flynapse_audio/{key}.mp3"
    if os.path.exists(out_path):
        print(f"⏭️ Skipping existing segment: {key} ({out_path})")
        continue
    print(f"🎙️ Generating segment: {key} ...")
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=VOICE,
        input=text
    )
    speech.stream_to_file(out_path)
    print(f"✅ Saved {out_path}")

print("\nAll voiceover segments generated successfully.\n")
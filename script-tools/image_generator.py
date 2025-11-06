from openai import OpenAI
import os, base64
import sys
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# Get Azure OpenAI settings from environment
API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = "https://flynapse-ai-foundry.cognitiveservices.azure.com"
AZURE_OPENAI_API_VERSION = "2025-04-01-preview"
AZURE_OPENAI_IMAGE_DEPLOYMENT = "gpt-image-1"

missing = []
if not API_KEY:
    missing.append("AZURE_OPENAI_API_KEY")
if not AZURE_OPENAI_ENDPOINT:
    missing.append("AZURE_OPENAI_ENDPOINT")
if not AZURE_OPENAI_API_VERSION:
    missing.append("AZURE_OPENAI_API_VERSION")
if not AZURE_OPENAI_IMAGE_DEPLOYMENT:
    missing.append("AZURE_OPENAI_IMAGE_DEPLOYMENT")
if missing:
    print(f"Error: Missing required environment variables: {', '.join(missing)}")
    sys.exit(1)

# Initialize Azure OpenAI-compatible client
# Note: Azure uses deployment in the path and requires api-version and api-key header

client = OpenAI(
    api_key=API_KEY,
    base_url=f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_IMAGE_DEPLOYMENT}",
    default_query={"api-version": AZURE_OPENAI_API_VERSION},
    default_headers={"api-key": API_KEY},
)

# --- 1️⃣ Shared watermark phrase ---
WATERMARK_NOTE = (
    "Include a small subtle 'Flynapse' watermark in the bottom-right corner in light gray text, "
    "simple sans-serif font, unobtrusive but visible. Do not add any other text."
)

# --- 2️⃣ Lookboard prompt ---
lookboard_prompt = f"""
Create a flat vector style visual reference board for a corporate aviation AI brand called Flynapse.
Show color swatches, gradient samples, and example lighting schemes in a clean 16:9 layout.
Include labeled sections for:
- Brand Blues (#1F6FEB primary, #0D2B4A deep navy)
- Neutrals (#F7F9FC soft white, #D9E1EC cool gray)
- Accents (#E85C5C red, #F29F67 orange, #33B5C3 teal)
- Lighting directions (top-left, radial, sunrise warm)
Minimalist, professional design with subtle aviation-tech aesthetic.
{WATERMARK_NOTE}
Corporate flat vector style, 16:9, clean background.
"""

# --- 3️⃣ Scene prompts ---
scene_prompts = {
    "scene_1_grounded_aircraft": f"""
    Flat vector illustration of a large commercial aircraft grounded on the tarmac under cloudy sky,
    surrounded by orange maintenance cones and ground equipment. Subtle clock overlay hinting at time loss.
    Minimalist airport background with cool gray and blue palette, corporate aviation explainer style,
    clean gradients, 16:9 composition.
    {WATERMARK_NOTE}
    """,

    "scene_2_delay_ripple": f"""
    Flat vector illustration showing an abstract flight route map or operations network over a stylized globe,
    with glowing red delay nodes spreading outward in ripple waves. Represents cascading disruptions in airline schedules.
    Minimalist tech style with geometric lines, blue and red highlights, corporate tone, 16:9 composition.
    {WATERMARK_NOTE}
    """,

    # --- NEW 3-part visual sequence for "pressure" segment ---
    "scene_3a_engineer_data_overload": f"""
    Flat vector illustration of multiple aircraft engineers in a hangar or control room,
    surrounded by floating holographic manuals, fault codes, and dashboards.
    Their expressions show stress and urgency as streams of data and warning icons swirl around.
    One engineer gestures toward a large schematic display. The aircraft tail and maintenance bay are visible in the background.
    Dynamic composition, bluish lighting, aviation industry explainer style, clean gradients, 16:9 aspect ratio.
    {WATERMARK_NOTE}
    """,

    "scene_3b_fault_alert": f"""
    Flat vector close-up of a diagnostic tablet or cockpit-style display showing a flashing
    “Hydraulic Pump Pressure Low” alert in red and amber tones.
    An engineer leans in, focused, as subsystem panels show valve and pressure readings.
    Background shows blurred hangar elements and subtle motion lines indicating tension.
    Clean, technical gradients, minimal clutter, aviation tech interface style, 16:9 aspect ratio.
    {WATERMARK_NOTE}
    """,

    "scene_3c_time_lost": f"""
    Flat vector illustration of a weary engineer flipping between paper manuals and digital screens,
    surrounded by scattered diagrams and open binders.
    Through a large hangar door, the idle aircraft is visible under sunset light — symbolizing time lost.
    Subtle motion lines and floating pages convey chaos and frustration.
    Emotional yet clean composition, consistent aviation explainer aesthetic, 16:9 aspect ratio.
    {WATERMARK_NOTE}
    """,
    # --- END of 3-part sequence ---

    "scene_3_relief_intro": f"""
    Flat vector illustration of a stylized digital cockpit or holographic dashboard transforming into a real software interface window. 
    Represents transition from concept to product. Clean, minimal, futuristic vector design with blue tech tones, 16:9 aspect ratio.
    {WATERMARK_NOTE}
    """,

    "scene_4_ramp_coordination": f"""
    Flat vector illustration of engineers and ground crew coordinating beside an aircraft at sunrise.
    Digital tablets and AR overlays display data around the plane. Scene conveys teamwork, efficiency, and readiness.
    Warm lighting, clean gradients, professional aviation explainer tone, 16:9 aspect ratio.
    {WATERMARK_NOTE}
    """,

    "scene_5_takeoff_logo": f"""
    Flat vector illustration for a closing brand frame.
    A small, stylized airplane climbs gracefully toward the upper third of the frame,
    leaving dynamic contrails or glowing data streams behind it that curve upward.
    The lower and central area should be open, clean, and reserved for the Flynapse logo and tagline text.
    Background should transition from soft gradient blue at the top to lighter white-blue near the bottom,
    symbolizing clarity and uplift.
    Include subtle abstract cloud and network line motifs, maintaining professional corporate aviation style.
    Minimalist, flat vector, clean gradients, 16:9 composition.
    {WATERMARK_NOTE}
    """
}


# --- 4️⃣ Create output folder ---
os.makedirs("flynapse_images", exist_ok=True)

# --- 5️⃣ Helper: save image locally ---
def save_image(response, filename):
    image_base64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)
    filepath = f"flynapse_images/{filename}.png"
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    print(f"✅ Saved: {filepath}")

# --- 6️⃣ Generate lookboard first ---
lookboard_filepath = os.path.join("flynapse_images", "flynapse_lookboard.png")
if os.path.exists(lookboard_filepath):
    print(f"⏭️ Skipping lookboard (exists: {lookboard_filepath})")
else:
    print("🎨 Generating Flynapse Lookboard...")
    lookboard_response = client.images.generate(
        prompt=lookboard_prompt,
        size="1536x1024"
    )
    save_image(lookboard_response, "flynapse_lookboard")

# --- 7️⃣ Generate all scenes ---
for name, prompt in scene_prompts.items():
    scene_filepath = os.path.join("flynapse_images", f"{name}.png")
    if os.path.exists(scene_filepath):
        print(f"⏭️ Skipping {name} (exists: {scene_filepath})")
        continue
    print(f"🖼️ Generating {name} ...")
    response = client.images.generate(
        prompt=prompt,
        size="1536x1024"
    )
    save_image(response, name)

print("\n✅ All images (with watermark + lookboard) generated successfully!")

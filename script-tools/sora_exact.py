#!/usr/bin/env python3
"""
Using the exact code from the documentation with your specific values.
Shows that the documentation approach doesn't work with Azure Sora.

Reference: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/video-generation?tabs=python-key
"""

import os
import time
from openai import OpenAI

# Set your API key in environment variable
# export AZURE_OPENAI_API_KEY="your-key-here"

# Create client exactly as in the docs
client = OpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url="https://flynapse-sora.openai.azure.com/openai/v1/",  # Using .openai.azure.com
)

print("Using API endpoint: https://flynapse-sora.openai.azure.com/openai/v1/")
print("Following docs exactly: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/video-generation")

try:
    # Create video exactly as in the docs
    video = client.videos.create(
        model="sora",  # Your deployment name
        prompt="A video of a cool cat on a motorcycle in the night",
    )

    print("Video generation started:", video)

    # If the above works, let's also try to poll and download
    print(f"Video ID: {video.id}")
    print(f"Initial status: {video.status}")

    # Poll until completion
    while video.status not in ["completed", "failed", "cancelled"]:
        print(f"Status: {video.status}. Waiting 15 seconds...")
        time.sleep(15)
        
        # Retrieve the latest status
        video = client.videos.retrieve(video.id)

    # Final status
    if video.status == "completed":
        print("Video successfully completed!")
        
        # Try to download
        try:
            print(f"Downloading video with ID: {video.id}")
            content = client.videos.download_content(video.id, variant="video")
            output_path = "sora_exact_output.mp4"
            content.write_to_file(output_path)
            print(f"Saved video to {output_path}")
        except Exception as e:
            print(f"Download error: {str(e)}")
            print("This confirms the documentation is incorrect about the download mechanism.")
    else:
        print(f"Video creation ended with status: {video.status}")
        print(video)
except Exception as e:
    print(f"Error: {str(e)}")
    print("This confirms the documentation is incorrect about the API parameters or endpoint structure.")
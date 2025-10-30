#!/usr/bin/env python3
"""
Direct API call to Azure OpenAI Sora using the exact URL provided.
This approach works for video generation but fails on download.

Reference: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/video-generation?tabs=python-key
"""

import requests
import time
import json
import os
import sys

# Your API key should be set in environment variable
# export AZURE_OPENAI_API_KEY="your-key-here"

# Get API key from environment
API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
if not API_KEY:
    print("Error: AZURE_OPENAI_API_KEY environment variable not set")
    sys.exit(1)

# API endpoint
API_URL = "https://flynapse-sora.cognitiveservices.azure.com/openai/v1/video/generations/jobs?api-version=preview"
MODEL = "sora"

# Headers
headers = {
    "Content-Type": "application/json",
    "api-key": API_KEY
}

# Request payload - use width and height as separate parameters
payload = {
    "model": MODEL,
    "prompt": "A ticking clock and a worried business person",
    "n_seconds": 4,
    # Use width and height as separate parameters instead of "size"
    "width": 1280,
    "height": 720
}

print(f"Making direct API call to: {API_URL}")
print(f"With payload: {json.dumps(payload, indent=2)}")

try:
    # Create job
    response = requests.post(API_URL, headers=headers, json=payload)
    
    if not response.ok:
        print(f"Error: {response.status_code} {response.text}")
        exit(1)
    
    job_data = response.json()
    print(f"Response: {json.dumps(job_data, indent=2)}")
    
    job_id = job_data.get("id")
    if not job_id:
        print("No job ID in response")
        exit(1)
    
    print(f"Job ID: {job_id}")
    
    # Poll status
    status_url = f"https://flynapse-sora.cognitiveservices.azure.com/openai/v1/video/generations/jobs/{job_id}?api-version=preview"
    
    while True:
        time.sleep(15)
        status_response = requests.get(status_url, headers=headers)
        
        if not status_response.ok:
            print(f"Error checking status: {status_response.status_code} {status_response.text}")
            continue
        
        status_data = status_response.json()
        status = status_data.get("status")
        progress = status_data.get("progress", 0)
        print(f"Status: {status}, Progress: {progress}%")
        
        if status in ("succeeded", "completed", "done"):
            print("Job completed!")
            print(f"Full response: {json.dumps(status_data, indent=2)}")
            
            # Try multiple download URL formats
            download_urls = [
                # Try with job_id in the URL
                f"https://flynapse-sora.cognitiveservices.azure.com/openai/v1/video/generations/jobs/{job_id}/content?api-version=preview",
                # Try with job_id and variant
                f"https://flynapse-sora.cognitiveservices.azure.com/openai/v1/video/generations/jobs/{job_id}/content?api-version=preview&variant=video",
                # Try with job_id in a different format
                f"https://flynapse-sora.cognitiveservices.azure.com/openai/v1/video/generations/jobs/{job_id}/video?api-version=preview",
            ]
            
            # Also try with generation_id if available
            generations = status_data.get("generations", [])
            if generations and len(generations) > 0:
                generation_id = generations[0].get("id")
                if generation_id:
                    download_urls.extend([
                        f"https://flynapse-sora.cognitiveservices.azure.com/openai/v1/video/generations/{generation_id}/content?api-version=preview",
                        f"https://flynapse-sora.cognitiveservices.azure.com/openai/v1/video/generations/{generation_id}/content?api-version=preview&variant=video",
                    ])
            
            # Try each URL until one works
            success = False
            for url in download_urls:
                print(f"Trying download URL: {url}")
                download_response = requests.get(url, headers=headers, stream=True)
                
                if download_response.ok:
                    # Check if the response is actually a video (content type or size)
                    content_type = download_response.headers.get('content-type', '')
                    content_length = int(download_response.headers.get('content-length', 0))
                    
                    if 'video' in content_type or content_length > 10000:  # Assuming videos are larger than 10KB
                        # Save the video
                        output_path = "sora_direct_output.mp4"
                        with open(output_path, "wb") as f:
                            for chunk in download_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        print(f"Saved video to {output_path}")
                        success = True
                        break
                    else:
                        print(f"Response doesn't appear to be a video: {content_type}, size: {content_length}")
                else:
                    print(f"Error with URL {url}: {download_response.status_code} {download_response.text}")
            
            if not success:
                print("Failed to download video with any URL format")
                print("This confirms the documentation is incorrect about the download mechanism.")
            
            break
        
        if status in ("failed", "canceled", "cancelled", "error"):
            print(f"Job failed: {json.dumps(status_data, indent=2)}")
            break
        
        time.sleep(15)

except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
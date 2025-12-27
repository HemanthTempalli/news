"""
Quick test to verify API key fix works
"""
import sys
import io
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from config import GEMINI_API_KEY, ADK_MODEL_NAME
from google import genai
import os

print("=" * 70)
print("Testing API Key Fix")
print("=" * 70)

# Ensure environment is set correctly
os.environ['GOOGLE_API_KEY'] = GEMINI_API_KEY
os.environ['GEMINI_API_KEY'] = GEMINI_API_KEY

print(f"\nAPI Key being used: {GEMINI_API_KEY[:20]}... (length: {len(GEMINI_API_KEY)})")
print(f"Model: {ADK_MODEL_NAME}")

# Create client
print("\nCreating Gemini client...")
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("✅ Client created successfully")
except Exception as e:
    print(f"❌ Error creating client: {e}")
    sys.exit(1)

# Test API call
print("\nTesting API call with simple prompt...")
try:
    response = client.models.generate_content(
        model=ADK_MODEL_NAME,
        contents="Say 'API key is working' if you can read this."
    )
    result = response.text if hasattr(response, 'text') else str(response)
    print(f"✅ API call successful!")
    print(f"Response: {result[:100]}")
    print("\n" + "=" * 70)
    print("✅ SUCCESS: API key is working correctly!")
    print("=" * 70)
except Exception as e:
    error_str = str(e)
    if "API key" in error_str or "expired" in error_str.lower() or "400" in error_str:
        print(f"❌ API KEY ERROR: {error_str[:200]}")
        print("\nThe API key might still be invalid or expired.")
        print("Please check:")
        print("1. Your .env file has the correct API key")
        print("2. The API key is valid and not expired")
        print("3. You have API access enabled in Google AI Studio")
    else:
        print(f"❌ Error: {error_str[:200]}")
    sys.exit(1)


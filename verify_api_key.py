"""
Script to verify API key is loaded correctly from .env file
This helps diagnose API key issues
"""
import os
import sys
import io
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv

print("=" * 70)
print("API Key Verification Script")
print("=" * 70)

# Check system environment variables (these might be old/expired)
print("\n1. System Environment Variables (may be outdated):")
sys_gemini = os.environ.get('GEMINI_API_KEY', 'NOT SET')
sys_google = os.environ.get('GOOGLE_API_KEY', 'NOT SET')
print(f"   GEMINI_API_KEY: {sys_gemini[:20] + '...' if sys_gemini != 'NOT SET' and len(sys_gemini) > 20 else sys_gemini}")
print(f"   GOOGLE_API_KEY: {sys_google[:20] + '...' if sys_google != 'NOT SET' and len(sys_google) > 20 else sys_google}")

# Load .env file
print("\n2. Loading .env file...")
env_paths = [
    Path(__file__).parent / ".env",
    Path(__file__).parent / "backend" / ".env",
]

loaded = False
for env_path in env_paths:
    if env_path.exists():
        print(f"   Found .env at: {env_path}")
        # Use override=True to override system env vars
        load_dotenv(env_path, override=True)
        loaded = True
        break

if not loaded:
    print("   ❌ ERROR: No .env file found!")
    print("   Please create a .env file with: GEMINI_API_KEY=your_key_here")
    sys.exit(1)

# Check .env file values
print("\n3. Values from .env file (after override=True):")
env_gemini = os.getenv('GEMINI_API_KEY', 'NOT SET')
env_google = os.getenv('GOOGLE_API_KEY', 'NOT SET')
print(f"   GEMINI_API_KEY: {env_gemini[:20] + '...' if env_gemini != 'NOT SET' and len(env_gemini) > 20 else env_gemini} (length: {len(env_gemini) if env_gemini != 'NOT SET' else 0})")
print(f"   GOOGLE_API_KEY: {env_google[:20] + '...' if env_google != 'NOT SET' and len(env_google) > 20 else env_google} (length: {len(env_google) if env_google != 'NOT SET' else 0})")

# Verify they match
if env_gemini != 'NOT SET' and env_google != 'NOT SET':
    if env_gemini == env_google:
        print("\n✅ SUCCESS: API keys match and are loaded correctly!")
    else:
        print("\n⚠️  WARNING: GEMINI_API_KEY and GOOGLE_API_KEY don't match!")
        print("   This might cause issues. They should be the same.")
else:
    print("\n❌ ERROR: API key not found in .env file!")
    print("   Please add: GEMINI_API_KEY=your_key_here")

# Test import
print("\n4. Testing config import...")
try:
    from config import GEMINI_API_KEY, ADK_MODEL_NAME
    print(f"   ✅ Config loaded successfully")
    print(f"   API Key from config: {GEMINI_API_KEY[:20] + '...' if len(GEMINI_API_KEY) > 20 else GEMINI_API_KEY} (length: {len(GEMINI_API_KEY)})")
    print(f"   Model: {ADK_MODEL_NAME}")
except Exception as e:
    print(f"   ❌ Error importing config: {e}")

print("\n" + "=" * 70)
print("Verification Complete")
print("=" * 70)


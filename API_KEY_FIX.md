# API Key Fix - System Environment Variable Override Issue

## Problem
You were getting "API key expired" errors even though you have a valid API key in your `.env` file that works on other machines.

## Root Cause
Your system has **system-level environment variables** set that were overriding the `.env` file:
- System `GEMINI_API_KEY` = Old/expired key
- System `GOOGLE_API_KEY` = Different old/expired key
- `.env` file = New valid key

The Python `dotenv` library by default does NOT override system environment variables, so it was using the old system-level keys instead of your `.env` file.

## Solution Applied

### 1. Updated `backend/config.py`
- Changed `load_dotenv()` to `load_dotenv(override=True)`
- This ensures `.env` file values override system environment variables
- Added explicit setting of both `GEMINI_API_KEY` and `GOOGLE_API_KEY`

### 2. Updated `backend/agents/fact_check_agent_adk.py`
- Added `get_client()` function that always creates a fresh client with the correct API key
- Updated agent functions to use fresh clients and retry on API key errors
- Added API key validation and logging

## How to Verify the Fix

Run the verification script:
```bash
python verify_api_key.py
```

This will show you:
1. What system environment variables are set (may be old)
2. What values are loaded from `.env` file
3. Whether they match correctly

## Alternative: Clear System Environment Variables (Optional)

If you want to remove the system-level environment variables entirely:

**Windows PowerShell (as Administrator):**
```powershell
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "Machine")
[Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "Machine")
```

**Or manually:**
1. Press `Win + R`, type `sysdm.cpl`, press Enter
2. Go to "Advanced" tab → "Environment Variables"
3. Remove `GEMINI_API_KEY` and `GOOGLE_API_KEY` from System variables
4. Restart your terminal/IDE

**Note:** You don't need to do this - the fix ensures `.env` file takes precedence.

## Testing

After the fix, try running your fact-check again:
```bash
python test_claim.py
```

Or use the main CLI:
```bash
python backend/main.py
```

The API key should now be loaded correctly from your `.env` file!


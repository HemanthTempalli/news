# Fix: Environment File Terminal Injection

## Problem
You're seeing this error:
> "An environment file is configured but terminal environment injection is disabled. Enable 'python.terminal.use EnvFile' to use environment variables from .env files in terminals."

## Solution 1: VS Code/Cursor Settings (Automatic)

I've created `.vscode/settings.json` and `.cursor/settings.json` files that should fix this automatically.

**To apply the fix:**
1. Close and reopen VS Code/Cursor
2. Or reload the window: `Ctrl+Shift+P` → "Reload Window"

## Solution 2: Manual Settings (If Solution 1 doesn't work)

1. Open Settings: `Ctrl+,` (or `File` → `Preferences` → `Settings`)
2. Search for: `python.terminal.activateEnvironment`
3. Check the box to enable it
4. Search for: `python.envFile`
5. Set it to: `${workspaceFolder}/.env`

## Solution 3: Manual Terminal Setup (Temporary Fix)

If the above doesn't work, you can manually load the .env file in your terminal:

**PowerShell:**
```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
}
```

**Or use Python to load it:**
```python
from dotenv import load_dotenv
load_dotenv()
```

## Solution 4: Check Python Extension

Make sure you have the Python extension installed:
- VS Code: Install "Python" extension by Microsoft
- Cursor: Should have Python support built-in

## Verify It's Working

After applying the fix, open a new terminal and run:
```python
import os
print(os.getenv('GEMINI_API_KEY')[:10] + '...' if os.getenv('GEMINI_API_KEY') else 'Not found')
```

If you see part of your API key, it's working!


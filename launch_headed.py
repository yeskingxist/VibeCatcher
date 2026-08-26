import sys
import time
from auth import auth_manager

print("="*60)
print("LAUNCHING HEADED CHROMIUM BROWSER WINDOW...")
print("Please log in to your Instagram account in the opened window.")
print("Once login is completed, the session ID will be captured automatically.")
print("="*60)

success = auth_manager.login_via_headed_browser()

if success:
    print("\n[OK] Success! Session captured and saved to session.json.")
else:
    print("\n[FAIL] Failed to capture session ID or window closed.")

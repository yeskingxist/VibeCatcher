import os
import time
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, TwoFactorRequired, BadPassword, LoginRequired
from rich.console import Console
from rich.prompt import Prompt

from config import config, SESSION_FILE

console = Console(force_terminal=True)

class AuthManager:
    """Manages Instagram client authentication, device parameters, 2FA, and session persistence."""
    
    def __init__(self):
        self.client = Client()
        self._configure_client()

    def _configure_client(self):
        """Sets custom proxy and settings on the instagrapi Client instance."""
        if config.proxy:
            console.print(f"[cyan]Using Proxy: {config.proxy}[/cyan]")
            self.client.set_proxy(config.proxy)
            
        # Custom device settings to mimic a real Android device
        custom_device = config.data.get("custom_device")
        if custom_device:
            device = self.client.device_settings.copy() if hasattr(self.client, "device_settings") and self.client.device_settings else {}
            device.update(custom_device)
            if "version_code" not in device:
                device["version_code"] = "314582313"
            try:
                self.client.set_device(device)
            except Exception:
                pass

    def load_session(self) -> bool:
        """Attempts to load saved session from session.json and verify it."""
        if SESSION_FILE.exists():
            try:
                # Re-instantiate to discard dirty in-memory cache/state
                self.client = Client()
                self._configure_client()
                
                self.client.load_settings(SESSION_FILE)
                if self.client.user_id:
                    # Trust the loaded session to avoid blocking network checks on every status poll
                    if not self.client.username or self.client.username == "None":
                        self.client.username = "Connected"
                    return True
            except Exception as e:
                console.print(f"[yellow]Session expired or invalid: {e}[/yellow]")
                # Attempt silent background auto-refresh via Playwright
                if self.auto_refresh_session():
                    return True
        return False

    def save_session(self):
        """Saves current session settings to session.json."""
        try:
            self.client.dump_settings(SESSION_FILE)
            console.print("[bold green][OK] Session saved for future use.[/bold green]")
        except Exception as e:
            console.print(f"[red]Failed to save session: {e}[/red]")

    def disconnect(self):
        """Disconnects currently authenticated account and clears settings."""
        if SESSION_FILE.exists():
            try:
                SESSION_FILE.unlink()
                console.print("[bold yellow]Session file deleted successfully.[/bold yellow]")
            except Exception as e:
                console.print(f"[red]Failed to delete session file: {e}[/red]")
        
        # Clear credentials from config if any
        if "credentials" in config.data:
            del config.data["credentials"]
            config.save()
            
        self.client = Client()
        self._configure_client()

    def handle_challenge(self, username: str, password: str):
        """Handles security challenge / 2FA verification."""
        try:
            console.print("[bold yellow]Challenge or 2FA Required![/bold yellow]")
            code = Prompt.ask("Enter 2FA / Security Verification Code")
            self.client.login(username, password, verification_code=code)
            self.save_session()
            return True
        except Exception as e:
            console.print(f"[bold red]Challenge verification failed: {e}[/bold red]")
            return False

    def login_with_sessionid(self, session_id: str) -> bool:
        """Bypasses password authentication using Instagram sessionid cookie."""
        self._configure_client()
        try:
            console.print("[yellow]Bypassing login via sessionid cookie...[/yellow]")
            self.client.login_by_sessionid(session_id)
            self.save_session()
            console.print("[bold green][OK] Session successfully authenticated via sessionid cookie![/bold green]")
            return True
        except Exception as e:
            console.print(f"[bold red]SessionID Login Error: {e}[/bold red]")
            return False

    def login(self, username: str = None, password: str = None, interactive: bool = True) -> bool:
        """Log in via restored session or username/password credentials."""
        self._configure_client()

        if not username and not password:
            if self.load_session():
                return True

        if not username or not password:
            if not interactive:
                raise ValueError("Username and password are required for non-interactive login.")
            console.print("\n[bold cyan]=== Instagram Login ===[/bold cyan]")
            username = Prompt.ask("Instagram Username")
            password = Prompt.ask("Instagram Password (visible)")

        try:
            console.print(f"[yellow]Authenticating as @{username}...[/yellow]")
            self.client.login(username, password)
            self.save_session()
            
            # Save credentials for future background auto-refresh
            config.data["credentials"] = {"username": username, "password": password}
            config.save()
            
            console.print(f"[bold green][OK] Successfully logged in as @{username}![/bold green]")
            return True
        except TwoFactorRequired as e:
            if interactive:
                return self.handle_challenge(username, password)
            raise e
        except ChallengeRequired as e:
            if interactive:
                return self.handle_challenge(username, password)
            raise e
        except BadPassword as e:
            console.print(f"[bold red]BadPassword Error: {e}[/bold red]")
            return False
        except Exception as e:
            console.print(f"[bold red]Login error details: {type(e).__name__}: {e}[/bold red]")
            return False

    def _get_browser_profile_dir(self) -> str:
        """Returns the persistent browser profile directory path."""
        profile_dir = Path(__file__).parent.resolve() / "browser_data"
        profile_dir.mkdir(exist_ok=True)
        return str(profile_dir)

    def auto_refresh_session(self) -> bool:
        """Silently opens the persistent browser profile headlessly, extracts fresh sessionid."""
        return self.refresh_from_persistent_browser()

    def login_via_persistent_browser(self, status_callback=None) -> bool:
        """Opens a headed persistent browser for manual Instagram login.
        
        The browser profile is saved permanently in browser_data/ so Instagram
        stays logged in across reboots. After user logs in, sessionid cookie is
        extracted and fed to instagrapi.
        
        Args:
            status_callback: Optional callable(msg, pct) for progress updates.
        """
        console.print("[yellow]Launching persistent browser for manual login...[/yellow]")
        if status_callback:
            status_callback("Launching browser window...", 10)
        
        try:
            from playwright.sync_api import sync_playwright
            profile_dir = self._get_browser_profile_dir()
            
            with sync_playwright() as p:
                # Persistent context = browser profile saved to disk permanently
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=False,
                    viewport={"width": 420, "height": 780},
                    user_agent="Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                    args=["--disable-blink-features=AutomationControlled"],
                )
                
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://www.instagram.com/accounts/login/", timeout=60000)
                
                if status_callback:
                    status_callback("Browser opened — log in to your Instagram account.", 25)
                console.print("[cyan]Browser opened — waiting for user to log in...[/cyan]")
                
                # Poll for sessionid cookie (max 5 minutes)
                session_cookie = None
                logged_in_username = None
                for i in range(600):
                    try:
                        if not context.pages:
                            break
                    except Exception:
                        break
                    
                    cookies = context.cookies()
                    # Debug print
                    if i % 10 == 0:
                        console.print(f"DEBUG: Found {len(cookies)} cookies. Names: {[c['name'] for c in cookies]}")
                        
                    for c in cookies:
                        if c["name"] == "sessionid" and c["value"]:
                            session_cookie = c["value"]
                            break
                    
                    if session_cookie:
                        if status_callback:
                            status_callback("Login detected! Verifying account...", 70)
                        console.print(f"[green]Login detected! (sessionid={session_cookie[:10]}...) Waiting 3 seconds...[/green]")
                        time.sleep(3)
                        
                        # Try to grab the logged-in username from the page
                        try:
                            # Re-read cookies after settling in case they refreshed
                            cookies = context.cookies()
                            for c in cookies:
                                if c["name"] == "sessionid" and c["value"]:
                                    session_cookie = c["value"]
                                if c["name"] == "ds_user_id" and c["value"]:
                                    pass  # user_id available if needed
                        except Exception:
                            pass
                        break
                    
                    time.sleep(0.5)
                
                # Close the browser window (profile stays on disk)
                try:
                    context.close()
                except Exception:
                    pass
                
                if session_cookie:
                    if status_callback:
                        status_callback("Session captured! Connecting to Instagram API...", 85)
                    console.print(f"[bold green][OK] Session cookie captured from persistent browser![/bold green]")
                    result = self.login_with_sessionid(session_cookie)
                    if result:
                        # Resolve username
                        try:
                            res = self.client.private_request('accounts/current_user/?edit=true')
                            logged_in_username = res['user']['username']
                            self.client.username = logged_in_username
                            self.save_session()
                        except Exception:
                            logged_in_username = "Connected"
                        if status_callback:
                            status_callback(f"Connected as @{logged_in_username}!", 100)
                    return result
                else:
                    if status_callback:
                        status_callback("Browser closed without login.", 0)
                    console.print("[red]Browser closed or timed out without capturing session cookie.[/red]")
                    return False
        except Exception as e:
            if status_callback:
                status_callback(f"Browser error: {e}", 0)
            console.print(f"[red]Persistent browser exception: {e}[/red]")
            return False

    def refresh_from_persistent_browser(self) -> bool:
        """Headlessly opens the persistent browser profile and extracts a fresh sessionid.
        
        Since the user already logged in once via login_via_persistent_browser(),
        Instagram auto-logs-in when the same profile is reopened. We just grab
        the cookie and reconnect instagrapi.
        """
        profile_dir = self._get_browser_profile_dir()
        # Only attempt if profile exists with data
        if not Path(profile_dir).exists() or not any(Path(profile_dir).iterdir()):
            console.print("[yellow]No persistent browser profile found. Cannot auto-refresh.[/yellow]")
            return False
        
        console.print("[yellow]Attempting silent session refresh from persistent browser profile...[/yellow]")
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=True,
                    viewport={"width": 420, "height": 780},
                    user_agent="Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                    args=["--disable-blink-features=AutomationControlled"],
                )
                
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://www.instagram.com/", timeout=30000)
                
                # Wait for auto-login to resolve (max 15 seconds)
                session_cookie = None
                for _ in range(30):
                    cookies = context.cookies("https://www.instagram.com")
                    for c in cookies:
                        if c["name"] == "sessionid" and c["value"]:
                            session_cookie = c["value"]
                            break
                    if session_cookie:
                        break
                    time.sleep(0.5)
                
                try:
                    context.close()
                except Exception:
                    pass
                
                if session_cookie:
                    console.print("[bold green][OK] Fresh session ID extracted from persistent profile![/bold green]")
                    return self.login_with_sessionid(session_cookie)
                else:
                    console.print("[red]Auto-refresh failed: No sessionid in persistent profile (re-login may be needed).[/red]")
                    return False
        except Exception as e:
            console.print(f"[red]Persistent browser refresh exception: {e}[/red]")
            return False

    def login_via_local_browser(self) -> bool:
        """Extracts active Instagram session cookies from local Google Chrome and Comet (BrowserOS) profiles,
        decrypts them using DPAPI + AES, and logs in."""
        import json
        import base64
        import sqlite3
        import shutil
        import tempfile
        import ctypes
        from ctypes import wintypes
        try:
            from Cryptodome.Cipher import AES
        except ImportError:
            try:
                from Crypto.Cipher import AES
            except ImportError:
                console.print("[bold red]Error: pycryptodome is required to decrypt browser cookies. Install with: pip install pycryptodome[/bold red]")
                return False

        # DPAPI blob decryption helper
        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        def decrypt_dpapi(encrypted_bytes):
            try:
                crypt32 = ctypes.windll.crypt32
                data_in = DATA_BLOB(len(encrypted_bytes), ctypes.create_string_buffer(encrypted_bytes))
                data_out = DATA_BLOB()
                success = crypt32.CryptUnprotectData(
                    ctypes.byref(data_in), None, None, None, None, 0, ctypes.byref(data_out)
                )
                if not success:
                    return None
                decrypted = ctypes.string_at(data_out.pbData, data_out.cbData)
                ctypes.windll.kernel32.LocalFree(data_out.pbData)
                return decrypted
            except Exception:
                return None

        def get_chrome_aes_key(local_state_path):
            try:
                with open(local_state_path, "r", encoding="utf-8") as f:
                    local_state = json.load(f)
                encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
                return decrypt_dpapi(encrypted_key[5:])
            except Exception:
                return None

        def decrypt_cookie_val(cipher_text, key):
            try:
                if cipher_text[:3] in (b'v10', b'v11'):
                    iv = cipher_text[3:15]
                    encrypted_value = cipher_text[15:]
                    cipher = AES.new(key, AES.MODE_GCM, iv)
                    decrypted = cipher.decrypt(encrypted_value)
                    return decrypted[:-16].decode('utf-8', errors='ignore')
                return cipher_text.decode('utf-8', errors='ignore')
            except Exception:
                return None

        local_appdata = Path(os.environ.get("LOCALAPPDATA", ""))
        
        # Define browsers and their profile trees
        browsers = {
            "Google Chrome": {
                "local_state": local_appdata / "Google/Chrome/User Data/Local State",
                "user_data": local_appdata / "Google/Chrome/User Data",
            },
            "Comet (BrowserOS)": {
                "local_state": local_appdata / "BrowserOS/BrowserOS/User Data/Local State",
                "user_data": local_appdata / "BrowserOS/BrowserOS/User Data",
            }
        }

        console.print("[yellow]Scanning local browsers for active Instagram logins...[/yellow]")
        
        for browser_name, paths in browsers.items():
            local_state = paths["local_state"]
            user_data = paths["user_data"]
            
            if not local_state.exists() or not user_data.exists():
                continue
                
            key = get_chrome_aes_key(local_state)
            if not key:
                continue
                
            # Scan all subdirectories for Network/Cookies SQLite file
            cookies_files = list(user_data.glob("**/Network/Cookies")) + list(user_data.glob("**/Cookies"))
            # Deduplicate
            cookies_files = list(set(cookies_files))
            
            for cookies_db in cookies_files:
                # Deduce profile name from path
                profile_name = cookies_db.parent.parent.name if "Network" in cookies_db.parts else cookies_db.parent.name
                
                temp_dir = tempfile.gettempdir()
                temp_db = os.path.join(temp_dir, "temp_auth_cookies")
                try:
                    shutil.copy2(cookies_db, temp_db)
                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name, value, encrypted_value FROM cookies WHERE host_key LIKE '%instagram.com'")
                    rows = cursor.fetchall()
                    
                    extracted = {}
                    for name, val, enc_val in rows:
                        decrypted = None
                        if enc_val:
                            decrypted = decrypt_cookie_val(enc_val, key)
                        else:
                            decrypted = val
                        if decrypted:
                            extracted[name] = decrypted
                            
                    conn.close()
                    os.remove(temp_db)
                    
                    session_id = extracted.get("sessionid")
                    if session_id:
                        console.print(f"[cyan]Found Instagram session ID in {browser_name} ({profile_name}). Testing...[/cyan]")
                        # Try verifying with login_by_sessionid
                        if self.login_with_sessionid(session_id):
                            # Test if session works
                            try:
                                me = self.client.user_info(self.client.user_id)
                                console.print(f"[bold green][OK] Successfully authenticated as @{me.username} from {browser_name} ({profile_name})![/bold green]")
                                return True
                            except Exception as e:
                                console.print(f"[yellow]Session from {browser_name} ({profile_name}) was invalid: {e}[/yellow]")
                except Exception as e:
                    if os.path.exists(temp_db):
                        os.remove(temp_db)
                    continue

        console.print("[bold red]Failed to extract any active, valid Instagram session cookies from your browsers.[/bold red]")
        return False

auth_manager = AuthManager()


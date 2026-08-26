import time
import random
from datetime import datetime, timedelta
from typing import Dict
from rich.console import Console

from config import config

console = Console()

class BotGuard:
    """Anti-Detection engine managing delays, humanized typing, and rate limits."""
    
    def __init__(self):
        self.action_counts: Dict[str, list] = {
            "comment": [],
            "follow": [],
            "dm": [],
            "delete": []
        }

    def _clean_old_records(self, action_type: str, window_seconds: int = 3600):
        now = datetime.now()
        cutoff = now - timedelta(seconds=window_seconds)
        self.action_counts[action_type] = [
            t for t in self.action_counts.get(action_type, []) if t > cutoff
        ]

    def check_rate_limit(self, action_type: str) -> bool:
        """Check if executing action exceeds safety limits."""
        limits = config.get_delays_and_limits()
        self._clean_old_records(action_type, window_seconds=3600)
        
        count = len(self.action_counts.get(action_type, []))
        
        max_map = {
            "comment": limits.get("max_comments_per_hour", 15),
            "follow": limits.get("max_follows_per_day", 35),
            "dm": limits.get("max_dms_per_hour", 30),
            "delete": 100
        }
        
        max_allowed = max_map.get(action_type, 50)
        if count >= max_allowed:
            console.print(f"[bold red]Rate limit threshold reached for '{action_type}' ({count}/{max_allowed}).[/bold red]")
            console.print("[yellow]Pausing operation to protect account from suspension...[/yellow]")
            return False
        return True

    def record_action(self, action_type: str):
        if action_type in self.action_counts:
            self.action_counts[action_type].append(datetime.now())

    def apply_delay(self, action_type: str, text_payload: str = None):
        """Applies a humanized randomized delay before executing an action."""
        limits = config.get_delays_and_limits()
        
        delay_range = limits.get(f"{action_type}_delay", (5, 12))
        min_sec, max_sec = delay_range
        
        # Calculate human typing delay if text payload exists
        typing_delay = 0.0
        if text_payload:
            # Simulate ~40-60 WPM typing speed + random variation
            typing_delay = len(text_payload) * random.uniform(0.05, 0.15)
        
        base_delay = random.uniform(min_sec, max_sec) + typing_delay
        # Gaussian micro-jitter (+/- 10%)
        jitter = random.gauss(0, base_delay * 0.1)
        final_delay = max(1.5, base_delay + jitter)
        
        console.print(f"[dim blue]Anti-Bot Guard: Simulating human activity... waiting {final_delay:.1f}s[/dim blue]")
        time.sleep(final_delay)

bot_guard = BotGuard()

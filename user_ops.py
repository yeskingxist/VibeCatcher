from rich.console import Console
from instagrapi.exceptions import UserNotFound

from auth import auth_manager
from bot_guard import bot_guard

console = Console()

class UserOpsManager:
    """Manages Instagram user operations (Follow, Unfollow, Profile Info)."""

    def follow_user(self, username: str) -> bool:
        """Follows a user with anti-detection protection."""
        if not bot_guard.check_rate_limit("follow"):
            return False

        try:
            console.print(f"[yellow]Fetching profile for @{username}...[/yellow]")
            info = auth_manager.client.user_info_by_username(username)
            user_id = info.pk
            
            # Check if already following via correct API endpoint
            friendship = auth_manager.client.user_friendship_v1(user_id)
            if friendship.following:
                console.print(f"[yellow]Already following @{username}, skipping follow request.[/yellow]")
                return True

            # Apply anti-bot humanized delay
            bot_guard.apply_delay("follow")

            console.print(f"[cyan]Sending follow request to @{username}...[/cyan]")
            result = auth_manager.client.user_follow(user_id)
            bot_guard.record_action("follow")
            
            if result:
                console.print(f"[bold green][OK] Successfully followed @{username}![/bold green]")
                return True
            else:
                console.print(f"[yellow]Follow request pending or already following @{username}.[/yellow]")
                return True
        except UserNotFound:
            console.print(f"[bold red]User '@{username}' not found.[/bold red]")
            return False
        except Exception as e:
            console.print(f"[bold red]Failed to follow user: {e}[/bold red]")
            return False

    def unfollow_user(self, username: str) -> bool:
        """Unfollows a user with anti-detection protection."""
        try:
            user_id = auth_manager.client.user_id_from_username(username)
            bot_guard.apply_delay("follow")
            result = auth_manager.client.user_unfollow(user_id)
            console.print(f"[bold green][OK] Successfully unfollowed @{username}![/bold green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Failed to unfollow user: {e}[/bold red]")
            return False

    def get_user_info(self, username: str):
        """Displays user profile details."""
        try:
            info = auth_manager.client.user_info_by_username(username)
            console.print(f"\n[bold cyan]Profile: @{info.username} ({info.full_name})[/bold cyan]")
            console.print(f"* Bio: {info.biography}")
            console.print(f"* Followers: {info.follower_count:,}")
            console.print(f"* Following: {info.following_count:,}")
            console.print(f"* Posts: {info.media_count:,}")
            console.print(f"* Private: {info.is_private}")
            return info
        except Exception as e:
            console.print(f"[bold red]Failed to fetch info for @{username}: {e}[/bold red]")
            return None

user_ops_manager = UserOpsManager()

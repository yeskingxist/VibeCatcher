import time
import re
import json
import urllib.parse
import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Callable, Optional
from rich.console import Console

from auth import auth_manager
from bot_guard import bot_guard
from reels import reel_manager
from user_ops import user_ops_manager
from pdf_builder import generate_cumulative_pdf

console = Console(force_terminal=True)

def clean_and_resolve_url(raw_url: Any) -> Optional[str]:
    """Cleans, unwraps Instagram redirect shims, and validates external resource URLs."""
    if not raw_url or not isinstance(raw_url, str):
        return None
    raw_url = raw_url.strip()
    if raw_url.lower() in ('true', 'false', 'none', 'null', 'undefined', ''):
        return None

    # Handle percent-encoded URLs like https%3A%2F%2F...
    if raw_url.startswith(('http%3A%2F%2F', 'https%3A%2F%2F')):
        raw_url = urllib.parse.unquote(raw_url)

    if not raw_url.startswith(('http://', 'https://')):
        return None

    # Handle Instagram / Facebook link redirect shims:
    # e.g., https://l.instagram.com/?u=https%3A%2F%2Fdrive.google.com...
    # or https://instagram.com/linkshim/?u=...
    if any(shim in raw_url.lower() for shim in ('l.instagram.com', 'instagram.com/linkshim', 'l.facebook.com', 'facebook.com/l.php')):
        try:
            parsed = urllib.parse.urlparse(raw_url)
            qs = urllib.parse.parse_qs(parsed.query)
            for k in ('u', 'url', 'target', 'dest'):
                if k in qs and qs[k]:
                    return clean_and_resolve_url(qs[k][0])
            match = re.search(r'[?&](?:u|url)=(https?(?:%3A%2F%2F|://)[^\s&"\'>]+)', raw_url)
            if match:
                return clean_and_resolve_url(urllib.parse.unquote(match.group(1)))
        except Exception:
            pass
        return None

    # Disallow internal Instagram/Facebook CDNs & posts/reels
    lower = raw_url.lower()
    disallowed = [
        'cdninstagram.com', 'fbcdn.net',
        'instagram.com/p/', 'instagram.com/reel/', 'instagram.com/stories/', 'instagram.com/tv/',
        'facebook.com/tr/', 'threads.net/'
    ]
    if any(d in lower for d in disallowed):
        return None

    # Clean trailing punctuation
    raw_url = raw_url.rstrip('.,;)>]"\'')
    return raw_url

def extract_urls_from_item(item: dict) -> List[str]:
    """Extracts all candidate external URLs from any Instagram DM item."""
    found = []

    # 1. Plain text & Link objects
    for text_val in [
        item.get('text', ''),
        item.get('link', {}).get('text', '') if isinstance(item.get('link'), dict) else '',
        item.get('link', {}).get('link_context', {}).get('link_url', '') if isinstance(item.get('link'), dict) else ''
    ]:
        if text_val and isinstance(text_val, str):
            for u in re.findall(r'https?://[^\s"\'\>\]\)]+', text_val):
                res = clean_and_resolve_url(u)
                if res:
                    found.append(res)

    # 2. Generic XMA & CTA Buttons
    xma_sources = []
    if isinstance(item.get('generic_xma'), list):
        xma_sources.extend(item['generic_xma'])
    elif isinstance(item.get('generic_xma'), dict):
        xma_sources.append(item['generic_xma'])
    if isinstance(item.get('xma'), list):
        xma_sources.extend(item['xma'])
    elif isinstance(item.get('xma'), dict):
        xma_sources.append(item['xma'])

    for xma in xma_sources:
        if not isinstance(xma, dict):
            continue
        for target_field in ['target_url', 'preview_url', 'action_url']:
            val = xma.get(target_field)
            if val and isinstance(val, str):
                res = clean_and_resolve_url(val)
                if res:
                    found.append(res)

        # Buttons inside XMA
        for btn in xma.get('cta_buttons', []):
            if not isinstance(btn, dict):
                continue
            for btn_field in ['action_url', 'target_url', 'url', 'action_payload']:
                val = btn.get(btn_field)
                if val and isinstance(val, str):
                    res = clean_and_resolve_url(val)
                    if res:
                        found.append(res)

    # 3. Encoded URLs in entire item JSON/string
    item_str = str(item)
    for raw_m in re.findall(r'https?://[^\s"\'\>\]\)]+', item_str):
        res = clean_and_resolve_url(raw_m)
        if res:
            found.append(res)
    for enc_m in re.findall(r'https%3A%2F%2F[^\s"\'\>\]\)\&\\]+', item_str):
        res = clean_and_resolve_url(urllib.parse.unquote(enc_m))
        if res:
            found.append(res)

    # Deduplicate preserving order
    seen = set()
    cleaned = []
    for u in found:
        if u not in seen:
            seen.add(u)
            cleaned.append(u)
    return cleaned

class ReelHarvestPipeline:
    """End-to-end automation pipeline: Reel Watch -> Follow Creator -> Comment -> DM Capture -> Scrape -> PDF Summary."""

    def scrape_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetches and summarizes webpage content from extracted DM link."""
        if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
            return None
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            response = httpx.get(url, headers=headers, follow_redirects=True, timeout=12.0)
            final_url = str(response.url)
            
            if response.status_code != 200:
                return {
                    "url": final_url,
                    "title": "External Resource",
                    "summary": f"Resource response code HTTP {response.status_code}",
                    "snippets": []
                }

            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else "Extracted Resource"
            
            # Extract paragraphs
            paragraphs = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 30]
            snippets = paragraphs[:5] # Top highlights
            
            summary = " ".join(paragraphs[:3])[:300] + "..." if paragraphs else "Resource link successfully retrieved."

            return {
                "url": final_url,
                "title": title,
                "summary": summary,
                "snippets": snippets
            }
        except Exception as e:
            return {
                "url": url,
                "title": "Resource Page",
                "summary": f"Resource captured ({str(e)[:120]})",
                "snippets": []
            }

    def process_reel(self, reel_url: str, comment_text: str, progress_cb: Callable[[str, int], None]) -> Dict[str, Any]:
        """
        Executes the full automated workflow.
        progress_cb(step_message, percentage) updates UI in real-time.
        """
        # Step 0: Ensure session is authenticated and valid
        if not auth_manager.load_session() or not auth_manager.is_session_valid():
            progress_cb("Verifying Instagram session...", 5)
            refreshed = auth_manager.auto_refresh_session()
            if not refreshed or not auth_manager.is_session_valid():
                auth_manager.disconnect()
                raise Exception("Instagram session has expired! Please click 'Connect Instagram Account' in the dashboard to reconnect.")

        # Step 1: Resolving Reel & Media Info
        progress_cb("1/6: Resolving Reel & Simulating Watch Time...", 10)
        media_id = reel_manager.extract_media_id(reel_url)
        try:
            media_info = auth_manager.client.media_info(media_id)
        except Exception as media_err:
            err_msg = str(media_err).lower()
            if any(k in err_msg for k in ['redirect', 'login_required', 'unauthorized', '403', 'checkpoint']):
                if auth_manager.auto_refresh_session() and auth_manager.is_session_valid():
                    media_info = auth_manager.client.media_info(media_id)
                else:
                    auth_manager.disconnect()
                    raise Exception("Instagram session has expired! Please click 'Connect Instagram Account' in the dashboard to reconnect.")
            else:
                raise Exception(f"Failed to fetch Reel details: {media_err}")
        creator = media_info.user
        creator_username = creator.username
        raw_caption = getattr(media_info, 'caption_text', '') or ''
        # Basic summary: strip hashtags, join lines
        clean_caption = re.sub(r'#\w+', '', raw_caption)
        clean_caption = " ".join([line.strip() for line in clean_caption.split('\n') if line.strip()])
        
        if len(clean_caption) < 10 and getattr(media_info, 'video_url', None):
            progress_cb("Reel has no caption. Transcribing audio via AI...", 15)
            try:
                import subprocess
                import speech_recognition as sr
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
                    resp = httpx.get(media_info.video_url, follow_redirects=True, timeout=20.0)
                    temp_video.write(resp.content)
                    temp_video_path = temp_video.name
                    
                temp_audio_path = temp_video_path.replace(".mp4", ".wav")
                subprocess.run(['ffmpeg', '-i', temp_video_path, '-q:a', '0', '-map', 'a', temp_audio_path, '-y'], 
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                recognizer = sr.Recognizer()
                with sr.AudioFile(temp_audio_path) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data)
                
                clean_caption = f"🎤 [AI Transcript]: {text}"
                try: os.remove(temp_video_path)
                except: pass
                try: os.remove(temp_audio_path)
                except: pass
            except Exception as tr_err:
                console.print(f"[yellow]Transcription failed: {tr_err}[/yellow]")
                clean_caption = ""

        summary_caption = clean_caption[:200] + "..." if len(clean_caption) > 200 else clean_caption
        
        # Simulate reel watch delay
        time.sleep(4.0)

        # Step 2: Follow Creator
        progress_cb(f"2/6: Following Creator @{creator_username}...", 25)
        user_ops_manager.follow_user(creator_username)
        progress_cb("Waiting 3 seconds after follow...", 35)
        time.sleep(3.0)

        # Step 3: Comment on Reel & Send DM Keyword Trigger
        progress_cb("3/6: Cleaning up previous comments...", 45)
        reel_manager.delete_my_previous_comments(reel_url)
        
        progress_cb(f"3/6: Posting comment: '{comment_text}' on Reel...", 50)
        comment_id = reel_manager.comment_on_reel(reel_url, comment_text)

        try:
            # Step 4: Wait and Poll for DM Auto-Responder (40 Seconds Loop)
            progress_cb("4/6: Polling Direct Messages for Creator Auto-Responder (40s timer)...", 65)
            
            extracted_urls = []
            attempted_postbacks = set()
            start_time = time.time()
            max_wait = 40  # 40 seconds timer
            tid = None
            
            while time.time() - start_time < max_wait:
                elapsed = int(time.time() - start_time)
                progress_cb(f"4/6: Waiting for DM... ({elapsed}s / {max_wait}s)", 65 + int((elapsed / max_wait) * 15))
                
                try:
                    items = []
                    
                    # 1. If we already resolved a tid, try to fetch its latest messages
                    if tid:
                        try:
                            raw_thread = auth_manager.client.private_request(f'direct_v2/threads/{tid}/?limit=20')
                            items = raw_thread.get('thread', {}).get('items', [])
                        except Exception:
                            tid = None  # Reset if thread became inaccessible
                    
                    # 2. If no tid or no items, scan active primary inbox first
                    if not tid or not items:
                        try:
                            raw_inbox = auth_manager.client.private_request('direct_v2/inbox/?limit=10')
                            threads = raw_inbox.get('inbox', {}).get('threads', [])
                            for t in threads:
                                if any(u.get('username', '').lower() == creator_username.lower() or str(u.get('pk')) == str(creator.pk) for u in t.get('users', [])):
                                    tid = t.get('thread_id')
                                    items = t.get('items', [])
                                    break
                        except Exception:
                            pass

                    # 3. Check Pending Inbox (Message Requests) in case creator bot routed there
                    if not tid or not items:
                        try:
                            raw_pending = auth_manager.client.private_request('direct_v2/pending_inbox/?limit=10')
                            pending_threads = raw_pending.get('inbox', {}).get('threads', [])
                            for pt in pending_threads:
                                if any(u.get('username', '').lower() == creator_username.lower() or str(u.get('pk')) == str(creator.pk) for u in pt.get('users', [])):
                                    tid = pt.get('thread_id')
                                    # Approve pending thread to ensure messages are accessible
                                    try:
                                        auth_manager.client.direct_pending_approve(tid)
                                    except Exception:
                                        pass
                                    items = pt.get('items', [])
                                    break
                        except Exception:
                            pass
                    
                    # 4. Fallback to direct thread by participants
                    if not tid:
                        try:
                            thread_data = auth_manager.client.direct_thread_by_participants([creator.pk])
                            thread_info = thread_data.get('thread', thread_data) if isinstance(thread_data, dict) else {}
                            tid = thread_info.get('thread_id')
                            if tid:
                                raw_thread = auth_manager.client.private_request(f'direct_v2/threads/{tid}/?limit=20')
                                items = raw_thread.get('thread', {}).get('items', [])
                        except Exception:
                            pass

                    for item in items:
                        # Filter out messages sent by viewer (us)
                        if item.get('is_sent_by_viewer') is True:
                            continue

                        # Extract any valid URLs from this message
                        item_urls = extract_urls_from_item(item)
                        for u in item_urls:
                            if u not in extracted_urls:
                                extracted_urls.append(u)
                                console.print(f"[bold green][URL EXTRACTED] Found resource link: {u}[/bold green]")

                        # Handle Interactive CTA Buttons / Postbacks (ManyChat / Cosmofeed / Auto-Responders)
                        xma_sources = []
                        if isinstance(item.get('generic_xma'), list):
                            xma_sources.extend(item['generic_xma'])
                        elif isinstance(item.get('generic_xma'), dict):
                            xma_sources.append(item['generic_xma'])
                        if isinstance(item.get('xma'), list):
                            xma_sources.extend(item['xma'])
                        elif isinstance(item.get('xma'), dict):
                            xma_sources.append(item['xma'])

                        for xma in xma_sources:
                            if not isinstance(xma, dict):
                                continue
                            for btn in xma.get('cta_buttons', []):
                                if not isinstance(btn, dict):
                                    continue
                                btn_title = btn.get('title', '') or btn.get('text', '')
                                btn_payload = btn.get('action_payload', '') or btn.get('action_url', '')

                                # Direct check: Does the button have a direct destination URL?
                                btn_url = (clean_and_resolve_url(btn.get('action_url')) or 
                                           clean_and_resolve_url(btn.get('target_url')) or 
                                           clean_and_resolve_url(btn.get('url')))
                                if btn_url and btn_url not in extracted_urls:
                                    extracted_urls.append(btn_url)
                                    console.print(f"[bold green][BUTTON URL CAPTURED] '{btn_title}': {btn_url}[/bold green]")

                                # If it's an unclicked postback button, trigger it properly
                                elif btn_title and btn_title not in attempted_postbacks:
                                    console.print(f"[bold cyan][BUTTON DETECTED] Auto-clicking DM button: '{btn_title}'...[/bold cyan]")
                                    attempted_postbacks.add(btn_title)
                                    
                                    # Method A: Instagram Native Postback Broadcast
                                    try:
                                        token = auth_manager.client.generate_mutation_token()
                                        pb_kwargs = {
                                            "action": "send_item",
                                            "thread_ids": json.dumps([int(tid)]) if tid else "[]",
                                            "client_context": token,
                                            "mutation_token": token,
                                            "device_id": getattr(auth_manager.client, 'android_device_id', None) or auth_manager.client.generate_uuid(),
                                            "_uuid": auth_manager.client.uuid,
                                            "postback_action_text": btn_title,
                                            "postback_action_payload": btn_payload or btn_title,
                                            "nav_chain": "1qT:feed_timeline:1,7Az:direct_inbox:4,5rG:direct_thread:7",
                                            "offline_threading_id": token,
                                        }
                                        auth_manager.client.private_request(
                                            'direct_v2/threads/broadcast/postback/',
                                            data=auth_manager.client.with_default_data(pb_kwargs),
                                            with_signature=False
                                        )
                                        console.print(f"[green][OK] Triggered postback for '{btn_title}'![/green]")
                                    except Exception as pb_err:
                                        console.print(f"[yellow]Postback broadcast note: {pb_err}[/yellow]")
                                        # Method B: Quick-Reply Text fallback
                                        try:
                                            auth_manager.client.direct_send(btn_title, thread_ids=[tid])
                                            console.print(f"[green][OK] Sent quick-reply text '{btn_title}'[/green]")
                                        except Exception:
                                            pass

                    extracted_urls = list(set(extracted_urls))
                    if extracted_urls:
                        progress_cb(f"[OK] DM Received & {len(extracted_urls)} Link(s) Captured!", 80)
                        break
                except Exception as err:
                    console.print(f"[yellow]DM Poll note: {err}[/yellow]")

                if extracted_urls:
                    break
                    
                time.sleep(1.5) # Fast 1.5s polling loop

            # Fallback Check: Creator Profile Bio Link (If DM did not yield links)
            if not extracted_urls:
                progress_cb("Checking creator profile bio link as fallback...", 82)
                try:
                    u_info = auth_manager.client.user_info(creator.pk)
                    bio_link = getattr(u_info, 'external_url', '') or ''
                    if bio_link:
                        clean_bio = clean_and_resolve_url(bio_link)
                        if clean_bio:
                            console.print(f"[bold cyan][BIO LINK CAPTURED] Creator bio link fallback: {clean_bio}[/bold cyan]")
                            extracted_urls.append(clean_bio)
                except Exception as bio_err:
                    console.print(f"[yellow]Bio link fallback note: {bio_err}[/yellow]")

            # Step 5: Scrape Extracted Resources
            progress_cb(f"5/6: Found {len(extracted_urls)} link(s). Scraping resource contents...", 85)
            resources_data = []
            for url in extracted_urls:
                data = self.scrape_url(url)
                if data:
                    resources_data.append(data)

            # Step 6: Maintain Cumulative JSON History & Generate Consolidated PDF Document
            progress_cb("6/6: Updating Cumulative History & PDF Document...", 95)
            
            from pathlib import Path
            history_file = Path(__file__).parent / "history.json"
            
            history_data = []
            if history_file.exists():
                try:
                    with open(history_file, "r", encoding="utf-8") as h_f:
                        history_data = json.load(h_f)
                except Exception:
                    pass

            profile_pic_url = str(getattr(creator, 'profile_pic_url', '') or getattr(creator, 'profile_pic_url_hd', '') or '')
            # Append new entry
            history_data.append({
                "creator": creator_username,
                "profile_pic": profile_pic_url,
                "reel_url": reel_url,
                "caption": summary_caption,
                "resources": resources_data
            })

            # Save back to history.json
            try:
                with open(history_file, "w", encoding="utf-8") as h_f:
                    json.dump(history_data, h_f, indent=4)
            except Exception as write_json_err:
                console.print(f"[yellow]History JSON save note: {write_json_err}[/yellow]")

            # Regenerate consolidated PDF
            pdf_filename = "consolidated_report.pdf"
            generated_pdf_name = generate_cumulative_pdf(pdf_filename, history_data)

            # Schedule 5-Minute Auto-Delete / Hide DM Thread Background Task
            if 'tid' in locals() and tid:
                import threading
                def auto_delete_thread_task(thread_id_to_delete: str, username_to_clean: str):
                    time.sleep(300.0) # Wait 5 minutes (300s)
                    try:
                        auth_manager.client.direct_thread_hide(thread_id_to_delete)
                        console.print(f"[dim green][OK] Auto-cleaned DM thread for @{username_to_clean} after 5 minutes.[/dim green]")
                    except Exception as clean_err:
                        console.print(f"[dim yellow]Auto-clean note: {clean_err}[/dim yellow]")

                t = threading.Thread(target=auto_delete_thread_task, args=(tid, creator_username), daemon=True)
                t.start()

            progress_cb("Complete! Consolidated PDF Ready for Download. (DM thread queued to auto-clean in 5 mins)", 100)

            return {
                "status": "success",
                "creator": creator_username,
                "reel_url": reel_url,
                "extracted_urls": extracted_urls,
                "pdf_filename": generated_pdf_name,
                "download_url": f"/downloads/{generated_pdf_name}"
            }
        finally:
            if comment_id:
                console.print(f"[yellow]Auto-cleaning trigger comment (ID: {comment_id}) to leave no traces...[/yellow]")
                try:
                    auth_manager.client.comment_bulk_delete(media_id, [comment_id])
                    console.print("[bold green][OK] Trigger comment cleaned successfully![/bold green]")
                except Exception as del_err:
                    console.print(f"[dim yellow]Could not auto-clean trigger comment: {del_err}[/dim yellow]")

pipeline = ReelHarvestPipeline()

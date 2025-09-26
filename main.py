import json
import time
import os
import sys
import signal
import logging
from datetime import datetime, timezone
from pathlib import Path

from discord_ipc import DiscordIPC  # Use our custom IPC implementation
import trakt
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID")
TRAKT_CLIENT_SECRET = os.getenv("TRAKT_CLIENT_SECRET")
TRAKT_APPLICATION_ID = os.getenv("TRAKT_APPLICATION_ID")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")

# Daemon mode configuration
DAEMON_MODE = "--daemon" in sys.argv or os.getenv("DAEMON_MODE") == "1"
BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "trakt-discord.log"
LOCAL_TOKEN_FILE = BASE_DIR / ".pytrakt.json"
HOME_TOKEN_FILE = Path.home() / ".pytrakt.json"
TOKEN_FILES = (LOCAL_TOKEN_FILE, HOME_TOKEN_FILE)

CURRENT_ACTIVITY_STATE = {
    "item_key": None,
    "start_timestamp": None,
    "raw_started_at": None,
}

# --- Logging Setup ---
def setup_logging():
    """Setup logging for daemon or interactive mode."""
    log_level = logging.INFO
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    if DAEMON_MODE:
        # File logging for daemon mode
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler()  # Still log to stdout for systemd
            ]
        )
    else:
        # Console logging for interactive mode
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[logging.StreamHandler()]
        )
    
    return logging.getLogger(__name__)

logger = setup_logging()

# --- Signal Handlers ---
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name} signal, shutting down gracefully...")
    shutdown_requested = True
    # Raising KeyboardInterrupt lets us break out of blocking calls (e.g. input())
    raise KeyboardInterrupt

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
# --- End Configuration ---

def _apply_trakt_tokens(token_data):
    """Push token data into trakt.core globals."""
    trakt.core.CLIENT_ID = token_data.get('CLIENT_ID')
    trakt.core.CLIENT_SECRET = token_data.get('CLIENT_SECRET')
    trakt.core.OAUTH_TOKEN = token_data.get('OAUTH_TOKEN')
    trakt.core.OAUTH_REFRESH = token_data.get('OAUTH_REFRESH')
    trakt.core.OAUTH_EXPIRES_AT = token_data.get('OAUTH_EXPIRES_AT')
    if token_data.get('APPLICATION_ID'):
        trakt.core.APPLICATION_ID = token_data['APPLICATION_ID']


def _persist_token_data(token_data):
    """Persist the provided token data to all known token files."""
    serialized = json.dumps(token_data)
    for path in TOKEN_FILES:
        try:
            path.write_text(serialized)
        except Exception as err:
            logger.debug(f"Unable to write token file {path}: {err}")


def persist_current_tokens():
    """Capture the active trakt.core tokens and persist them to disk."""
    token_data = {
        'APPLICATION_ID': getattr(trakt.core, 'APPLICATION_ID', TRAKT_APPLICATION_ID),
        'CLIENT_ID': getattr(trakt.core, 'CLIENT_ID', TRAKT_CLIENT_ID),
        'CLIENT_SECRET': getattr(trakt.core, 'CLIENT_SECRET', TRAKT_CLIENT_SECRET),
        'OAUTH_TOKEN': getattr(trakt.core, 'OAUTH_TOKEN', None),
        'OAUTH_REFRESH': getattr(trakt.core, 'OAUTH_REFRESH', None),
        'OAUTH_EXPIRES_AT': getattr(trakt.core, 'OAUTH_EXPIRES_AT', None),
    }

    if not token_data['OAUTH_TOKEN']:
        return

    expires_ts = _normalize_timestamp(token_data['OAUTH_EXPIRES_AT'])
    token_data['OAUTH_EXPIRES_AT'] = expires_ts
    _persist_token_data(token_data)


def load_stored_tokens():
    """Load tokens from disk (local or home) and apply the freshest valid set."""
    candidates = []

    for path in TOKEN_FILES:
        if not path.exists():
            continue
        try:
            with path.open('r') as f:
                token_data = json.load(f)
            if not isinstance(token_data, dict):
                continue
        except Exception as err:
            logger.debug(f"Could not read token file {path}: {err}")
            continue

        expires_raw = token_data.get('OAUTH_EXPIRES_AT')
        expires_ts = _normalize_timestamp(expires_raw)
        candidates.append({
            'path': path,
            'data': token_data,
            'expires_ts': expires_ts,
            'expires_raw': expires_raw,
        })

    if not candidates:
        return False

    now = int(time.time())
    BUFFER = 300

    # Sort by expiry (descending) so newest/longest-lived tokens come first
    candidates.sort(key=lambda c: c['expires_ts'] or 0, reverse=True)

    for candidate in candidates:
        token_data = candidate['data']

        if 'OAUTH_TOKEN' not in token_data or not token_data['OAUTH_TOKEN']:
            continue

        expires_ts = candidate['expires_ts']
        if expires_ts is not None and now >= (expires_ts - BUFFER):
            logger.info(f"Stored tokens in {candidate['path'].name} are expired")
            continue

        _apply_trakt_tokens(token_data)
        print("Loaded stored tokens successfully")

        # Keep both token files in sync with the working copy
        _persist_token_data({
            'APPLICATION_ID': token_data.get('APPLICATION_ID', TRAKT_APPLICATION_ID),
            'CLIENT_ID': token_data.get('CLIENT_ID'),
            'CLIENT_SECRET': token_data.get('CLIENT_SECRET'),
            'OAUTH_TOKEN': token_data.get('OAUTH_TOKEN'),
            'OAUTH_REFRESH': token_data.get('OAUTH_REFRESH'),
            'OAUTH_EXPIRES_AT': expires_ts if expires_ts is not None else token_data.get('OAUTH_EXPIRES_AT'),
        })

        return True

    return False

def authenticate_trakt():
    """
    Handles Trakt.tv authentication with automatic token loading and PIN fallback.
    """
    print("Authenticating with Trakt.tv...")
    logger.info("Authenticating with Trakt.tv...")

    # Set the application ID first
    trakt.core.APPLICATION_ID = TRAKT_APPLICATION_ID

    # Try to load existing tokens first
    if load_stored_tokens():
        try:
            # Test if the loaded tokens work by making an API call
            # Use get_user_settings instead of last_activities
            from trakt.users import get_user_settings
            test_call = get_user_settings()
            print("Successfully authenticated using stored tokens!")
            return True
        except Exception as e:
            print(f"Stored tokens failed verification: {e}")
            print("Falling back to PIN authentication...")

    # If stored tokens don't work or don't exist, use PIN authentication
    try:
        print("Starting PIN authentication...")
        trakt.init(client_id=TRAKT_CLIENT_ID, client_secret=TRAKT_CLIENT_SECRET, store=True)
        persist_current_tokens()
        # Reload from disk once so we normalize timestamps and sync both token files
        load_stored_tokens()
        print("PIN authentication successful!")
        return True

    except Exception as e:
        print(f"PIN authentication failed: {e}")
        return False

def get_watching_status():
    """
    Fetches the current watching status from Trakt.tv.
    Uses User('me').watching to get live check-in status.
    Returns the currently watching episode/movie or None.
    """
    try:
        from trakt.users import User

        # Get the current user and check what they're watching
        user_me = User('me')
        watching = user_me.watching

        if watching:
            print(f"Currently watching: {watching}")
            return watching
        else:
            print("Not currently checked in to anything")
            return None

    except Exception as e:
        print(f"Error getting watching status: {e}")
        return None

def get_poster_url(watching_item):
    """
    Get poster URL for the currently watching show/movie.
    Returns a valid URL string or None if not available.
    """
    try:
        # For TV episodes, get the show poster by searching for the show
        if hasattr(watching_item, 'show') and watching_item.show:
            show_title = str(watching_item.show)

            # Search for the show to get full object with TMDB ID
            try:
                from trakt.tv import search
                search_results = search(show_title, search_type='show')
                if search_results and len(search_results) > 0:
                    show_obj = search_results[0]  # Take first/best match

                    # Try TMDB poster URL first (best quality)
                    if hasattr(show_obj, 'tmdb') and show_obj.tmdb:
                        # Use TMDB API v3 poster URL format
                        # Note: This requires the poster_path from TMDB API, but we'll try a common approach
                        # For now, let's use Trakt's poster if TMDB doesn't work
                        pass

                    # Use Trakt's poster images
                    if hasattr(show_obj, 'images') and show_obj.images:
                        extracted = extract_image_url(show_obj.images)
                        if extracted:
                            return extracted

            except Exception as e:
                print(f"Error searching for show: {e}")

            # Fallback: try to extract from episode images
            if hasattr(watching_item, 'images') and watching_item.images:
                return extract_image_url(watching_item.images)

        # For movies, try episode/movie TMDB ID
        elif hasattr(watching_item, 'tmdb') and watching_item.tmdb:
            # For movies, we could use TMDB API but for now use Trakt images
            pass

        # Final fallback: try any images on the item
        if hasattr(watching_item, 'images') and watching_item.images:
            return extract_image_url(watching_item.images)

        if hasattr(watching_item, 'images_ext') and watching_item.images_ext:
            return extract_image_url(watching_item.images_ext)

        return None

    except Exception as e:
        print(f"Error getting poster URL: {e}")
        return None

def extract_image_url(image_data):
    """
    Extract a usable URL string from Trakt's image data structure.
    Prioritizes posters over screenshots for better visuals.
    """
    try:
        if isinstance(image_data, str):
            # Already a string URL
            return image_data if image_data.startswith('http') else f"https://{image_data}"
        elif isinstance(image_data, dict):
            # Look for poster images first (best for shows), then other types
            image_types = ['poster', 'thumb', 'fanart', 'screenshot']

            for img_type in image_types:
                if img_type in image_data:
                    img_value = image_data[img_type]

                    if isinstance(img_value, list) and len(img_value) > 0:
                        url = img_value[0]
                        return url if url.startswith('http') else f"https://{url}"
                    elif isinstance(img_value, str):
                        return img_value if img_value.startswith('http') else f"https://{img_value}"

            # If it's a dict, try to get any URL-like value
            for key, value in image_data.items():
                if isinstance(value, list) and len(value) > 0:
                    url = str(value[0])
                    if any(ext in url for ext in ['.jpg', '.png', '.webp', '.jpeg']):
                        return url if url.startswith('http') else f"https://{url}"
                elif isinstance(value, str) and any(ext in value for ext in ['.jpg', '.png', '.webp', '.jpeg', 'http']):
                    return value if value.startswith('http') else f"https://{value}"

        return None
    except Exception as e:
        print(f"Error extracting image URL: {e}")
        return None


def _normalize_timestamp(value):
    """Return a Unix timestamp (seconds) parsed from various value shapes."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(candidate)
        except ValueError:
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S%z"):
                try:
                    dt = datetime.strptime(candidate, fmt)
                    break
                except ValueError:
                    continue
            else:
                return None
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return int(dt.timestamp())


def _estimate_start_from_progress(watching_item):
    """Estimate start timestamp and report progress percentage if possible."""
    try:
        progress = getattr(watching_item, "progress", None)
        progress = float(progress) if progress is not None else None
    except (TypeError, ValueError):
        progress = None

    if not progress or progress <= 0:
        return None

    runtime = getattr(watching_item, "runtime", None)

    if runtime is None and hasattr(watching_item, "show") and watching_item.show:
        runtime = getattr(watching_item.show, "runtime", None)

    try:
        runtime = float(runtime) if runtime is not None else None
    except (TypeError, ValueError):
        runtime = None

    if not runtime or runtime <= 0:
        return None

    # Trakt runtimes are expressed in minutes; convert to seconds
    seconds_elapsed = int(runtime * 60 * (progress / 100.0))
    if seconds_elapsed < 0:
        return None

    start_timestamp = max(int(time.time()) - seconds_elapsed, 0)
    return start_timestamp, progress


def _build_activity_key(watching_item):
    """Construct a stable identifier for the currently playing item."""
    if not watching_item:
        return None

    ids = getattr(watching_item, "ids", None)
    trakt_id = None

    if isinstance(ids, dict):
        trakt_id = ids.get("trakt") or ids.get("slug") or ids.get("imdb")
    elif ids is not None:
        trakt_id = getattr(ids, "trakt", None) or getattr(ids, "slug", None) or getattr(ids, "imdb", None)

    if trakt_id:
        prefix = "episode" if hasattr(watching_item, "show") and watching_item.show else "movie"
        return f"{prefix}:{trakt_id}"

    if hasattr(watching_item, "show") and watching_item.show:
        show_obj = watching_item.show
        show_title = None
        if callable(getattr(show_obj, "title", None)):
            try:
                show_title = show_obj.title()
            except Exception:
                show_title = None
        if show_title is None:
            show_title = getattr(show_obj, "title", None)
        season = getattr(watching_item, "season", "?")
        number = getattr(watching_item, "number", "?")
        return f"episode:{show_title}:{season}:{number}"

    title = getattr(watching_item, "title", None)
    year = getattr(watching_item, "year", None)
    if title:
        return f"movie:{title}:{year}"

    return str(watching_item)


def _resolve_activity_start(watching_item, item_key):
    """Determine the correct start timestamp for Discord presence updates."""
    candidate_attrs = ("started_at", "watched_at", "last_watched_at")
    start_timestamp = None
    raw_source = None

    estimate = _estimate_start_from_progress(watching_item)
    if estimate is not None:
        start_timestamp, progress_value = estimate
        raw_source = ("progress", progress_value)

    if start_timestamp is None:
        for attr in candidate_attrs:
            value = getattr(watching_item, attr, None)
            ts = _normalize_timestamp(value)
            if ts is not None:
                start_timestamp = ts
                raw_source = (attr, value)
                break

    # If we have progress data we always prefer that so Discord reflects position
    if raw_source and raw_source[0] == "progress":
        CURRENT_ACTIVITY_STATE.update(
            item_key=item_key,
            start_timestamp=start_timestamp,
            raw_started_at=raw_source,
        )
        return start_timestamp

    previous_state_matches = (
        CURRENT_ACTIVITY_STATE["item_key"] == item_key
        and CURRENT_ACTIVITY_STATE["start_timestamp"] is not None
    )

    if previous_state_matches:
        previous_raw = CURRENT_ACTIVITY_STATE.get("raw_started_at")
        if raw_source is None or raw_source == previous_raw:
            return CURRENT_ACTIVITY_STATE["start_timestamp"]

    if start_timestamp is None:
        start_timestamp = int(time.time())

    CURRENT_ACTIVITY_STATE.update(
        item_key=item_key,
        start_timestamp=start_timestamp,
        raw_started_at=raw_source,
    )

    return start_timestamp


def _reset_activity_state():
    """Clear the cached activity information when nothing is playing."""
    CURRENT_ACTIVITY_STATE.update(item_key=None, start_timestamp=None, raw_started_at=None)

def connect_to_discord():
    """
    Attempts to connect to Discord Rich Presence using custom IPC.
    Returns (rpc_client, success_bool)
    """
    try:
        print("Attempting Discord connection...")
        rpc = DiscordIPC(DISCORD_CLIENT_ID)
        rpc.connect()
        print("Connected to Discord Rich Presence.")
        return rpc, True
    except Exception as e:
        print(f"Could not connect to Discord: {e}")
        print("Will continue without Discord and retry later...")
        return None, False

def update_discord_presence_with_reconnect(rpc_container, watching_item):
    """
    Updates Discord Rich Presence with automatic reconnection handling.
    Uses "Watching" activity type with dynamic poster artwork.
    """
    if not rpc_container[0]:
        # No connection, try to reconnect
        print("No Discord connection, attempting to reconnect...")
        rpc_container[0], connected = connect_to_discord()
        if not connected:
            return False

    if watching_item:
        details = ""
        state = ""

        item_key = _build_activity_key(watching_item)
        start_time = _resolve_activity_start(watching_item, item_key)

        # Get poster artwork
        poster_url = get_poster_url(watching_item)
        large_image = poster_url if poster_url else "trakt_logo"
        small_image = "trakt_logo"  # Always show Trakt logo in corner

        # Check if it's a TV episode or movie
        if hasattr(watching_item, 'show') and watching_item.show:
            # This is a TV episode
            show_title = watching_item.show.title() if callable(watching_item.show.title) else watching_item.show.title
            details = show_title  # Main title is just the show name

            season = getattr(watching_item, 'season', '?')
            number = getattr(watching_item, 'number', '?')
            episode_title = getattr(watching_item, 'title', 'Unknown Episode')

            state = f"S{season:02d}E{number:02d} - {episode_title}"

        elif hasattr(watching_item, 'title'):
            # This is likely a movie
            details = watching_item.title
            if hasattr(watching_item, 'year') and watching_item.year:
                state = f"({watching_item.year})"

        print(f"Updating Discord: {details} - {state}")
        if poster_url:
            print(f"Using poster: {poster_url}")

        try:
            rpc_container[0].update(
                details=details,
                state=state,
                large_image=large_image,
                large_text=f"Watching on Trakt.tv",
                small_image=small_image,
                small_text="Trakt.tv",
                start=start_time,
                activity_type=3  # 3 = WATCHING activity type
            )
            return True
        except Exception as e:
            print(f"Failed to update Discord presence: {e}")
            # Check if it's a connection error and reset connection
            print("Discord connection may be lost, will attempt to reconnect on next update...")
            try:
                rpc_container[0].close()
            except:
                pass
            rpc_container[0] = None
            return False
    else:
        print("Not watching anything. Clearing Discord presence.")
        _reset_activity_state()
        try:
            rpc_container[0].clear()
            return True
        except Exception as e:
            print(f"Failed to clear Discord presence: {e}")
            # Check if it's a connection error and reset connection
            print("Discord connection may be lost, will attempt to reconnect on next update...")
            try:
                rpc_container[0].close()
            except:
                pass
            rpc_container[0] = None
            return False

def main():
    """
    Main function to initialize and run the application.
    """
    if not all([TRAKT_CLIENT_ID, TRAKT_CLIENT_SECRET, DISCORD_CLIENT_ID]):
        print("Error: Please ensure TRAKT_CLIENT_ID, TRAKT_CLIENT_SECRET, and DISCORD_CLIENT_ID are set in your .env file.")
        return

    if not authenticate_trakt():
        return

    # Initial Discord connection attempt
    rpc_client, connected = connect_to_discord()
    if not connected:
        print("Warning: Could not connect to Discord initially. Will keep trying...")

    # Use a list container so we can modify the connection from within functions
    rpc_container = [rpc_client]

    try:
        print("Starting monitoring loop...")
        consecutive_failures = 0

        while not shutdown_requested:
            watching_status = get_watching_status()
            success = update_discord_presence_with_reconnect(rpc_container, watching_status)

            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    print("Multiple Discord connection failures. Discord may not be running.")
                    print("Will continue trying to reconnect...")
                    # Add a longer delay after multiple failures
                    time.sleep(30)
                    consecutive_failures = 0
                    continue

            # Check for new status every 15 seconds
            for _ in range(15):
                if shutdown_requested:
                    break
                time.sleep(1)

        if shutdown_requested:
            print("Shutdown requested. Exiting monitoring loop...")

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Clean up Discord connection if it exists
        if rpc_container[0]:
            try:
                rpc_container[0].close()
                print("Discord connection closed.")
            except:
                pass

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code if exit_code is not None else 0)

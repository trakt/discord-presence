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
from types import SimpleNamespace

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID")
TRAKT_CLIENT_SECRET = os.getenv("TRAKT_CLIENT_SECRET")
TRAKT_APPLICATION_ID = os.getenv("TRAKT_APPLICATION_ID")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
LOG_LEVEL_NAME = (os.getenv("LOG_LEVEL") or "INFO").strip()

# Daemon mode configuration
DAEMON_MODE = "--daemon" in sys.argv or os.getenv("DAEMON_MODE") == "1"
BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "trakt-discord.log"
LOCAL_TOKEN_FILE = BASE_DIR / ".pytrakt.json"
HOME_TOKEN_FILE = Path.home() / ".pytrakt.json"
TOKEN_FILES = (LOCAL_TOKEN_FILE, HOME_TOKEN_FILE)
PID_FILE = BASE_DIR / "discord_presence.pid"

CURRENT_ACTIVITY_STATE = {
    "item_key": None,
    "start_timestamp": None,
    "raw_started_at": None,
}

TOKEN_RUNTIME_STATE = {
    "issued_at": None,
    "expires_at": None,
}

# Default Trakt tokens currently expire after 7 days; use that as the fallback window.
DEFAULT_TOKEN_LIFETIME_SECONDS = 7 * 24 * 60 * 60
TOKEN_REFRESH_THRESHOLD = 0.8
TOKEN_REFRESH_BUFFER_SECONDS = 300  # 5 minutes grace window

# --- Logging Setup ---


def _resolve_log_level(name):
    """Resolve log level names or numeric strings to logging constants."""
    if not name:
        return logging.INFO

    candidate = str(name).strip()
    if not candidate:
        return logging.INFO

    upper = candidate.upper()
    if hasattr(logging, upper):
        level = getattr(logging, upper)
        if isinstance(level, int):
            return level

    try:
        numeric_level = int(candidate)
        return numeric_level
    except ValueError:
        pass

    logging.getLogger("discord_presence").warning(
        "Unrecognized LOG_LEVEL '%s', defaulting to INFO", name
    )
    return logging.INFO


def setup_logging():
    """Setup logging for daemon or interactive mode."""
    log_level = _resolve_log_level(LOG_LEVEL_NAME)
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


def _is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we might not own it
        return True
    except OSError:
        return False
    return True


def acquire_single_instance() -> bool:
    """Ensure only one instance of the bot runs at a time."""
    try:
        if PID_FILE.exists():
            existing_pid = int(PID_FILE.read_text().strip() or 0)
            if _is_process_running(existing_pid) and existing_pid != os.getpid():
                logger.error(
                    "Another Discord Presence instance is already running (PID %s). Exiting.",
                    existing_pid,
                )
                return False
        PID_FILE.write_text(str(os.getpid()))
        return True
    except Exception as err:
        logger.error("Unable to acquire single-instance lock: %s", err)
        return False


def release_single_instance():
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception as err:
        logger.debug("Failed to remove PID file: %s", err)


def _namespace(payload):
    if isinstance(payload, dict):
        return SimpleNamespace(**{key: _namespace(value) for key, value in payload.items()})
    if isinstance(payload, list):
        return [_namespace(item) for item in payload]
    return payload

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
    issued_at = token_data.get('OAUTH_ISSUED_AT')
    if issued_at is not None:
        setattr(trakt.core, 'OAUTH_ISSUED_AT', issued_at)
    if token_data.get('APPLICATION_ID'):
        trakt.core.APPLICATION_ID = token_data['APPLICATION_ID']

    trakt.core.config().update(
        APPLICATION_ID=token_data.get('APPLICATION_ID', TRAKT_APPLICATION_ID),
        CLIENT_ID=token_data.get('CLIENT_ID'),
        CLIENT_SECRET=token_data.get('CLIENT_SECRET'),
        OAUTH_TOKEN=token_data.get('OAUTH_TOKEN'),
        OAUTH_REFRESH=token_data.get('OAUTH_REFRESH'),
        OAUTH_EXPIRES_AT=token_data.get('OAUTH_EXPIRES_AT'),
    ).store()

    _set_runtime_token_state(issued_at, token_data.get('OAUTH_EXPIRES_AT'))


def _set_runtime_token_state(issued_at, expires_at):
    if issued_at is not None:
        TOKEN_RUNTIME_STATE['issued_at'] = issued_at
    if expires_at is not None:
        TOKEN_RUNTIME_STATE['expires_at'] = expires_at


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
    config = trakt.core.config()
    config.load()

    token_data = {
        'APPLICATION_ID': config.get('APPLICATION_ID', TRAKT_APPLICATION_ID),
        'CLIENT_ID': config.get('CLIENT_ID') or TRAKT_CLIENT_ID,
        'CLIENT_SECRET': config.get('CLIENT_SECRET') or TRAKT_CLIENT_SECRET,
        'OAUTH_TOKEN': config.get('OAUTH_TOKEN'),
        'OAUTH_REFRESH': config.get('OAUTH_REFRESH'),
        'OAUTH_EXPIRES_AT': config.get('OAUTH_EXPIRES_AT'),
    }

    if not token_data['OAUTH_TOKEN']:
        return

    expires_ts = _normalize_timestamp(token_data['OAUTH_EXPIRES_AT'])
    token_data['OAUTH_EXPIRES_AT'] = expires_ts

    issued_ts = _normalize_timestamp(getattr(trakt.core, 'OAUTH_ISSUED_AT', None))
    if issued_ts is None:
        issued_ts = int(time.time()) if expires_ts is not None else None
    if issued_ts is not None:
        token_data['OAUTH_ISSUED_AT'] = issued_ts

    _apply_trakt_tokens(token_data)
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

    # Sort by expiry (descending) so newest/longest-lived tokens come first
    candidates.sort(key=lambda c: c['expires_ts'] or 0, reverse=True)

    for candidate in candidates:
        token_data = candidate['data']

        if not token_data.get('OAUTH_TOKEN'):
            continue

        expires_ts = candidate['expires_ts']
        issued_ts = _resolve_issued_at(token_data, expires_ts)
        token_data['OAUTH_EXPIRES_AT'] = expires_ts
        if issued_ts is not None:
            token_data['OAUTH_ISSUED_AT'] = issued_ts

        _apply_trakt_tokens(token_data)

        should_refresh = False
        if expires_ts is None:
            should_refresh = False
        else:
            remaining = expires_ts - now
            lifetime = expires_ts - issued_ts if issued_ts is not None else DEFAULT_TOKEN_LIFETIME_SECONDS
            if lifetime <= 0:
                lifetime = DEFAULT_TOKEN_LIFETIME_SECONDS
            progress = (lifetime - max(remaining, 0)) / float(lifetime)
            if remaining <= TOKEN_REFRESH_BUFFER_SECONDS or progress >= TOKEN_REFRESH_THRESHOLD:
                should_refresh = True

        if should_refresh and token_data.get('OAUTH_REFRESH'):
            logger.info("Stored tokens nearing expiry, attempting proactive refresh...")
            if maybe_refresh_tokens(force=True):
                logger.info("Loaded stored tokens successfully")
                return True
            logger.warning("Automatic refresh attempt failed, will fall back to next credential")
            continue

        if expires_ts is not None and expires_ts - now <= 0:
            logger.info(f"Stored tokens in {candidate['path'].name} are expired")
            continue

        logger.info("Loaded stored tokens successfully")
        _persist_token_data(token_data)
        return True

    return False


def maybe_refresh_tokens(force=False):
    """Refresh the Trakt token if it is close to expiring."""
    expires_at = TOKEN_RUNTIME_STATE.get('expires_at')
    issued_at = TOKEN_RUNTIME_STATE.get('issued_at')

    if expires_at is None:
        expires_at = _normalize_timestamp(getattr(trakt.core, 'OAUTH_EXPIRES_AT', None))
    if issued_at is None:
        issued_at = _normalize_timestamp(getattr(trakt.core, 'OAUTH_ISSUED_AT', None))

    now = int(time.time())
    needs_refresh = force

    if not needs_refresh and expires_at is not None:
        lifetime = expires_at - issued_at if issued_at is not None else DEFAULT_TOKEN_LIFETIME_SECONDS
        if lifetime <= 0:
            lifetime = DEFAULT_TOKEN_LIFETIME_SECONDS
        elapsed = now - (issued_at if issued_at is not None else expires_at - lifetime)
        if elapsed < 0:
            elapsed = 0
        progress = elapsed / float(lifetime) if lifetime else 1.0
        remaining = expires_at - now

        if remaining <= TOKEN_REFRESH_BUFFER_SECONDS or progress >= TOKEN_REFRESH_THRESHOLD:
            needs_refresh = True

    if not needs_refresh and expires_at is not None and expires_at <= now:
        needs_refresh = True

    if not needs_refresh:
        return False

    token_auth = getattr(trakt.core.api(), 'auth', None)
    if not token_auth or not hasattr(token_auth, 'refresh_token'):
        logger.debug("Token auth refresh is unavailable")
        return False

    try:
        token_auth.refresh_token()
    except Exception as err:
        logger.warning(f"Token refresh failed: {err}")
        return False

    persist_current_tokens()
    logger.info("Token refresh succeeded and credentials persisted.")
    return True

def authenticate_trakt():
    """
    Handles Trakt.tv authentication with automatic token loading and PIN fallback.
    """
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
            logger.info("Successfully authenticated using stored tokens!")
            return True
        except Exception as e:
            logger.warning("Stored tokens failed verification: %s", e)
            logger.info("Falling back to PIN authentication...")

    # If stored tokens don't work or don't exist, use PIN authentication
    try:
        logger.info("Starting PIN authentication...")
        trakt.init(client_id=TRAKT_CLIENT_ID, client_secret=TRAKT_CLIENT_SECRET, store=True)
        persist_current_tokens()
        # Reload from disk once so we normalize timestamps and sync both token files
        load_stored_tokens()
        logger.info("PIN authentication successful!")
        return True

    except Exception as e:
        logger.error("PIN authentication failed: %s", e)
        return False

def get_watching_status():
    """Fetch the current watching status with extended artwork from Trakt."""
    try:
        data = trakt.core.api().get('users/me/watching?extended=full,images')
    except Exception as exc:
        logger.warning("Error getting watching status: %s", exc)
        return None

    if not data:
        logger.debug("Not currently checked in to anything")
        return None

    media_type = data.get('type')
    base = {
        'type': media_type,
        'progress': data.get('progress'),
        'started_at': data.get('started_at'),
        'watched_at': data.get('watched_at'),
        'paused_at': data.get('paused_at'),
        'expires_at': data.get('expires_at'),
    }

    if media_type == 'movie':
        movie = data.get('movie', {}) or {}
        base.update(movie)
        base['movie'] = movie
        logger.debug("Currently watching movie: %s", movie.get('title'))
    elif media_type == 'episode':
        episode = data.get('episode', {}) or {}
        show = data.get('show', {}) or {}
        base.update({
            'title': episode.get('title'),
            'season': episode.get('season'),
            'number': episode.get('number'),
            'ids': episode.get('ids'),
            'episode': episode,
            'show': show,
            'runtime': episode.get('runtime') or show.get('runtime'),
        })
        logger.debug(
            "Currently watching episode: %s S%02dE%02d",
            show.get('title'),
            episode.get('season') or 0,
            episode.get('number') or 0,
        )
    else:
        logger.debug("Watching item type %s", media_type)

    return _namespace(base)

def get_poster_url(watching_item):
    """
    Get poster URL for the currently watching show/movie from extended Trakt images.
    Returns a valid URL string or None if not available.
    """
    try:
        media_type = getattr(watching_item, 'type', None)

        if media_type == 'episode':
            show = getattr(watching_item, 'show', None)
            if show and getattr(show, 'images', None):
                poster = extract_image_url(show.images)
                if poster:
                    return poster

            episode = getattr(watching_item, 'episode', None)
            if episode and getattr(episode, 'images', None):
                poster = extract_image_url(episode.images)
                if poster:
                    return poster

        elif media_type == 'movie':
            movie = getattr(watching_item, 'movie', None)
            if movie and getattr(movie, 'images', None):
                poster = extract_image_url(movie.images)
                if poster:
                    return poster

            if getattr(watching_item, 'images', None):
                poster = extract_image_url(watching_item.images)
                if poster:
                    return poster

        return None

    except Exception as e:
        logger.warning("Error getting poster URL: %s", e)
        return None

def extract_image_url(image_data):
    """
    Extract a usable URL string from Trakt's image data structure.
    Prioritizes posters over screenshots for better visuals.
    """
    try:
        if image_data is None:
            return None

        if isinstance(image_data, SimpleNamespace):
            image_data = vars(image_data)

        if isinstance(image_data, str):
            return _normalize_image_url(image_data)

        if isinstance(image_data, dict):
            image_types = ['poster', 'fanart', 'thumb', 'screenshot']

            for img_type in image_types:
                if img_type not in image_data:
                    continue
                img_value = image_data[img_type]

                if isinstance(img_value, list):
                    for entry in img_value:
                        url = _extract_url_from_entry(entry)
                        if url:
                            return url
                else:
                    url = _extract_url_from_entry(img_value)
                    if url:
                        return url

            for value in image_data.values():
                url = None
                if isinstance(value, list):
                    for entry in value:
                        url = _extract_url_from_entry(entry)
                        if url:
                            break
                else:
                    url = _extract_url_from_entry(value)
                if url:
                    return url

        return None
    except Exception as e:
        logger.debug("Error extracting image URL: %s", e)
        return None


def _extract_url_from_entry(entry):
    if isinstance(entry, str):
        return _normalize_image_url(entry)
    if isinstance(entry, dict):
        for key in ('full', 'medium', 'large', 'thumb', 'original', 'url', 'link'):
            if entry.get(key):
                url = _normalize_image_url(entry[key])
                if url:
                    return url
    return None


def _normalize_image_url(candidate):
    if not candidate:
        return None
    url = str(candidate)
    if not url.startswith('http'):
        url = url.lstrip('/')
        url = f"https://{url}"
    return url


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


def _resolve_issued_at(token_data, expires_ts):
    issued_candidate = token_data.get('OAUTH_ISSUED_AT') or token_data.get('OAUTH_CREATED_AT')
    issued_ts = _normalize_timestamp(issued_candidate)

    if issued_ts is None and expires_ts is not None:
        # Fall back to assuming the default Trakt token lifetime when issuance is unknown
        issued_ts = expires_ts - DEFAULT_TOKEN_LIFETIME_SECONDS

    return issued_ts


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
        logger.info("Attempting Discord connection...")
        rpc = DiscordIPC(DISCORD_CLIENT_ID)
        rpc.connect()
        logger.info("Connected to Discord Rich Presence.")
        return rpc, True
    except Exception as e:
        logger.warning("Could not connect to Discord: %s", e)
        logger.info("Will continue without Discord and retry later...")
        return None, False

def update_discord_presence_with_reconnect(rpc_container, watching_item):
    """
    Updates Discord Rich Presence with automatic reconnection handling.
    Uses "Watching" activity type with dynamic poster artwork.
    """
    if not rpc_container[0]:
        # No connection, try to reconnect
        logger.debug("No Discord connection, attempting to reconnect...")
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

        logger.debug("Updating Discord presence: %s — %s", details, state)
        if poster_url:
            logger.debug("Using poster artwork: %s", poster_url)

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
            logger.warning("Failed to update Discord presence: %s", e)
            # Check if it's a connection error and reset connection
            logger.info("Discord connection may be lost, will attempt to reconnect on next update...")
            try:
                rpc_container[0].close()
            except:
                pass
            rpc_container[0] = None
            return False
    else:
        logger.debug("No active watch detected. Clearing Discord presence.")
        _reset_activity_state()
        try:
            rpc_container[0].clear()
            return True
        except Exception as e:
            logger.warning("Failed to clear Discord presence: %s", e)
            # Check if it's a connection error and reset connection
            logger.info("Discord connection may be lost, will attempt to reconnect on next update...")
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
        logger.error("Missing required credentials. Please set TRAKT_CLIENT_ID, TRAKT_CLIENT_SECRET, and DISCORD_CLIENT_ID in your .env file.")
        return

    has_lock = acquire_single_instance()
    if not has_lock:
        return

    if not authenticate_trakt():
        release_single_instance()
        return

    # Ensure freshly-loaded tokens are healthy before proceeding
    maybe_refresh_tokens()

    # Initial Discord connection attempt
    rpc_client, connected = connect_to_discord()
    if not connected:
        logger.warning("Could not connect to Discord initially. Will keep trying...")

    # Use a list container so we can modify the connection from within functions
    rpc_container = [rpc_client]

    try:
        logger.info("Starting monitoring loop...")
        consecutive_failures = 0

        while not shutdown_requested:
            maybe_refresh_tokens()
            watching_status = get_watching_status()
            success = update_discord_presence_with_reconnect(rpc_container, watching_status)

            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    logger.warning("Multiple Discord connection failures. Discord may not be running.")
                    logger.info("Will continue trying to reconnect...")
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
            logger.info("Shutdown requested. Exiting monitoring loop...")
            try:
                update_discord_presence_with_reconnect(rpc_container, None)
            except Exception as clear_err:
                logger.debug("Failed to clear Discord presence during shutdown: %s", clear_err)

    except KeyboardInterrupt:
        logger.info("Exiting...")
    finally:
        # Clean up Discord connection if it exists
        if rpc_container[0]:
            try:
                rpc_container[0].clear()
                _reset_activity_state()
                logger.debug("Discord presence cleared on shutdown.")
            except Exception as clear_err:
                logger.debug("Failed to clear Discord presence during shutdown: %s", clear_err)
            finally:
                try:
                    rpc_container[0].close()
                    logger.debug("Discord connection closed.")
                except Exception as close_err:
                    logger.debug("Error while closing Discord connection: %s", close_err)
        if has_lock:
            release_single_instance()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code if exit_code is not None else 0)

import time
import os

from pypresence import Presence
import trakt
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID")
TRAKT_CLIENT_SECRET = os.getenv("TRAKT_CLIENT_SECRET")
TRAKT_APPLICATION_ID = os.getenv("TRAKT_APPLICATION_ID")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
# --- End Configuration ---

def load_stored_tokens():
    """
    Load and set tokens directly from .pytrakt.json if they exist and are valid.
    Returns True if successful, False otherwise.
    """
    try:
        import json
        if not os.path.exists(".pytrakt.json"):
            return False
        
        with open(".pytrakt.json", 'r') as f:
            token_data = json.load(f)
        
        required_keys = ['OAUTH_TOKEN', 'OAUTH_REFRESH', 'OAUTH_EXPIRES_AT', 'CLIENT_ID', 'CLIENT_SECRET']
        if not all(key in token_data for key in required_keys):
            return False
        
        # Check if token is expired (with 5 minute buffer)
        expires_at = token_data['OAUTH_EXPIRES_AT']
        current_time = int(time.time())
        if current_time >= (expires_at - 300):  # 5 minute buffer
            print("Stored tokens are expired")
            return False
        
        # Set tokens directly in trakt.core (this is how pytrakt actually works)
        trakt.core.CLIENT_ID = token_data['CLIENT_ID']
        trakt.core.CLIENT_SECRET = token_data['CLIENT_SECRET']
        trakt.core.OAUTH_TOKEN = token_data['OAUTH_TOKEN']
        trakt.core.OAUTH_REFRESH = token_data['OAUTH_REFRESH']
        trakt.core.OAUTH_EXPIRES_AT = token_data['OAUTH_EXPIRES_AT']
        
        print("Loaded stored tokens successfully")
        return True
        
    except Exception as e:
        print(f"Error loading stored tokens: {e}")
        return False

def authenticate_trakt():
    """
    Handles Trakt.tv authentication with automatic token loading and PIN fallback.
    """
    print("Authenticating with Trakt.tv...")
    
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
        print("PIN authentication successful!")
        return True
        
    except Exception as e:
        print(f"PIN authentication failed: {e}")
        return False

def get_watching_status():
    """
    Fetches the current watching status from Trakt.tv.
    Returns the watching object or None.
    """
    try:
        # Use get_playback to get current watching status
        from trakt.sync import get_playback
        playback_entries = get_playback()
        
        # get_playback returns a list, we want the most recent entry
        if playback_entries and len(playback_entries) > 0:
            return playback_entries[0]  # Most recent playback
        else:
            return None
            
    except Exception as e:
        print(f"Error getting watching status: {e}")
        return None

def update_discord_presence(rpc, playback_entry):
    """
    Updates the Discord Rich Presence based on the current Trakt.tv playback status.
    """
    if playback_entry and hasattr(playback_entry, 'media'):
        details = ""
        state = ""

        # Use current time as a placeholder for the start time
        start_time = int(time.time())

        # PlaybackEntry has media attribute that contains movie or episode info
        media = playback_entry.media
        
        if hasattr(media, 'title') and not hasattr(media, 'show'):
            # This is a movie
            details = f"Watching {media.title}"
            if hasattr(media, 'year'):
                state = f"({media.year})"
        elif hasattr(media, 'show'):
            # This is an episode
            show = media.show
            details = f"Watching {show.title}"
            if hasattr(media, 'season') and hasattr(media, 'number'):
                state = f"S{media.season:02d}E{media.number:02d}"
                if hasattr(media, 'title'):
                    state += f" - {media.title}"

        print(f"Updating Discord: {details} - {state}")
        try:
            rpc.update(
                details=details,
                state=state,
                large_image="trakt_logo",
                large_text="Watching on Trakt.tv",
                start=start_time
            )
        except Exception as e:
            print(f"Failed to update Discord presence: {e}")
    else:
        print("Not watching anything. Clearing Discord presence.")
        try:
            rpc.clear()
        except Exception as e:
            print(f"Failed to clear Discord presence: {e}")

def main():
    """
    Main function to initialize and run the application.
    """
    if not all([TRAKT_CLIENT_ID, TRAKT_CLIENT_SECRET, DISCORD_CLIENT_ID]):
        print("Error: Please ensure TRAKT_CLIENT_ID, TRAKT_CLIENT_SECRET, and DISCORD_CLIENT_ID are set in your .env file.")
        return

    if not authenticate_trakt():
        return

    try:
        rpc = Presence(DISCORD_CLIENT_ID)
        rpc.connect()
        print("Connected to Discord Rich Presence.")
    except Exception as e:
        print(f"Could not connect to Discord: {e}")
        print("Please ensure Discord is running and the Discord Client ID is correct.")
        return

    try:
        while True:
            playback_status = get_watching_status()
            update_discord_presence(rpc, playback_status)
            # Check for new status every 15 seconds
            time.sleep(15)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        rpc.close()

if __name__ == "__main__":
    main()

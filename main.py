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

def authenticate_trakt():
    """
    Handles Trakt.tv authentication using pytrakt's init method.
    """
    trakt.core.APPLICATION_ID = TRAKT_APPLICATION_ID
    print("Authenticating with Trakt.tv...")
    try:
        trakt.init(client_id=TRAKT_CLIENT_ID, client_secret=TRAKT_CLIENT_SECRET, store=True)
        print("Trakt.tv authentication successful!")
        return True
    except Exception as e:
        print(f"An error occurred during Trakt.tv authentication: {e}")
        print("Please ensure your TRAKT_CLIENT_ID and TRAKT_CLIENT_SECRET are correct.")
        return False

def get_watching_status():
    """
    Fetches the current watching status from Trakt.tv.
    Returns the watching object or None.
    """
    try:
        # Correct way to get watching status in pytrakt
        watching = trakt.sync.watching()
        return watching
    except Exception as e:
        print(f"Error getting watching status: {e}")
        return None

def update_discord_presence(rpc, watching_data):
    """
    Updates the Discord Rich Presence based on the current Trakt.tv status.
    """
    if watching_data and hasattr(watching_data, 'media_type'):
        details = ""
        state = ""

        # Use current time as a placeholder for the start time
        start_time = int(time.time())

        if watching_data.media_type == 'movies':
            movie = watching_data.movie
            details = f"Watching {movie.title}"
            state = f"({movie.year})"
        elif watching_data.media_type == 'episodes':
            show = watching_data.show
            episode = watching_data.episode
            details = f"Watching {show.title}"
            state = f"S{episode.season:02d}E{episode.number:02d} - {episode.title}"

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
            watching_status = get_watching_status()
            update_discord_presence(rpc, watching_status)
            # Check for new status every 15 seconds
            time.sleep(15)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        rpc.close()

if __name__ == "__main__":
    main()

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

def connect_to_discord():
    """
    Establishes connection to Discord Rich Presence.
    Returns (rpc_client, success_bool)
    """
    try:
        rpc = Presence(DISCORD_CLIENT_ID)
        rpc.connect()
        print("Connected to Discord Rich Presence.")
        return rpc, True
    except Exception as e:
        print(f"Could not connect to Discord: {e}")
        return None, False

def update_discord_presence_with_reconnect(rpc_container, watching_item):
    """
    Updates Discord Rich Presence with automatic reconnection handling.
    rpc_container is a list containing [rpc_client] so we can modify it.
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

        # Use current time as a placeholder for the start time
        start_time = int(time.time())

        # Check if it's a TV episode or movie based on attributes
        if hasattr(watching_item, 'show') and watching_item.show:
            # This is a TV episode
            show_title = watching_item.show.title() if callable(watching_item.show.title) else watching_item.show.title
            details = f"Watching {show_title}"
            
            season = getattr(watching_item, 'season', '?')
            number = getattr(watching_item, 'number', '?')
            episode_title = getattr(watching_item, 'title', 'Unknown Episode')
            
            state = f"S{season:02d}E{number:02d} - {episode_title}"
                
        elif hasattr(watching_item, 'title'):
            # This is likely a movie
            details = f"Watching {watching_item.title}"
            if hasattr(watching_item, 'year') and watching_item.year:
                state = f"({watching_item.year})"

        print(f"Updating Discord: {details} - {state}")
        try:
            rpc_container[0].update(
                details=details,
                state=state,
                large_image="trakt_logo",
                large_text="Watching on Trakt.tv",
                start=start_time
            )
            return True
        except Exception as e:
            print(f"Failed to update Discord presence: {e}")
            # Check if it's a connection error
            if "pipe was closed" in str(e).lower() or "broken pipe" in str(e).lower() or "connection" in str(e).lower():
                print("Discord connection lost, will attempt to reconnect on next update...")
                try:
                    rpc_container[0].close()
                except:
                    pass
                rpc_container[0] = None
            return False
    else:
        print("Not watching anything. Clearing Discord presence.")
        try:
            rpc_container[0].clear()
            return True
        except Exception as e:
            print(f"Failed to clear Discord presence: {e}")
            # Check if it's a connection error
            if "pipe was closed" in str(e).lower() or "broken pipe" in str(e).lower() or "connection" in str(e).lower():
                print("Discord connection lost, will attempt to reconnect on next update...")
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
        
        while True:
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
            time.sleep(15)
            
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
    main()

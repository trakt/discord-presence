#!/usr/bin/env python3
"""
Clean Discord IPC implementation with WATCHING activity type support.
Optimized for "TV with Trakt" Discord application.
"""

import json
import os
import socket
import struct
import time
import uuid
import glob
import tempfile
from typing import Optional, Dict, Any


class DiscordIPC:
    """
    Discord IPC client with WATCHING activity type support.
    """
    
    def __init__(self, client_id: str, pipe: int = 0):
        """
        Initialize Discord IPC client.
        
        Args:
            client_id: Discord application client ID
            pipe: IPC pipe number (0-9)
        """
        self.client_id = str(client_id)
        self.pipe = pipe
        self.socket = None
        self.connected = False
        
        # Activity types
        self.ACTIVITY_TYPES = {
            'PLAYING': 0,
            'STREAMING': 1, 
            'LISTENING': 2,
            'WATCHING': 3,
            'CUSTOM': 4,
            'COMPETING': 5
        }
    
    def connect(self) -> bool:
        """
        Connect to Discord IPC.
        
        Returns:
            bool: True if connected successfully
        """
        if self.connected:
            return True
        
        # Try multiple pipe numbers
        for pipe_id in range(10):
            try:
                if self._connect_pipe(pipe_id):
                    self.pipe = pipe_id
                    if self._handshake():
                        self.connected = True
                        return True
                    else:
                        self._disconnect()
            except Exception:
                continue
        
        raise ConnectionError("Could not find Discord installed and running on this machine.")
    
    def _connect_pipe(self, pipe_id: int) -> bool:
        """
        Connect to a specific Discord IPC pipe.
        
        Args:
            pipe_id: Pipe number to try
            
        Returns:
            bool: True if connected to pipe
        """
        if os.name == 'nt':  # Windows
            pipe_path = f"\\\\.\\pipe\\discord-ipc-{pipe_id}"
            try:
                self.socket = open(pipe_path, 'r+b', buffering=0)
                return True
            except (FileNotFoundError, PermissionError, OSError):
                return False
        else:  # Unix-like (Mac, Linux)
            # Try multiple possible locations for Discord IPC
            possible_paths = [
                f"/tmp/discord-ipc-{pipe_id}",  # Linux standard location
                f"{tempfile.gettempdir()}/discord-ipc-{pipe_id}",  # System temp dir
            ]

            # Add paths for Flatpak and Snap if on Linux
            if os.uname().sysname == 'Linux':
                uid = os.getuid()
                possible_paths.extend([
                    f"/run/user/{uid}/app/com.discordapp.Discord/discord-ipc-{pipe_id}",  # Flatpak
                    f"/run/user/{uid}/snap.discord/discord-ipc-{pipe_id}",  # Snap
                ])

            # On macOS, search in /var/folders/*/T/
            if os.uname().sysname == 'Darwin':  # macOS
                patterns = [
                    f"/var/folders/*/T/discord-ipc-{pipe_id}",
                    f"/var/folders/*/*/T/discord-ipc-{pipe_id}",
                    f"/var/folders/*/*/*/T/discord-ipc-{pipe_id}"
                ]
                for pattern in patterns:
                    discord_sockets = glob.glob(pattern)
                    possible_paths.extend(discord_sockets)
            
            for pipe_path in possible_paths:
                if not os.path.exists(pipe_path):
                    continue
                    
                try:
                    self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    self.socket.connect(pipe_path)
                    return True
                except (FileNotFoundError, ConnectionRefusedError, PermissionError, OSError):
                    if self.socket:
                        self.socket.close()
                        self.socket = None
                    continue
            
            return False
    
    def _disconnect(self):
        """Disconnect from Discord IPC."""
        if self.socket:
            try:
                if hasattr(self.socket, 'close'):
                    self.socket.close()
            except Exception:
                pass
            finally:
                self.socket = None
        self.connected = False
    
    def _send_data(self, op_code: int, data: Dict[str, Any]) -> bool:
        """
        Send data to Discord IPC.
        
        Args:
            op_code: Operation code
            data: Data payload
            
        Returns:
            bool: True if sent successfully
        """
        if not self.socket:
            return False
            
        payload = json.dumps(data).encode('utf-8')
        header = struct.pack('<II', op_code, len(payload))
        
        try:
            if os.name == 'nt':  # Windows named pipe
                self.socket.write(header + payload)
                self.socket.flush()
            else:  # Unix socket
                self.socket.sendall(header + payload)
            return True
        except Exception:
            return False
    
    def _receive_data(self) -> Optional[Dict[str, Any]]:
        """
        Receive data from Discord IPC.
        
        Returns:
            Optional[Dict]: Received data or None if failed
        """
        if not self.socket:
            return None
            
        try:
            if os.name == 'nt':  # Windows named pipe
                header = self.socket.read(8)
            else:  # Unix socket
                header = self.socket.recv(8)
                
            if len(header) < 8:
                return None
                
            op_code, length = struct.unpack('<II', header)
            
            if os.name == 'nt':  # Windows named pipe
                payload = self.socket.read(length)
            else:  # Unix socket
                payload = self.socket.recv(length)
                
            return json.loads(payload.decode('utf-8'))
        except Exception:
            return None
    
    def _handshake(self) -> bool:
        """
        Perform Discord IPC handshake.
        
        Returns:
            bool: True if handshake successful
        """
        handshake_data = {
            'v': 1,
            'client_id': self.client_id
        }
        
        if not self._send_data(0, handshake_data):  # HANDSHAKE op_code = 0
            return False
            
        response = self._receive_data()
        return response is not None and 'data' in response
    
    def update(self, 
               details: Optional[str] = None,
               state: Optional[str] = None, 
               start: Optional[int] = None,
               end: Optional[int] = None,
               large_image: Optional[str] = None,
               large_text: Optional[str] = None,
               small_image: Optional[str] = None,
               small_text: Optional[str] = None,
               party_id: Optional[str] = None,
               party_size: Optional[list] = None,
               join: Optional[str] = None,
               spectate: Optional[str] = None,
               match: Optional[str] = None,
               buttons: Optional[list] = None,
               instance: bool = True,
               activity_type: int = 0,
               pid: Optional[int] = None) -> bool:
        """
        Update Discord Rich Presence activity.
        
        Args:
            details: Show/movie title
            state: Episode info or status
            start: Unix timestamp for when activity started
            end: Unix timestamp for when activity will end
            large_image: Name/URL of large profile artwork
            large_text: Tooltip for large image
            small_image: Name/URL of small profile artwork  
            small_text: Tooltip for small image
            party_id: ID of player's party/lobby/group
            party_size: Current and max party size [current, max]
            join: Unique hashed string for chat invitations
            spectate: Unique hashed string for spectate button
            match: Unique hashed string for spectate and join
            buttons: List of button dicts [{"label": "text", "url": "https://..."}]
            instance: Whether this is a game session with specific beginning/end
            activity_type: Activity type (0=PLAYING, 1=STREAMING, 2=LISTENING, 3=WATCHING)
            pid: Process ID
            
        Returns:
            bool: True if update successful
        """
        if not self.connected:
            return False
        
        # For WATCHING activity type, Discord handles the payload differently
        if activity_type == 3:  # WATCHING
            activity = {
                'type': activity_type,
                'application_id': self.client_id,
                'details': details,  # This becomes the main title after "Watching"
                'state': state,      # This becomes the subtitle
            }
        else:
            # For other activity types, use standard structure
            activity = {
                'type': activity_type,
                'application_id': self.client_id,
                'name': details or state or 'Discord IPC',
            }
            if details is not None:
                activity['details'] = details
            if state is not None:
                activity['state'] = state
            
        if start is not None or end is not None:
            timestamps = {}
            if start is not None:
                timestamps['start'] = start
            if end is not None:
                timestamps['end'] = end
            activity['timestamps'] = timestamps
            
        if large_image is not None or small_image is not None:
            assets = {}
            if large_image is not None:
                assets['large_image'] = large_image
            if large_text is not None:
                assets['large_text'] = large_text
            if small_image is not None:
                assets['small_image'] = small_image
            if small_text is not None:
                assets['small_text'] = small_text
            activity['assets'] = assets
            
        if party_id is not None or party_size is not None:
            party = {}
            if party_id is not None:
                party['id'] = party_id
            if party_size is not None and len(party_size) >= 2:
                party['size'] = [party_size[0], party_size[1]]
            activity['party'] = party
            
        if join is not None or spectate is not None or match is not None:
            secrets = {}
            if join is not None:
                secrets['join'] = join
            if spectate is not None:
                secrets['spectate'] = spectate
            if match is not None:
                secrets['match'] = match
            activity['secrets'] = secrets
            
        if buttons is not None:
            activity['buttons'] = buttons[:2]  # Max 2 buttons
            
        if instance is not None:
            activity['instance'] = instance
            
        data = {
            'cmd': 'SET_ACTIVITY',
            'args': {
                'pid': pid or os.getpid(),
                'activity': activity
            },
            'nonce': str(uuid.uuid4())
        }
        
        return self._send_data(1, data)  # FRAME op_code = 1
    
    def clear(self, pid: Optional[int] = None) -> bool:
        """
        Clear Discord Rich Presence activity.
        
        Args:
            pid: Process ID
            
        Returns:
            bool: True if clear successful
        """
        if not self.connected:
            return False
            
        data = {
            'cmd': 'SET_ACTIVITY', 
            'args': {
                'pid': pid or os.getpid(),
                'activity': None
            },
            'nonce': str(uuid.uuid4())
        }
        
        return self._send_data(1, data)  # FRAME op_code = 1
    
    def close(self):
        """Close Discord IPC connection."""
        self._disconnect()


# For backwards compatibility with pypresence
Presence = DiscordIPC

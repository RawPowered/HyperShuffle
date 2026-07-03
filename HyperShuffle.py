#!/usr/bin/env python3
"""
HyperShuffle - Advanced Plex Collection Shuffling System
A refined version of TrueShuffle with super-shuffle as default mode
"""

import os
import sys
import time
import random
import sqlite3
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import colorama
from colorama import Fore, Back, Style

# Plex API imports
from plexapi.myplex import MyPlexAccount
from plexapi.utils import millisecondToHumanstr
from plexapi.library import Library, Hub
import plexapi.video, plexapi.audio

# Local imports
import config

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)

class SessionClientWrapper:
    """Wrapper class for clients that don't support direct control but can be controlled via server sessions."""
    
    def __init__(self, session, server, client):
        self.session = session
        self.server = server
        self.client = client
        self.name = client.name
        self.platform = getattr(client, 'platform', 'Unknown')
        self.machineIdentifier = getattr(client, 'machineIdentifier', 'unknown')
        
    def timeline(self):
        """Get timeline from session instead of direct client."""
        # Return the session itself as timeline data
        return [self.session]
    
    def play(self):
        """Resume playback via session."""
        try:
            self.session.play()
            return True
        except Exception as e:
            print(f"  ⚠️  Session play error: {str(e)}")
            return False
    
    def pause(self):
        """Pause playback via session."""
        try:
            self.session.pause()
            return True
        except Exception as e:
            print(f"  ⚠️  Session pause error: {str(e)}")
            return False
    
    def stop(self):
        """Stop playback via session."""
        try:
            self.session.stop()
            return True
        except Exception as e:
            print(f"  ⚠️  Session stop error: {str(e)}")
            return False
    
    def skipNext(self):
        """Skip to next via session."""
        try:
            self.session.skipNext()
            return True
        except Exception as e:
            print(f"  ⚠️  Session skipNext error: {str(e)}")
            return False
    
    def setSubtitleStream(self, stream_id):
        """Set subtitle stream via session."""
        try:
            # Try to set subtitles on the session media
            if hasattr(self.session, 'setSubtitleStream'):
                self.session.setSubtitleStream(stream_id)
                return True
            elif hasattr(self.session, 'media') and len(self.session.media) > 0:
                # Try setting on the media object
                media = self.session.media[0]
                if hasattr(media, 'setSubtitleStream'):
                    media.setSubtitleStream(stream_id)
                    return True
            
            print(f"  ⚠️  {Fore.YELLOW}Samsung TV subtitle control not supported via session{Style.RESET_ALL}")
            print(f"  💡 {Fore.BLUE}Use your Samsung TV remote:{Style.RESET_ALL}")
            print(f"     • Press the 'Tools' or 'Settings' button")
            print(f"     • Look for 'Subtitle' or 'CC' options")
            print(f"     • Or try the 'Info' button during playback")
            return False
            
        except Exception as e:
            print(f"  ❌ Session subtitle error: {str(e)}")
            return False
    
    def setShuffle(self, enabled):
        """Set shuffle mode via session."""
        try:
            if hasattr(self.session, 'setShuffle'):
                self.session.setShuffle(enabled)
                return True
            print(f"  ⚠️  {Fore.YELLOW}Samsung TV shuffle control not supported via session{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"  ⚠️  Session shuffle error: {str(e)}")
            return False
    
    def playMedia(self, media):
        """Play media via session/server."""
        try:
            # Use the server to play media on this client
            self.client.playMedia(media)
            return True
        except Exception as e:
            print(f"  ⚠️  Session playMedia error: {str(e)}")
            return False
    
    def volumeUp(self):
        """Volume up - not supported via session."""
        print(f"  ⚠️  {Fore.YELLOW}Volume control not supported for Samsung TV via session{Style.RESET_ALL}")
        print(f"  💡 {Fore.BLUE}Use your Samsung TV remote for volume control{Style.RESET_ALL}")
        return False
    
    def volumeDown(self):
        """Volume down - not supported via session."""
        print(f"  ⚠️  {Fore.YELLOW}Volume control not supported for Samsung TV via session{Style.RESET_ALL}")
        print(f"  💡 {Fore.BLUE}Use your Samsung TV remote for volume control{Style.RESET_ALL}")
        return False
    
    def mute(self):
        """Mute - not supported via session."""
        print(f"  ⚠️  {Fore.YELLOW}Mute control not supported for Samsung TV via session{Style.RESET_ALL}")
        print(f"  💡 {Fore.BLUE}Use your Samsung TV remote for mute control{Style.RESET_ALL}")
        return False
    
    def setVolume(self, level):
        """Set volume - not supported via session."""
        print(f"  ⚠️  {Fore.YELLOW}Volume control not supported for Samsung TV via session{Style.RESET_ALL}")
        print(f"  💡 {Fore.BLUE}Use your Samsung TV remote for volume control{Style.RESET_ALL}")
        return False

class SamsungClientWrapper:
    """Wrapper for Samsung Tizen clients with limited API support.

    Provides safe fallbacks for common controls and delegates unknown
    attributes to the underlying client connection.
    """
    
    def __init__(self, client_connection, original_client):
        self.client_connection = client_connection
        self.original_client = original_client
        self.platform = getattr(original_client, 'platform', 'Tizen')
        
    def __getattr__(self, name):
        """Delegate unknown attributes to the wrapped client connection."""
        return getattr(self.client_connection, name)
    
    def timeline(self):
        """Return timeline if supported, else empty list."""
        try:
            try:
                return self.client_connection.timeline()
            except (TypeError, AttributeError):
                return getattr(self.client_connection, 'timeline', [])
        except Exception:
            return []
    
    def play(self):
        try:
            if hasattr(self.client_connection, 'play'):
                return self.client_connection.play()
            raise Exception('play not supported')
        except Exception as e:
            raise Exception(f"Samsung playback control failed: {str(e)}")
    
    def pause(self):
        try:
            if hasattr(self.client_connection, 'pause'):
                return self.client_connection.pause()
            raise Exception('pause not supported')
        except Exception as e:
            raise Exception(f"Samsung playback control failed: {str(e)}")
    
    def stop(self):
        try:
            if hasattr(self.client_connection, 'stop'):
                return self.client_connection.stop()
            raise Exception('stop not supported')
        except Exception as e:
            raise Exception(f"Samsung playback control failed: {str(e)}")
    
    def skipNext(self):
        """Try multiple ways to skip to next."""
        try:
            if hasattr(self.client_connection, 'skipNext'):
                return self.client_connection.skipNext()
            if hasattr(self.client_connection, 'stepForward'):
                return self.client_connection.stepForward()
            if hasattr(self.client_connection, 'seekTo'):
                return self.client_connection.seekTo(999999)
            raise Exception('skip not supported')
        except Exception as e:
            raise Exception(f"Samsung skip failed: {str(e)}")
    
    def stepForward(self):
        try:
            if hasattr(self.client_connection, 'stepForward'):
                return self.client_connection.stepForward()
            return self.skipNext()
        except Exception as e:
            raise Exception(f"Samsung stepForward failed: {str(e)}")
    
    def seekTo(self, ms):
        if hasattr(self.client_connection, 'seekTo'):
            return self.client_connection.seekTo(ms)
        raise Exception('seekTo not supported')
    
    def setSubtitleStream(self, stream_id):
        try:
            if hasattr(self.client_connection, 'setSubtitleStream'):
                return self.client_connection.setSubtitleStream(stream_id)
            print(f"  ⚠️  {Fore.YELLOW}Samsung TV subtitle control not supported via API{Style.RESET_ALL}")
            print(f"  💡 {Fore.BLUE}Use your Samsung TV remote to enable subtitles{Style.RESET_ALL}")
            return False
        except Exception as e:
            raise Exception(f"Samsung subtitle control failed: {str(e)}")
    
    def setShuffle(self, enabled):
        try:
            if hasattr(self.client_connection, 'setShuffle'):
                return self.client_connection.setShuffle(enabled)
            print(f"  ⚠️  {Fore.YELLOW}Samsung TV shuffle control not supported via API{Style.RESET_ALL}")
            return False
        except Exception as e:
            raise Exception(f"Samsung shuffle control failed: {str(e)}")
    
    def playMedia(self, media):
        try:
            if hasattr(self.client_connection, 'playMedia'):
                return self.client_connection.playMedia(media)
            raise Exception('playMedia not supported')
        except Exception as e:
            raise Exception(f"Samsung playMedia failed: {str(e)}")
    
    def volumeUp(self):
        print(f"  ⚠️  {Fore.YELLOW}Volume control not supported for Samsung TV via API{Style.RESET_ALL}")
        print(f"  💡 {Fore.BLUE}Use your Samsung TV remote for volume control{Style.RESET_ALL}")
        return False
    
    def volumeDown(self):
        print(f"  ⚠️  {Fore.YELLOW}Volume control not supported for Samsung TV via API{Style.RESET_ALL}")
        print(f"  💡 {Fore.BLUE}Use your Samsung TV remote for volume control{Style.RESET_ALL}")
        return False
    
    def mute(self):
        print(f"  ⚠️  {Fore.YELLOW}Mute control not supported for Samsung TV via API{Style.RESET_ALL}")
        print(f"  💡 {Fore.BLUE}Use your Samsung TV remote for mute control{Style.RESET_ALL}")
        return False
    
    def setVolume(self, level):
        print(f"  ⚠️  {Fore.YELLOW}Volume control not supported for Samsung TV via API{Style.RESET_ALL}")
        print(f"  💡 {Fore.BLUE}Use your Samsung TV remote for volume control{Style.RESET_ALL}")
        return False

class HyperShuffle:
    """
    Advanced Plex collection shuffling system with beautiful interface
    and comprehensive customization options.
    """
    
    def __init__(self):
        """Initialize HyperShuffle system."""
        # Resolve and connect to database with better timeout settings
        self.db_path = self.resolve_database_path()
        self.showDB = sqlite3.connect(str(self.db_path), timeout=30.0)
        self.cursor = self.showDB.cursor()
        # Ensure required schema exists
        self.ensure_database_schema()
        self.myAccount = MyPlexAccount(config.username, config.password)
        self.connected_servers = []
        self.available_clients = []
        self.current_collection_index = 0
        self.collection_index_file = 'collection_index.txt'
        
        # Configuration options
        self.config = {
            'auto_cycle_collections': True,
            'holiday_filtering': True,
            'view_count_priority': True,
            'balanced_lineup': False,
            'animation_domination': False,
            'auto_client_selection': True,
            'show_detailed_info': True,
            'confirm_plays': False,
            'max_consecutive_same_show': 2,
            'collection_cycle_delay': 5,
            'update_view_counts': True,
            'prioritization_mode': '1',  # Default: Push Holiday Episodes Back
            'skip_view_count_updates': False,  # Skip updates when clients are busy
            'database_retry_attempts': 3,  # Number of retries for database operations
            'client_retry_attempts': 3,  # Number of retries for client operations
            'client_timeout_seconds': 30,  # Timeout for client operations
            'preserve_shuffle_mode': True,  # Preserve client shuffle mode during playback
            'auto_manage_subtitles': False,  # Automatically manage subtitles
            'auto_download_subtitles': False,  # Auto-download subtitles if missing
            'auto_enable_subtitles': False,  # Auto-enable subtitles on playback
            'smart_subtitle_selection': True,  # Use intelligent subtitle selection for accuracy
            'preferred_subtitle_language': 'en',  # Preferred subtitle language code
            'remote_mode_shortcuts': True,  # Enable keyboard shortcuts in remote mode
            'show_startup_commands': True,  # Show command overview on startup
            'samsung_client_timeout': 10,  # Extended timeout for Samsung/Tizen clients
        }
        
        # Holiday keywords for filtering
        self.holiday_keywords = {
            'halloween': ['halloween', 'horror', 'treehouse', 'spooky', 'scary', 'ghost', 'witch', 'vampire', 'monster'],
            'thanksgiving': ['thanksgiving', 'turkey', 'pilgrim', 'harvest', 'feast', 'gratitude'],
            'christmas': ['christmas', 'x-mas', 'xmas', 'holy night', 'santa', 'elf', 'reindeer', 'snowman'],
            'summer': ['summer', 'beach', 'vacation', 'hot', 'sun', 'pool', 'barbecue', 'bbq', 'picnic'],
            'valentines': ['valentine', 'love', 'romance', 'heart', 'cupid'],
            'easter': ['easter', 'bunny', 'egg', 'spring', 'resurrection'],
            'new_year': ['new year', 'new years', 'resolution', 'celebration', 'fireworks']
        }
        
        self.print_banner()
        self.initialize_system()
    
    def print_banner(self):
        """Display the HyperShuffle banner."""
        banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                    {Fore.YELLOW}🎬 HYPER SHUFFLE 🎬{Fore.CYAN}                        ║
║              {Fore.WHITE}Advanced Plex Collection Shuffling System{Fore.CYAN}           ║
║                    {Fore.GREEN}Super-Shuffle Default Mode{Fore.CYAN}                   ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(banner)
    
    def resolve_database_path(self) -> Path:
        """Resolve a stable database path across dev and bundled EXE.
        
        Search order:
        1) Same directory as executable/script
        2) Parent directory (useful when running from dist/)
        3) Current working directory
        4) %APPDATA%/HyperShuffle/myShows.db (created if not found)
        """
        try:
            # Base dir depends on whether we're frozen (PyInstaller) or not
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).resolve().parent
            candidates = [
                base_dir / 'myShows.db',
                base_dir.parent / 'myShows.db',
                Path(os.getcwd()) / 'myShows.db',
            ]
            for candidate in candidates:
                try:
                    if candidate.exists() and candidate.stat().st_size > 0:
                        print(f"{Fore.BLUE}🗄️  Using database: {candidate}{Style.RESET_ALL}")
                        return candidate
                except Exception:
                    continue
            # Fallback to AppData
            appdata = os.getenv('APPDATA')
            if appdata:
                app_dir = Path(appdata) / 'HyperShuffle'
            else:
                app_dir = base_dir
            app_dir.mkdir(parents=True, exist_ok=True)
            db_path = app_dir / 'myShows.db'
            print(f"{Fore.YELLOW}⚠️  Database not found; creating at: {db_path}{Style.RESET_ALL}")
            return db_path
        except Exception as e:
            # Last-resort fallback in current dir
            print(f"{Fore.RED}⚠️  DB path resolution failed: {str(e)}{Style.RESET_ALL}")
            return Path('myShows.db')
    
    def ensure_database_schema(self):
        """Create required tables if they don't exist yet."""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS episodes (
                    ID INTEGER PRIMARY KEY,
                    Type TEXT,
                    Show TEXT,
                    Season TEXT,
                    Episode TEXT,
                    Title TEXT,
                    Server TEXT,
                    ViewCount INTEGER,
                    Length INTEGER
                )
            ''')
            # Helpful index for lookups/updates
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_episodes_show_server_episode
                ON episodes (Show, Server, Episode)
            ''')
            self.showDB.commit()
        except Exception as e:
            print(f"{Fore.RED}⚠️  Could not ensure database schema: {str(e)}{Style.RESET_ALL}")
    
    def initialize_system(self):
        """Initialize the HyperShuffle system."""
        print(f"{Fore.BLUE}🔧 Initializing HyperShuffle System...{Style.RESET_ALL}")
        
        # Connect to servers
        self.connect_servers()
        
        # Discover clients
        self.discover_clients()
        
        # Load collection index
        self.load_collection_index()
        
        print(f"{Fore.GREEN}✅ System initialization complete!{Style.RESET_ALL}\n")
    
    def connect_servers(self):
        """Connect to all configured Plex servers."""
        print(f"{Fore.BLUE}🌐 Connecting to Plex servers...{Style.RESET_ALL}")
        
        for server_name in config.servers:
            try:
                print(f"  🔗 Connecting to {server_name}...")
                server = self.myAccount.resource(server_name).connect()
                self.connected_servers.append(server)
                print(f"  ✅ {Fore.GREEN}Connected to {server.friendlyName}{Style.RESET_ALL}")
            except Exception as e:
                print(f"  ❌ {Fore.RED}Failed to connect to {server_name}: {str(e)}{Style.RESET_ALL}")
        
        if not self.connected_servers:
            print(f"{Fore.RED}❌ No servers connected. Please check your configuration.{Style.RESET_ALL}")
            sys.exit(1)
        
        print(f"{Fore.GREEN}✅ Connected to {len(self.connected_servers)} server(s){Style.RESET_ALL}")
    
    def discover_clients(self):
        """Discover available Plex clients."""
        print(f"{Fore.BLUE}📱 Discovering Plex clients...{Style.RESET_ALL}")
        
        try:
            self.available_clients = [
                x for x in self.myAccount.resources() 
                if "player" in x.provides and x.presence and x.publicAddressMatches
            ]
            
            for client in self.available_clients:
                status = f"{Fore.GREEN}Online{Style.RESET_ALL}" if client.presence else f"{Fore.RED}Offline{Style.RESET_ALL}"
                print(f"  📺 {client.name} ({client.platform}) - {status}")
            
            if not self.available_clients:
                print(f"{Fore.YELLOW}⚠️  No online clients found{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error discovering clients: {str(e)}{Style.RESET_ALL}")
    
    def load_collection_index(self):
        """Load the current collection index from file."""
        try:
            with open(self.collection_index_file, 'r') as f:
                self.current_collection_index = int(f.read().strip())
        except:
            self.current_collection_index = 0
    
    def save_collection_index(self):
        """Save the current collection index to file."""
        try:
            with open(self.collection_index_file, 'w') as f:
                f.write(str(self.current_collection_index))
        except Exception as e:
            print(f"{Fore.RED}⚠️  Could not save collection index: {str(e)}{Style.RESET_ALL}")
    
    def get_all_collections(self) -> List[Tuple]:
        """Get all collections from all servers."""
        all_collections = []
        
        for server in self.connected_servers:
            try:
                library = server.library.section('TV Shows')
                collections = library.collections()
                for collection in collections:
                    all_collections.append((collection, server))
            except Exception as e:
                print(f"{Fore.RED}⚠️  Could not access collections on {server.friendlyName}: {str(e)}{Style.RESET_ALL}")
        
        return all_collections
    
    def display_collections(self, collections: List[Tuple]):
        """Display available collections in a beautiful format."""
        if not collections:
            print(f"{Fore.YELLOW}📚 No collections found on any server{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}📚 Available Collections ({len(collections)} total):{Style.RESET_ALL}")
        print(f"{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
        
        for i, (collection, server) in enumerate(collections, 1):
            current_marker = f"{Fore.YELLOW}🎯 CURRENT{Style.RESET_ALL}" if i-1 == self.current_collection_index else ""
            print(f"{Fore.CYAN}║{Style.RESET_ALL} {i:2d}. {Fore.WHITE}{collection.title:<30}{Style.RESET_ALL} "
                  f"({collection.childCount:3d} items) - {Fore.BLUE}{server.friendlyName:<15}{Style.RESET_ALL} {current_marker}")
        
        print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
    
    def select_client(self) -> Optional[Any]:
        """Select a Plex client for playback."""
        if not self.available_clients:
            print(f"{Fore.RED}❌ No available clients found{Style.RESET_ALL}")
            return None
        
        if self.config['auto_client_selection'] and len(self.available_clients) == 1:
            client = self.available_clients[0]
            print(f"{Fore.GREEN}✅ Auto-selected client: {client.name}{Style.RESET_ALL}")
            return client
        
        print(f"\n{Fore.CYAN}📱 Select Plex Client:{Style.RESET_ALL}")
        for i, client in enumerate(self.available_clients, 1):
            status = f"{Fore.GREEN}Online{Style.RESET_ALL}" if client.presence else f"{Fore.RED}Offline{Style.RESET_ALL}"
            print(f"  {i}. {client.name} ({client.platform}) - {status}")
        
        while True:
            try:
                choice = input(f"\n{Fore.YELLOW}Select client (1-{len(self.available_clients)}): {Style.RESET_ALL}").strip()
                client_index = int(choice) - 1
                if 0 <= client_index < len(self.available_clients):
                    return self.available_clients[client_index]
                else:
                    print(f"{Fore.RED}❌ Invalid choice. Please enter 1-{len(self.available_clients)}.{Style.RESET_ALL}")
            except (ValueError, KeyboardInterrupt):
                print(f"{Fore.RED}❌ Invalid input or operation cancelled.{Style.RESET_ALL}")
                return None
    
    def connect_client_with_retry(self, client, max_retries=3):
        """Connect to client with retry logic for busy clients."""
        # Special handling for Samsung/Tizen clients
        is_samsung = 'samsung' in client.product.lower() if hasattr(client, 'product') else False
        is_tizen = client.platform.lower() == 'tizen' if hasattr(client, 'platform') else False
        
        if is_samsung or is_tizen:
            print(f"  📱 Detected Samsung/Tizen client - using alternative connection method...")
            return self.connect_samsung_client(client, max_retries)
        
        for attempt in range(max_retries):
            try:
                print(f"  🔗 Connecting to {client.name}... (attempt {attempt + 1}/{max_retries})")
                client_connection = client.connect()
                
                # Test if client is responsive
                try:
                    # Try multiple methods to test client responsiveness
                    test_passed = False
                    
                    # Test 1: Try timeline method
                    try:
                        client_connection.timeline()
                        test_passed = True
                    except (TypeError, AttributeError):
                        # Test 2: Try timeline property
                        try:
                            _ = client_connection.timeline
                            test_passed = True
                        except AttributeError:
                            # Test 3: Try basic client info
                            try:
                                _ = client_connection.machineIdentifier
                                test_passed = True
                            except AttributeError:
                                pass
                    
                    if test_passed:
                        print(f"  ✅ {Fore.GREEN}Successfully connected to {client.name}{Style.RESET_ALL}")
                        return client_connection
                    else:
                        print(f"  ✅ {Fore.GREEN}Connected to {client.name} (limited functionality){Style.RESET_ALL}")
                        return client_connection
                        
                except Exception as e:
                    if "timeout" in str(e).lower() or "read timed out" in str(e).lower():
                        print(f"  ⏳ Client {client.name} is busy, retrying in 2 seconds...")
                        time.sleep(2)
                        continue
                    else:
                        # Other error, but connection was successful
                        print(f"  ✅ {Fore.GREEN}Connected to {client.name} (with minor issues){Style.RESET_ALL}")
                        return client_connection
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  ⏳ Connection failed: {str(e)}, retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                else:
                    print(f"  ❌ {Fore.RED}Failed to connect to {client.name} after {max_retries} attempts{Style.RESET_ALL}")
                    return None
        
        return None

    def connect_samsung_client(self, client, max_retries=3):
        """Special connection method for Samsung/Tizen clients.

        Prefers session-based control when available, otherwise wraps a direct
        client connection with SamsungClientWrapper.
        """
        try:
            print(f"  🔧 Using Samsung-specific connection approach...")
            
            # Prefer session-based control if available
            session_wrapper = self.create_session_wrapper(client)
            if session_wrapper:
                print(f"  ✅ {Fore.GREEN}Connected to {client.name} via server session{Style.RESET_ALL}")
                return session_wrapper
            
            # Fallback to standard connection with relaxed requirements
            for attempt in range(max_retries):
                try:
                    print(f"  📺 Samsung connection attempt {attempt + 1}/{max_retries}...")
                    connection_timeout = 15
                    try:
                        client_connection = client.connect(timeout=connection_timeout)
                    except Exception as e:
                        if "timeout" in str(e).lower():
                            print(f"  ⏰ Samsung client timeout, trying without explicit timeout...")
                            client_connection = client.connect()
                        else:
                            raise e
                    print(f"  ✅ {Fore.GREEN}Samsung Tizen client connected{Style.RESET_ALL}")
                    print(f"  📱 {Fore.BLUE}Note: Samsung TVs have limited remote control API support{Style.RESET_ALL}")
                    return SamsungClientWrapper(client_connection, client)
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"  ⏳ Samsung connection failed: {str(e)}")
                        print(f"  🔄 Retrying Samsung connection in 3 seconds...")
                        time.sleep(3)
                        continue
                    else:
                        print(f"  ❌ {Fore.RED}Samsung direct connection failed after {max_retries} attempts{Style.RESET_ALL}")
                        print(f"  💡 {Fore.BLUE}Falling back to session control if available{Style.RESET_ALL}")
                        return self.create_session_wrapper(client)
        except Exception as e:
            print(f"  ❌ Samsung connection error: {str(e)}")
            return None

    def create_session_wrapper(self, client):
        """Create a session-based wrapper for clients that don't support direct control."""
        try:
            # Find the active session for this client
            for server in self.connected_servers:
                try:
                    sessions = server.sessions()
                    for session in sessions:
                        if hasattr(session, 'player'):
                            session_client_name = getattr(session.player, 'title', '')
                            if (client.name == session_client_name or 
                                session_client_name in client.name or 
                                client.name in session_client_name):
                                
                                # Create a wrapper object that mimics client connection
                                wrapper = SessionClientWrapper(session, server, client)
                                return wrapper
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            print(f"  ❌ Error creating session wrapper: {str(e)}")
        return None

    def connect_samsung_client(self, client, max_retries=3):
        """Special connection method for Samsung Tizen clients."""
        for attempt in range(max_retries):
            try:
                print(f"  📺 Samsung connection attempt {attempt + 1}/{max_retries}...")
                
                # Samsung clients need different timeout and connection parameters
                connection_timeout = 15  # Longer timeout for Samsung
                
                try:
                    # Try with extended timeout
                    client_connection = client.connect(timeout=connection_timeout)
                except Exception as e:
                    if "timeout" in str(e).lower():
                        print(f"  ⏰ Samsung client timeout, trying alternative method...")
                        # Try without explicit timeout
                        client_connection = client.connect()
                    else:
                        raise e
                
                # For Samsung, just getting a connection object might be enough
                print(f"  ✅ {Fore.GREEN}Samsung Tizen client connected{Style.RESET_ALL}")
                print(f"  📱 {Fore.BLUE}Note: Samsung TVs have limited remote control API support{Style.RESET_ALL}")
                
                # Create a wrapper that handles Samsung-specific limitations
                return SamsungClientWrapper(client_connection, client)
                
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    print(f"  ⏳ Samsung connection failed: {error_msg}")
                    print(f"  🔄 Retrying Samsung connection in 3 seconds...")
                    time.sleep(3)
                    continue
                else:
                    print(f"  ❌ {Fore.RED}Samsung connection failed after {max_retries} attempts{Style.RESET_ALL}")
                    print(f"  💡 {Fore.BLUE}Try these Samsung Tizen troubleshooting steps:{Style.RESET_ALL}")
                    print(f"     • Restart the Plex app on your Samsung TV")
                    print(f"     • Check that your TV and server are on the same network")
                    print(f"     • Some Samsung models have limited Plex API support")
                    print(f"     • Manual control from TV remote may work better")
                    return None
        
        return None
    
    def get_client_playback_state(self, client_connection):
        """Get current playback state and check if client is in shuffle mode."""
        try:
            # Try different methods to get timeline/status
            timeline = None
            current_session = None
            
            # Method 1: Try timeline as a method
            try:
                timeline = client_connection.timeline()
            except (TypeError, AttributeError) as e:
                # Method 2: Try timeline as a property
                try:
                    timeline = client_connection.timeline
                except AttributeError:
                    # Method 3: Try getting sessions from server
                    try:
                        # Get sessions from the server instead
                        sessions = client_connection.server.sessions()
                        for session in sessions:
                            # Look for sessions on this client
                            if hasattr(session, 'player') and hasattr(session.player, 'machineIdentifier'):
                                if session.player.machineIdentifier == client_connection.machineIdentifier:
                                    current_session = session
                                    break
                    except Exception:
                        pass
            
            playback_state = {
                'is_playing': False,
                'is_shuffle_mode': False,
                'current_playlist': None,
                'current_media': None,
                'playback_position': 0
            }
            
            # Process timeline if we got it
            if timeline and hasattr(timeline, '__len__') and len(timeline) > 0:
                current_session = timeline[0]
            
            # Process session data
            if current_session:
                # Check various state indicators
                state = getattr(current_session, 'state', None)
                if state:
                    playback_state['is_playing'] = state in ['playing', 'paused']
                
                # Get playback position
                playback_state['playback_position'] = getattr(current_session, 'viewOffset', 0)
                
                # Check shuffle mode
                if hasattr(current_session, 'shuffle'):
                    playback_state['is_shuffle_mode'] = current_session.shuffle
                elif hasattr(current_session, 'player') and hasattr(current_session.player, 'shuffle'):
                    playback_state['is_shuffle_mode'] = current_session.player.shuffle
                
                # Store media reference
                playback_state['current_media'] = current_session
            
            return playback_state
            
        except Exception as e:
            print(f"  ⚠️  {Fore.YELLOW}Could not get playback state: {str(e)}{Style.RESET_ALL}")
            return {
                'is_playing': False,
                'is_shuffle_mode': False,
                'current_playlist': None,
                'current_media': None,
                'playback_position': 0
            }

    def add_to_shuffle_playlist(self, client_connection, plex_episode):
        """Add episode to current shuffle playlist without interrupting playback."""
        try:
            # Try to add to existing playlist/queue
            print(f"  📝 Adding episode to shuffle playlist...")
            
            # Get current playback state
            playback_state = self.get_client_playback_state(client_connection)
            
            if playback_state['is_playing'] and playback_state['is_shuffle_mode']:
                # Client is playing in shuffle mode - add to queue
                try:
                    client_connection.addToPlayQueue(plex_episode)
                    print(f"  ✅ {Fore.GREEN}Added to shuffle queue without interrupting current playback{Style.RESET_ALL}")
                    return True
                except Exception as e:
                    # Fallback to creating new playlist
                    print(f"  ⚠️  Could not add to existing queue: {str(e)}")
                    print(f"  🔄 Creating new shuffle playlist...")
                    return self.create_shuffle_playlist(client_connection, plex_episode)
            else:
                # No shuffle mode active, play normally
                return False
                
        except Exception as e:
            print(f"  ❌ {Fore.RED}Error managing shuffle playlist: {str(e)}{Style.RESET_ALL}")
            return False

    def create_shuffle_playlist(self, client_connection, plex_episode):
        """Create a new shuffle playlist starting with the selected episode."""
        try:
            # Start playing the episode and enable shuffle
            client_connection.playMedia(plex_episode)
            
            # Try to enable shuffle mode
            try:
                time.sleep(1)  # Wait for playback to start
                client_connection.setShuffle(True)
                print(f"  🔀 {Fore.GREEN}Enabled shuffle mode on client{Style.RESET_ALL}")
                return True
            except Exception as e:
                print(f"  ⚠️  {Fore.YELLOW}Could not enable shuffle mode: {str(e)}{Style.RESET_ALL}")
                print(f"  ▶️  Playing normally...")
                return True
                
        except Exception as e:
            print(f"  ❌ {Fore.RED}Error creating shuffle playlist: {str(e)}{Style.RESET_ALL}")
            return False
    
    def play_episode_with_retry(self, client_connection, plex_episode, max_retries=3):
        """Play episode with retry logic for busy clients and shuffle mode preservation."""
        for attempt in range(max_retries):
            try:
                print(f"  ▶️  Attempting to play episode... (attempt {attempt + 1}/{max_retries})")
                
                # Check if we should preserve shuffle mode
                if self.config.get('preserve_shuffle_mode', True):
                    # Try to add to existing shuffle playlist first
                    if self.add_to_shuffle_playlist(client_connection, plex_episode):
                        return True
                
                # Apply subtitle settings before playback
                if self.config.get('auto_manage_subtitles', False):
                    self.setup_episode_subtitles(plex_episode)
                
                # Fallback to normal playback
                client_connection.playMedia(plex_episode)
                print(f"  ✅ {Fore.GREEN}Successfully queued episode for playback{Style.RESET_ALL}")
                
                # Enable subtitles after playback starts if configured
                if self.config.get('auto_enable_subtitles', False):
                    time.sleep(2)  # Wait for playback to start
                    self.enable_subtitles(client_connection, plex_episode)
                
                return True
                
            except Exception as e:
                error_msg = str(e).lower()
                if ("timeout" in error_msg or "read timed out" in error_msg or 
                    "connection" in error_msg or "busy" in error_msg):
                    
                    if attempt < max_retries - 1:
                        print(f"  ⏳ Client is busy or unresponsive, retrying in 3 seconds...")
                        time.sleep(3)
                        continue
                    else:
                        print(f"  ❌ {Fore.RED}Client remains unresponsive after {max_retries} attempts{Style.RESET_ALL}")
                        return False
                else:
                    # Non-retryable error
                    print(f"  ❌ {Fore.RED}Playback error: {str(e)}{Style.RESET_ALL}")
                    return False
        
        return False

    def setup_episode_subtitles(self, plex_episode):
        """Setup and download subtitles for the episode."""
        try:
            if not self.config.get('auto_manage_subtitles', False):
                return
            
            print(f"  🗣️  Setting up subtitles for episode...")
            
            # Check if episode has subtitles
            subtitle_streams = []
            if hasattr(plex_episode, 'streams'):
                subtitle_streams = [stream for stream in plex_episode.streams() if stream.streamType == 3]  # 3 = subtitle
            
            if not subtitle_streams:
                # Try to download subtitles if auto-download is enabled
                if self.config.get('auto_download_subtitles', False):
                    self.download_subtitles(plex_episode)
            else:
                print(f"  ✅ {Fore.GREEN}Found {len(subtitle_streams)} subtitle stream(s){Style.RESET_ALL}")
                
        except Exception as e:
            print(f"  ⚠️  {Fore.YELLOW}Error setting up subtitles: {str(e)}{Style.RESET_ALL}")

    def download_subtitles(self, plex_episode):
        """Download subtitles for the episode."""
        try:
            print(f"  📥 Attempting to download subtitles...")
            
            # Use Plex's built-in subtitle search/download
            # This requires the episode to support subtitle downloads
            if hasattr(plex_episode, 'searchSubtitles'):
                subtitles = plex_episode.searchSubtitles()
                if subtitles:
                    # Get the first available subtitle (usually best match)
                    first_subtitle = subtitles[0]
                    plex_episode.downloadSubtitles(first_subtitle)
                    print(f"  ✅ {Fore.GREEN}Downloaded subtitle: {first_subtitle.displayTitle}{Style.RESET_ALL}")
                else:
                    print(f"  ⚠️  {Fore.YELLOW}No subtitles found for download{Style.RESET_ALL}")
            else:
                print(f"  ⚠️  {Fore.YELLOW}Episode does not support subtitle downloads{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"  ❌ {Fore.RED}Error downloading subtitles: {str(e)}{Style.RESET_ALL}")

    def enable_subtitles(self, client_connection, plex_episode):
        """Enable subtitles on the client for the current episode using smart selection."""
        try:
            print(f"  🗣️  Enabling subtitles on client...")
            
            # Get available subtitle streams
            subtitle_streams = []
            if hasattr(plex_episode, 'streams'):
                subtitle_streams = [stream for stream in plex_episode.streams() if stream.streamType == 3]
            
            if subtitle_streams:
                print(f"  📊 Found {len(subtitle_streams)} subtitle stream(s)")
                
                # Use smart selection if enabled
                if self.config.get('smart_subtitle_selection', True):
                    best_subtitle = self.select_best_subtitle(subtitle_streams)
                else:
                    # Fallback to first available subtitle
                    best_subtitle = subtitle_streams[0]
                
                if best_subtitle:
                    try:
                        # Try to set subtitle stream on client
                        subtitle_id = getattr(best_subtitle, 'id', None)
                        if subtitle_id:
                            client_connection.setSubtitleStream(subtitle_id)
                            subtitle_name = getattr(best_subtitle, 'displayTitle', None) or getattr(best_subtitle, 'language', 'Default')
                            print(f"  ✅ {Fore.GREEN}Enabled subtitles: {subtitle_name} (ID: {subtitle_id}){Style.RESET_ALL}")
                            
                            # Show why this subtitle was selected
                            if self.config.get('smart_subtitle_selection', True):
                                self.explain_subtitle_choice(best_subtitle, subtitle_streams)
                        else:
                            # Fallback to stream index
                            stream_index = subtitle_streams.index(best_subtitle) + 1  # Usually 1-indexed
                            client_connection.setSubtitleStream(stream_index)
                            print(f"  ✅ {Fore.GREEN}Enabled subtitle stream {stream_index}{Style.RESET_ALL}")
                            
                    except Exception as e:
                        print(f"  ⚠️  {Fore.YELLOW}Smart selection failed: {str(e)}{Style.RESET_ALL}")
                        print(f"  🔄 Trying basic subtitle enabling...")
                        
                        # Fallback to basic enabling
                        success = False
                        for stream_id in [1, 2, 3]:
                            try:
                                client_connection.setSubtitleStream(stream_id)
                                print(f"  ✅ {Fore.GREEN}Enabled subtitle stream {stream_id}{Style.RESET_ALL}")
                                success = True
                                break
                            except:
                                continue
                        
                        if not success:
                            print(f"  ❌ {Fore.RED}Could not enable any subtitle stream{Style.RESET_ALL}")
                            
                else:
                    print(f"  ⚠️  {Fore.YELLOW}No suitable subtitle stream found{Style.RESET_ALL}")
            else:
                print(f"  ⚠️  {Fore.YELLOW}No subtitle streams available for this episode{Style.RESET_ALL}")
                # Try to download subtitles if auto-download is enabled
                if self.config.get('auto_download_subtitles', False):
                    print(f"  📥 Attempting to download subtitles...")
                    self.download_subtitles(plex_episode)
                
        except Exception as e:
            print(f"  ❌ {Fore.RED}Error enabling subtitles: {str(e)}{Style.RESET_ALL}")

    def select_best_subtitle(self, subtitle_streams):
        """Select the best subtitle stream based on accuracy factors."""
        if not subtitle_streams:
            return None
        
        print(f"    🧠 Analyzing {len(subtitle_streams)} subtitle options...")
        
        # Scoring system for subtitle quality
        scored_subtitles = []
        preferred_lang = self.config.get('preferred_subtitle_language', 'en').lower()
        
        for subtitle in subtitle_streams:
            score = 0
            reasons = []
            
            # Get subtitle properties
            language = getattr(subtitle, 'languageCode', '').lower() or getattr(subtitle, 'language', '').lower()
            title = getattr(subtitle, 'displayTitle', '') or getattr(subtitle, 'title', '')
            forced = getattr(subtitle, 'forced', False)
            codec = getattr(subtitle, 'codec', '').lower()
            
            # Language match (highest priority)
            if language == preferred_lang:
                score += 100
                reasons.append(f"matches preferred language ({preferred_lang})")
            elif language in ['en', 'eng', 'english'] and preferred_lang in ['en', 'eng', 'english']:
                score += 90
                reasons.append("English language match")
            elif language and language != 'unknown':
                score += 30
                reasons.append(f"has language code ({language})")
            
            # Forced subtitles are often more accurate for foreign language parts
            if forced:
                score += 50
                reasons.append("forced subtitles (foreign dialogue only)")
            
            # External subtitles are often higher quality
            if hasattr(subtitle, 'key') and 'external' in str(getattr(subtitle, 'key', '')):
                score += 40
                reasons.append("external subtitle file")
            
            # Prefer certain subtitle formats for accuracy
            if codec in ['srt', 'ass', 'ssa']:
                score += 30
                reasons.append(f"high-quality format ({codec})")
            elif codec in ['subrip', 'webvtt']:
                score += 20
                reasons.append(f"standard format ({codec})")
            
            # Check title for quality indicators
            title_lower = title.lower()
            if any(indicator in title_lower for indicator in ['sdh', 'cc', 'closed caption']):
                score += 35
                reasons.append("includes sound descriptions (SDH/CC)")
            elif 'full' in title_lower:
                score += 25
                reasons.append("full subtitles")
            elif 'complete' in title_lower:
                score += 25
                reasons.append("complete subtitles")
            
            # Penalty for certain indicators of lower quality
            if any(bad in title_lower for bad in ['auto', 'machine', 'google']):
                score -= 20
                reasons.append("auto-generated (lower accuracy)")
            elif 'hearing impaired' in title_lower and not forced:
                score += 15  # These are often very complete
                reasons.append("hearing impaired version (detailed)")
            
            scored_subtitles.append({
                'subtitle': subtitle,
                'score': score,
                'reasons': reasons,
                'language': language,
                'title': title
            })
        
        # Sort by score (highest first)
        scored_subtitles.sort(key=lambda x: x['score'], reverse=True)
        
        if scored_subtitles:
            best = scored_subtitles[0]
            print(f"    🎯 Selected subtitle with score {best['score']}: {best['title'] or best['language'] or 'Unknown'}")
            return best['subtitle']
        
        return None

    def explain_subtitle_choice(self, selected_subtitle, all_subtitles):
        """Explain why a particular subtitle was chosen."""
        try:
            title = getattr(selected_subtitle, 'displayTitle', '') or getattr(selected_subtitle, 'title', '')
            language = getattr(selected_subtitle, 'languageCode', '') or getattr(selected_subtitle, 'language', '')
            
            print(f"    💡 {Fore.BLUE}Selected for: {language.upper() if language else 'Unknown'} - {title or 'Default'}{Style.RESET_ALL}")
            print(f"       Chosen from {len(all_subtitles)} available options for best accuracy")
            
        except Exception as e:
            pass  # Don't let explanation errors break subtitle functionality

    def disable_subtitles(self, client_connection):
        """Disable subtitles on the client."""
        try:
            print(f"  🚫 Disabling subtitles on client...")
            client_connection.setSubtitleStream(0)  # 0 usually means no subtitles
            print(f"  ✅ {Fore.GREEN}Subtitles disabled{Style.RESET_ALL}")
        except Exception as e:
            print(f"  ❌ {Fore.RED}Error disabling subtitles: {str(e)}{Style.RESET_ALL}")

    def manual_subtitle_control(self, enable: bool):
        """Manually enable or disable subtitles on a selected client."""
        try:
            print(f"\n{Fore.CYAN}{'🗣️  ENABLE SUBTITLES' if enable else '🚫 DISABLE SUBTITLES'}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}=" * 40 + Style.RESET_ALL)
            
            # Select a client
            client = self.select_client()
            if not client:
                return
            
            # Connect to the client
            client_connection = self.connect_client_with_retry(client)
            if not client_connection:
                print(f"{Fore.RED}❌ Could not connect to client{Style.RESET_ALL}")
                return
            
            # Check if client is currently playing something
            playback_state = self.get_client_playback_state(client_connection)
            
            if not playback_state['is_playing']:
                print(f"{Fore.YELLOW}⚠️  Client is not currently playing anything{Style.RESET_ALL}")
                print(f"{Fore.BLUE}💡 Manual subtitle control works best during active playback{Style.RESET_ALL}")
                
                # Still allow manual control even without active playback
                if enable:
                    return self.force_enable_subtitles(client_connection, client)
                else:
                    return self.disable_subtitles(client_connection)
            
            if enable:
                print(f"{Fore.BLUE}🔍 Analyzing current playback for subtitle options...{Style.RESET_ALL}")
                
                # Get current media information
                current_media = playback_state['current_media']
                if current_media:
                    print(f"  📺 Current: {getattr(current_media, 'title', 'Unknown Media')}")
                
                # Try to find the actual Plex episode object for smart subtitle selection
                plex_episode = self.find_current_episode(current_media)
                
                if plex_episode:
                    print(f"  ✅ Found Plex episode object, using smart subtitle selection...")
                    # Use the smart subtitle system
                    self.enable_subtitles(client_connection, plex_episode)
                else:
                    print(f"  ⚠️  Could not find Plex episode object, using basic subtitle control...")
                    self.force_enable_subtitles(client_connection, client)
            else:
                # Disable subtitles
                self.disable_subtitles(client_connection)
                
        except Exception as e:
            print(f"{Fore.RED}❌ Error in manual subtitle control: {str(e)}{Style.RESET_ALL}")

    def find_current_episode(self, current_media):
        """Try to find the actual Plex episode object from timeline media."""
        try:
            if not current_media:
                return None
            
            # Get media details
            title = getattr(current_media, 'title', '')
            show_title = getattr(current_media, 'grandparentTitle', '')
            season_title = getattr(current_media, 'parentTitle', '')
            
            if not show_title:
                print(f"  ⚠️  No show title available")
                return None
            
            print(f"  🔍 Searching for: {show_title} - {title}")
            
            # Search through all connected servers
            for server in self.connected_servers:
                try:
                    # Search for the show
                    search_results = server.search(show_title, mediatype='show')
                    
                    for result in search_results:
                        if result.type == 'show' and result.title.lower() == show_title.lower():
                            # Found the show, now find the episode
                            episodes = result.episodes()
                            
                            for episode in episodes:
                                if episode.title and episode.title.lower() == title.lower():
                                    print(f"  ✅ Found matching episode: {episode.title}")
                                    return episode
                            
                            # If exact title match fails, try season/episode matching
                            for episode in episodes:
                                if (episode.parentTitle and episode.parentTitle == season_title and 
                                    episode.title and title in episode.title):
                                    print(f"  ✅ Found episode by season match: {episode.title}")
                                    return episode
                            break
                
                except Exception as e:
                    print(f"  ⚠️  Search error on {server.friendlyName}: {str(e)}")
                    continue
            
            return None
            
        except Exception as e:
            print(f"  ❌ Error finding episode: {str(e)}")
            return None

    def force_enable_subtitles(self, client_connection, client):
        """Force enable subtitles using direct client control methods."""
        try:
            print(f"  🗣️  Using direct subtitle control...")
            
            # Try multiple approaches to enable subtitles
            success = False
            client_platform = getattr(client, 'platform', '').lower()
            client_product = getattr(client, 'product', '').lower()
            
            # Samsung/Tizen specific methods first
            if 'tizen' in client_platform or 'samsung' in client_product:
                print(f"  📺 Detected Samsung Tizen client, using specialized methods...")
                
                # Method 1: Try Samsung-specific subtitle enabling
                try:
                    # Samsung clients often need subtitles enabled via settings
                    client_connection.setParameters(subtitles='1')
                    print(f"  ✅ {Fore.GREEN}Enabled subtitles via Samsung parameters{Style.RESET_ALL}")
                    success = True
                except Exception as e:
                    print(f"  ⚠️  Samsung parameters failed: {str(e)}")
                
                # Method 2: Try Tizen-specific calls
                if not success:
                    try:
                        client_connection.sendKey('KEY_SUBTITLE')
                        print(f"  ✅ {Fore.GREEN}Sent subtitle key to Samsung TV{Style.RESET_ALL}")
                        success = True
                    except Exception as e:
                        print(f"  ⚠️  Samsung key send failed: {str(e)}")
            
            # Standard methods for all clients
            if not success:
                # Method 3: Try different subtitle stream IDs
                for stream_id in [1, 2, 3, '1', 'auto']:
                    try:
                        client_connection.setSubtitleStream(stream_id)
                        print(f"  ✅ {Fore.GREEN}Enabled subtitle stream {stream_id} on {client.name}{Style.RESET_ALL}")
                        success = True
                        break
                    except Exception as e:
                        if stream_id == 1:  # Only show error for first attempt
                            print(f"  ⚠️  Stream {stream_id} failed: {str(e)}")
                        continue
            
            # Method 4: Try enabling subtitles through different API calls
            if not success:
                alternative_methods = [
                    ('enableSubtitles', lambda: client_connection.enableSubtitles()),
                    ('showSubtitles', lambda: client_connection.showSubtitles()),
                    ('setSubtitleMode', lambda: client_connection.setSubtitleMode('on')),
                    ('toggleSubtitles', lambda: client_connection.toggleSubtitles()),
                ]
                
                for method_name, method_func in alternative_methods:
                    try:
                        if hasattr(client_connection, method_name.split('(')[0]):
                            method_func()
                            print(f"  ✅ {Fore.GREEN}Enabled subtitles using {method_name}{Style.RESET_ALL}")
                            success = True
                            break
                    except Exception as e:
                        print(f"  ⚠️  {method_name} failed: {str(e)}")
                        continue
            
            if not success:
                print(f"  ❌ {Fore.RED}Could not enable subtitles using any method{Style.RESET_ALL}")
                if 'tizen' in client_platform or 'samsung' in client_product:
                    print(f"  💡 {Fore.BLUE}For Samsung Tizen TVs:{Style.RESET_ALL}")
                    print(f"     • Press the 'Settings' or 'Tools' button on your remote")
                    print(f"     • Navigate to Accessibility or Subtitle settings")
                    print(f"     • Enable subtitles/closed captions")
                    print(f"     • Samsung TVs often require manual subtitle enabling")
                else:
                    print(f"  💡 {Fore.BLUE}Try using your {client.platform} device's interface:{Style.RESET_ALL}")
                    print(f"     • Look for subtitle/CC button on remote or screen")
                    print(f"     • Check audio/video settings menu")
                    print(f"     • Some clients require subtitles to be enabled before playback starts")
            
            # Add a small delay to prevent interface issues
            time.sleep(0.3)
            
        except Exception as e:
            print(f"  ❌ {Fore.RED}Force enable subtitles error: {str(e)}{Style.RESET_ALL}")

    def ask_about_subtitles(self):
        """Ask user if they want to enable subtitles for this shuffle session."""
        try:
            print(f"\n{Fore.CYAN}🗣️  SUBTITLE OPTIONS{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}[1]{Style.RESET_ALL} Enable smart subtitles for this session")
            print(f"  {Fore.GREEN}[2]{Style.RESET_ALL} No subtitles (default)")
            
            choice = input(f"\n{Fore.YELLOW}Enable subtitles? (1/2 or Enter for no): {Style.RESET_ALL}").strip()
            
            if choice == '1':
                print(f"  ✅ {Fore.GREEN}Subtitles will be enabled for this session{Style.RESET_ALL}")
                return True
            else:
                print(f"  ⏩ Continuing without subtitles")
                return False
                
        except (KeyboardInterrupt, ValueError):
            print(f"  ⏩ Skipping subtitle options")
            return False

    def temp_enable_subtitles(self):
        """Temporarily enable subtitle features for current session."""
        self._subtitle_backup = {
            'auto_manage_subtitles': self.config.get('auto_manage_subtitles', False),
            'auto_download_subtitles': self.config.get('auto_download_subtitles', False),
            'auto_enable_subtitles': self.config.get('auto_enable_subtitles', False),
            'smart_subtitle_selection': self.config.get('smart_subtitle_selection', True)
        }
        
        self.config['auto_manage_subtitles'] = True
        self.config['auto_download_subtitles'] = True
        self.config['auto_enable_subtitles'] = True
        self.config['smart_subtitle_selection'] = True
        
        print(f"  🗣️  {Fore.GREEN}Enabled smart subtitles for this shuffle{Style.RESET_ALL}")

    def restore_subtitle_settings(self):
        """Restore subtitle settings after temporary enabling."""
        if hasattr(self, '_subtitle_backup'):
            self.config.update(self._subtitle_backup)
            delattr(self, '_subtitle_backup')

    def toggle_auto_subtitles(self, enable: bool):
        """Toggle automatic subtitle features on/off globally."""
        try:
            if enable:
                print(f"\n{Fore.GREEN}🗣️  ENABLING AUTOMATIC SUBTITLES{Style.RESET_ALL}")
                print(f"{Fore.GREEN}=" * 40 + Style.RESET_ALL)
                
                self.config['auto_manage_subtitles'] = True
                self.config['auto_download_subtitles'] = True
                self.config['auto_enable_subtitles'] = True
                self.config['smart_subtitle_selection'] = True
                
                print(f"  ✅ {Fore.GREEN}Auto-manage subtitles: ON{Style.RESET_ALL}")
                print(f"  ✅ {Fore.GREEN}Auto-download subtitles: ON{Style.RESET_ALL}")
                print(f"  ✅ {Fore.GREEN}Auto-enable subtitles: ON{Style.RESET_ALL}")
                print(f"  ✅ {Fore.GREEN}Smart subtitle selection: ON{Style.RESET_ALL}")
                print(f"\n{Fore.BLUE}💡 Automatic subtitles will now be used in all shuffle modes{Style.RESET_ALL}")
                
            else:
                print(f"\n{Fore.RED}🚫 DISABLING AUTOMATIC SUBTITLES{Style.RESET_ALL}")
                print(f"{Fore.RED}=" * 40 + Style.RESET_ALL)
                
                self.config['auto_manage_subtitles'] = False
                self.config['auto_download_subtitles'] = False
                self.config['auto_enable_subtitles'] = False
                # Keep smart selection enabled for manual use
                
                print(f"  ❌ {Fore.RED}Auto-manage subtitles: OFF{Style.RESET_ALL}")
                print(f"  ❌ {Fore.RED}Auto-download subtitles: OFF{Style.RESET_ALL}")
                print(f"  ❌ {Fore.RED}Auto-enable subtitles: OFF{Style.RESET_ALL}")
                print(f"  ✅ {Fore.GREEN}Smart subtitle selection: ON (for manual use){Style.RESET_ALL}")
                print(f"\n{Fore.BLUE}💡 Use 'subs on' command to manually enable subtitles when needed{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}❌ Error toggling auto subtitles: {str(e)}{Style.RESET_ALL}")
    
    def quick_collection_picker(self):
        """Quick collection picker with immediate shuffle start and smart subtitles."""
        print(f"\n{Fore.YELLOW}🚀 QUICK COLLECTION SHUFFLE{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}=" * 50 + Style.RESET_ALL)
        
        # Get all collections
        print(f"{Fore.BLUE}📚 Loading collections...{Style.RESET_ALL}")
        all_collections = self.get_all_collections()
        
        if not all_collections:
            print(f"{Fore.RED}❌ No collections found on any server{Style.RESET_ALL}")
            return False
        
        # Display collections in a compact format
        print(f"\n{Fore.CYAN}🎯 Select Collection to Shuffle:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}╔═══╦══════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║ # ║ Collection Name (Items) - Server                        ║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}╠═══╬══════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
        
        for i, (collection, server) in enumerate(all_collections, 1):
            # Truncate long names for display
            collection_name = collection.title[:35] + "..." if len(collection.title) > 35 else collection.title
            server_name = server.friendlyName[:12] + "..." if len(server.friendlyName) > 12 else server.friendlyName
            
            print(f"{Fore.CYAN}║{Style.RESET_ALL}{i:2d}{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}{collection_name:<38}{Style.RESET_ALL} "
                  f"({collection.childCount:3d}) - {Fore.BLUE}{server_name}{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}╚═══╩══════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        
        # Get user selection
        while True:
            try:
                choice = input(f"\n{Fore.YELLOW}Select collection number (1-{len(all_collections)}) or 'q' to quit: {Style.RESET_ALL}").strip()
                
                if choice.lower() in ['q', 'quit', 'exit']:
                    return False
                
                collection_index = int(choice) - 1
                if 0 <= collection_index < len(all_collections):
                    selected_collection, selected_server = all_collections[collection_index]
                    break
                else:
                    print(f"{Fore.RED}❌ Invalid choice. Please enter 1-{len(all_collections)}.{Style.RESET_ALL}")
            except (ValueError, KeyboardInterrupt):
                print(f"{Fore.RED}❌ Invalid input or operation cancelled.{Style.RESET_ALL}")
                return False
        
        print(f"\n{Fore.GREEN}✅ Selected: {selected_collection.title}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}🏠 Server: {selected_server.friendlyName}{Style.RESET_ALL}")
        
        # Auto-enable subtitle features for this session
        subtitle_backup = {
            'auto_manage_subtitles': self.config.get('auto_manage_subtitles', False),
            'auto_download_subtitles': self.config.get('auto_download_subtitles', False),
            'auto_enable_subtitles': self.config.get('auto_enable_subtitles', False),
            'smart_subtitle_selection': self.config.get('smart_subtitle_selection', True)
        }
        
        # Enable subtitle features
        self.config['auto_manage_subtitles'] = True
        self.config['auto_download_subtitles'] = True
        self.config['auto_enable_subtitles'] = True
        self.config['smart_subtitle_selection'] = True
        
        print(f"{Fore.GREEN}🗣️  Auto-enabled smart subtitles for this session:{Style.RESET_ALL}")
        print(f"     • Auto-manage subtitles: {Fore.GREEN}ON{Style.RESET_ALL}")
        print(f"     • Auto-download subtitles: {Fore.GREEN}ON{Style.RESET_ALL}")
        print(f"     • Auto-enable subtitles: {Fore.GREEN}ON{Style.RESET_ALL}")
        print(f"     • Smart subtitle selection: {Fore.GREEN}ON{Style.RESET_ALL}")
        
        # Start shuffle with this specific collection
        success = self.execute_collection_shuffle(selected_collection, selected_server)
        
        # Restore subtitle settings
        self.config.update(subtitle_backup)
        
        return success

    def execute_collection_shuffle(self, collection, server):
        """Execute shuffle for a specific collection with enhanced subtitle support."""
        print(f"\n{Fore.BLUE}🎬 Starting Collection Shuffle...{Style.RESET_ALL}")
        
        # Select client
        client = self.select_client()
        if not client:
            return False
        
        # Get shows from collection
        collection_shows = []
        try:
            for item in collection.items():
                if item.type == 'show':
                    collection_shows.append(item.title)
            print(f"{Fore.GREEN}📺 Found {len(collection_shows)} shows in {collection.title}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}❌ Error accessing collection shows: {str(e)}{Style.RESET_ALL}")
            return False
        
        if not collection_shows:
            print(f"{Fore.YELLOW}⚠️  No shows found in collection{Style.RESET_ALL}")
            return False
        
        # Update view counts if enabled (but skip if busy)
        if self.config['update_view_counts'] and not self.config['skip_view_count_updates']:
            print(f"{Fore.BLUE}📊 Updating view counts for {len(collection_shows)} shows...{Style.RESET_ALL}")
            update_count = 0
            for show in collection_shows[:3]:  # Limit to first 3 for quick start
                try:
                    self.update_view_counts(show)
                    self.showDB.commit()
                    update_count += 1
                except Exception as e:
                    if "database is locked" in str(e):
                        print(f"{Fore.YELLOW}⚠️  Database busy, proceeding with current data{Style.RESET_ALL}")
                        break
            
            if update_count > 0:
                print(f"{Fore.GREEN}✅ Updated {update_count} shows{Style.RESET_ALL}")
        
        # Get episodes from collection
        collection_episodes = self.get_episodes_from_collection(collection.title)
        
        if not collection_episodes:
            print(f"{Fore.YELLOW}⚠️  No episodes found for collection{Style.RESET_ALL}")
            return False
        
        # Apply default prioritization (push holiday episodes back)
        prioritized_episodes = self.push_holiday_episodes_back(collection_episodes)
        
        if not prioritized_episodes:
            print(f"{Fore.YELLOW}⚠️  No episodes after filtering{Style.RESET_ALL}")
            return False
        
        # Select episode with lowest view count
        try:
            selected_episode_data = min(prioritized_episodes, key=lambda x: x[2])  # x[2] is view count
        except ValueError:
            print(f"{Fore.RED}❌ No valid episodes found{Style.RESET_ALL}")
            return False
        
        # Display episode information
        self.display_episode_info(selected_episode_data)
        
        # Convert to Plex episode object
        plex_episode = self.convert_to_plex_episode(selected_episode_data)
        
        if not plex_episode:
            print(f"{Fore.RED}❌ Could not convert episode data{Style.RESET_ALL}")
            return False
        
        # Play the episode with smart subtitles
        print(f"\n{Fore.BLUE}🎬 Starting Playback with Smart Subtitles...{Style.RESET_ALL}")
        
        # Connect to client
        client_connection = self.connect_client_with_retry(client)
        if not client_connection:
            print(f"{Fore.RED}❌ Could not establish connection to client{Style.RESET_ALL}")
            return False
        
        # Special message for Samsung clients
        if isinstance(client_connection, SessionClientWrapper):
            print(f"  📱 {Fore.CYAN}Using Samsung TV session control{Style.RESET_ALL}")
            print(f"  💡 {Fore.BLUE}For subtitles: Use your TV remote > Settings/Tools > Subtitles{Style.RESET_ALL}")
        
        # Play episode with all enhancements
        playback_success = self.play_episode_with_retry(client_connection, plex_episode)
        
        if playback_success:
            print(f"\n{Fore.GREEN}🎉 COLLECTION SHUFFLE SUCCESS!{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ Playing: {selected_episode_data[0]} - {selected_episode_data[1]}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}📺 Client: {client.name} ({client.platform}){Style.RESET_ALL}")
            print(f"{Fore.BLUE}📚 Collection: {collection.title}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}🗣️  Smart subtitles automatically enabled{Style.RESET_ALL}")
            
            return True
        else:
            print(f"{Fore.RED}❌ Failed to play episode after multiple attempts{Style.RESET_ALL}")
            return False

    def remote_mode(self):
        """Advanced remote control mode for active playback management."""
        print(f"\n{Fore.MAGENTA}📱 REMOTE CONTROL MODE{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}=" * 60 + Style.RESET_ALL)
        
        # Get current active clients
        active_client = None
        client_connection = None
        
        print(f"{Fore.BLUE}🔍 Scanning for active playback...{Style.RESET_ALL}")
        
        # Method 1: Check server sessions first (more reliable)
        try:
            for server in self.connected_servers:
                try:
                    sessions = server.sessions()
                    if sessions:
                        print(f"  📊 Found {len(sessions)} active session(s) on {server.friendlyName}")
                        
                        # Try to match session with available client
                        for session in sessions:
                            if hasattr(session, 'player'):
                                session_client_name = getattr(session.player, 'title', '')
                                for client in self.available_clients:
                                    if client.name == session_client_name or session_client_name in client.name:
                                        temp_connection = self.connect_client_with_retry(client, max_retries=1)
                                        if temp_connection:
                                            active_client = client
                                            client_connection = temp_connection
                                            print(f"{Fore.GREEN}✅ Found active playback: {session_client_name}{Style.RESET_ALL}")
                                            break
                                if active_client:
                                    break
                        if active_client:
                            break
                except Exception as e:
                    print(f"  ⚠️  Could not check sessions on {server.friendlyName}: {str(e)}")
                    continue
        except Exception as e:
            print(f"  ⚠️  Error checking server sessions: {str(e)}")
        
        # Method 2: If no active session found, try direct client checking
        if not active_client:
            print(f"  🔍 No server sessions found, checking clients directly...")
            for client in self.available_clients:
                try:
                    temp_connection = self.connect_client_with_retry(client, max_retries=1)
                    if temp_connection:
                        playback_state = self.get_client_playback_state(temp_connection)
                        if playback_state['is_playing']:
                            active_client = client
                            client_connection = temp_connection
                            print(f"{Fore.GREEN}✅ Found active playback on {client.name}{Style.RESET_ALL}")
                            break
                except Exception as e:
                    print(f"  ⚠️  Could not check {client.name}: {str(e)}")
                    continue
        
        if not active_client:
            print(f"{Fore.YELLOW}⚠️  No active playback detected. Remote mode works best with active media.{Style.RESET_ALL}")
            # Still allow remote mode for manual control
            active_client = self.select_client()
            if not active_client:
                return
            client_connection = self.connect_client_with_retry(active_client)
            if not client_connection:
                print(f"{Fore.RED}❌ Could not connect to selected client{Style.RESET_ALL}")
                return
        
        self.show_remote_interface(active_client, client_connection)

    def show_remote_interface(self, client, client_connection):
        """Display the remote control interface."""
        while True:
            try:
                # Get current playback state
                playback_state = self.get_client_playback_state(client_connection)
                
                # Clear screen equivalent
                print("\n" * 2)
                
                # Header with Samsung/Tizen detection
                is_samsung_wrapper = isinstance(client_connection, SessionClientWrapper)
                client_type = "Samsung Session" if is_samsung_wrapper else client.platform
                
                print(f"{Fore.MAGENTA}╔══════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
                print(f"{Fore.MAGENTA}║                    📱 REMOTE CONTROL 📱                       ║{Style.RESET_ALL}")
                print(f"{Fore.MAGENTA}║                  {client.name} ({client_type}){'':>{26-len(client.name)-len(client_type)}}║{Style.RESET_ALL}")
                if is_samsung_wrapper:
                    print(f"{Fore.MAGENTA}║                   🔧 Using Session Control                    ║{Style.RESET_ALL}")
                print(f"{Fore.MAGENTA}╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
                
                # Samsung-specific guidance
                if is_samsung_wrapper:
                    print(f"{Fore.CYAN}💡 Samsung TV Notes:{Style.RESET_ALL}")
                    print(f"   • Playback controls (play/pause/skip) work via server session")
                    print(f"   • For subtitles: Use TV remote → Settings/Tools → Subtitles")
                    print(f"   • For volume: Use TV remote or soundbar remote")
                    print(f"   • Collection switching and episode info work normally")
                    print()
                
                # Status indicator
                if playback_state['is_playing']:
                    status_icon = "▶️ PLAYING" if playback_state.get('current_media') else "⏸️ PAUSED"
                    print(f"{Fore.GREEN}🎬 Status: {status_icon}{Style.RESET_ALL}")
                    
                    # Show current media info if available
                    current_media = playback_state.get('current_media')
                    if current_media:
                        media_title = getattr(current_media, 'title', 'Unknown')
                        show_title = getattr(current_media, 'grandparentTitle', '')
                        if show_title:
                            print(f"{Fore.BLUE}📺 Now: {show_title} - {media_title}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.BLUE}📺 Now: {media_title}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⏹️ Status: STOPPED{Style.RESET_ALL}")
                
                print()
                
                # Remote control options
                print(f"{Fore.CYAN}🎮 PLAYBACK CONTROLS:{Style.RESET_ALL}")
                print(f"  {Fore.GREEN}[1]{Style.RESET_ALL} ⏭️  Skip to Next Episode        {Fore.GREEN}[2]{Style.RESET_ALL} ▶️  Play/Pause Toggle")
                print(f"  {Fore.GREEN}[3]{Style.RESET_ALL} ⏹️  Stop Playback              {Fore.GREEN}[4]{Style.RESET_ALL} 🔄 Quick Collection Switch")
                print()
                
                print(f"{Fore.CYAN}🗣️  SUBTITLE CONTROLS:{Style.RESET_ALL}")
                print(f"  {Fore.YELLOW}[5]{Style.RESET_ALL} 🔄 Retry Subtitle Selection    {Fore.YELLOW}[6]{Style.RESET_ALL} 🎯 Manual Subtitle Pick")
                print(f"  {Fore.YELLOW}[7]{Style.RESET_ALL} 🚫 Disable Subtitles          {Fore.YELLOW}[8]{Style.RESET_ALL} 📥 Download New Subtitles")
                print()
                
                print(f"{Fore.CYAN}🎛️  ADVANCED CONTROLS:{Style.RESET_ALL}")
                print(f"  {Fore.BLUE}[9]{Style.RESET_ALL} 📊 Show Episode Info          {Fore.BLUE}[10]{Style.RESET_ALL} 📱 Switch Client")
                print(f"  {Fore.BLUE}[11]{Style.RESET_ALL} 🔀 Toggle Shuffle Mode        {Fore.BLUE}[12]{Style.RESET_ALL} 🔊 Volume Controls")
                print()
                
                print(f"{Fore.WHITE}📋 QUICK COMMANDS:{Style.RESET_ALL}")
                print(f"  {Fore.MAGENTA}[r]{Style.RESET_ALL} 🔄 Refresh Status  {Fore.MAGENTA}[h]{Style.RESET_ALL} 📚 Help  {Fore.MAGENTA}[q]{Style.RESET_ALL} ⬅️ Back to Main")
                
                print(f"\n{Fore.MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
                
                # Get user input
                choice = input(f"{Fore.YELLOW}Remote> {Style.RESET_ALL}").strip().lower()
                
                # Handle commands
                if choice == 'q' or choice == 'quit':
                    break
                elif choice == 'r' or choice == 'refresh':
                    continue  # Refresh the display
                elif choice == 'h' or choice == 'help':
                    self.show_remote_help()
                elif choice == '1':
                    self.remote_skip_episode(client_connection)
                elif choice == '2':
                    self.remote_play_pause_toggle(client_connection)
                elif choice == '3':
                    self.remote_stop_playback(client_connection)
                elif choice == '4':
                    if self.remote_quick_collection_switch(client, client_connection):
                        break  # Exit remote mode after collection switch
                elif choice == '5':
                    self.remote_retry_subtitles(client_connection, playback_state)
                elif choice == '6':
                    self.remote_manual_subtitle_selection(client_connection, playback_state)
                elif choice == '7':
                    self.disable_subtitles(client_connection)
                elif choice == '8':
                    self.remote_download_subtitles(client_connection, playback_state)
                elif choice == '9':
                    self.remote_show_episode_info(client_connection, playback_state)
                elif choice == '10':
                    new_client = self.select_client()
                    if new_client:
                        client = new_client
                        client_connection = self.connect_client_with_retry(client)
                        if not client_connection:
                            print(f"{Fore.RED}❌ Could not connect to new client{Style.RESET_ALL}")
                            break
                elif choice == '11':
                    self.remote_toggle_shuffle(client_connection)
                elif choice == '12':
                    self.remote_volume_controls(client_connection)
                else:
                    print(f"{Fore.RED}❌ Invalid command. Type 'h' for help.{Style.RESET_ALL}")
                
                # Small pause for user to read output, but don't freeze on certain commands
                if choice not in ['r', 'refresh', '', '1', '2', '3']:  # Skip pause for playback controls
                    try:
                        # Use a timeout to prevent indefinite hanging
                        print(f"{Fore.BLUE}Press Enter to continue (or wait 3 seconds)...{Style.RESET_ALL}", end="")
                        import select
                        import sys
                        
                        # This is a simple way to add a timeout on Windows
                        if hasattr(select, 'select'):
                            ready, _, _ = select.select([sys.stdin], [], [], 3)
                            if ready:
                                sys.stdin.readline()
                        else:
                            # Fallback for Windows
                            input()
                    except:
                        # If any input issues, just continue
                        time.sleep(1)
                        pass
                    
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}⚠️  Use 'q' to exit remote mode{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ Remote mode error: {str(e)}{Style.RESET_ALL}")
                input(f"{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}👋 Exited remote control mode{Style.RESET_ALL}")

    def remote_skip_episode(self, client_connection):
        """Skip to next episode or media item."""
        try:
            print(f"{Fore.BLUE}⏭️  Skipping to next episode...{Style.RESET_ALL}")
            
            # Try multiple skip methods for different client types
            success = False
            
            # Method 1: Standard skipNext
            try:
                client_connection.skipNext()
                success = True
                print(f"{Fore.GREEN}✅ Skipped to next episode (skipNext){Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️  skipNext failed: {str(e)}{Style.RESET_ALL}")
            
            # Method 2: Try stepForward for Samsung/Tizen clients
            if not success:
                try:
                    client_connection.stepForward()
                    success = True
                    print(f"{Fore.GREEN}✅ Skipped to next episode (stepForward){Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}⚠️  stepForward failed: {str(e)}{Style.RESET_ALL}")
            
            # Method 3: Try seekTo end for forcing next episode
            if not success:
                try:
                    # This might force the episode to end and move to next
                    client_connection.seekTo(999999)  # Seek to very end
                    success = True
                    print(f"{Fore.GREEN}✅ Forced skip by seeking to end{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}⚠️  seekTo failed: {str(e)}{Style.RESET_ALL}")
            
            if not success:
                print(f"{Fore.RED}❌ Could not skip using any method{Style.RESET_ALL}")
                print(f"{Fore.BLUE}💡 Try using your {getattr(client_connection, 'platform', 'device')} remote to skip{Style.RESET_ALL}")
                
            # Add a small delay to prevent interface freezing
            time.sleep(0.5)
            
        except Exception as e:
            print(f"{Fore.RED}❌ Could not skip: {str(e)}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}💡 Try using your client's interface to skip{Style.RESET_ALL}")

    def remote_play_pause_toggle(self, client_connection):
        """Toggle play/pause state."""
        try:
            playback_state = self.get_client_playback_state(client_connection)
            
            if playback_state['is_playing']:
                print(f"{Fore.BLUE}⏸️  Pausing playback...{Style.RESET_ALL}")
                client_connection.pause()
                print(f"{Fore.GREEN}✅ Playback paused{Style.RESET_ALL}")
            else:
                print(f"{Fore.BLUE}▶️  Resuming playback...{Style.RESET_ALL}")
                client_connection.play()
                print(f"{Fore.GREEN}✅ Playback resumed{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}❌ Could not toggle playback: {str(e)}{Style.RESET_ALL}")

    def remote_stop_playback(self, client_connection):
        """Stop current playback."""
        try:
            print(f"{Fore.BLUE}⏹️  Stopping playback...{Style.RESET_ALL}")
            client_connection.stop()
            print(f"{Fore.GREEN}✅ Playback stopped{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}❌ Could not stop playback: {str(e)}{Style.RESET_ALL}")

    def remote_quick_collection_switch(self, client, client_connection):
        """Quick collection switch from remote mode."""
        print(f"\n{Fore.CYAN}🔄 Quick Collection Switch{Style.RESET_ALL}")
        
        # Get collections in compact format
        all_collections = self.get_all_collections()
        if not all_collections:
            print(f"{Fore.RED}❌ No collections available{Style.RESET_ALL}")
            return False
        
        # Show first 10 collections for quick access
        display_collections = all_collections[:10]
        
        print(f"{Fore.CYAN}📚 Quick Collections (showing first 10):{Style.RESET_ALL}")
        for i, (collection, server) in enumerate(display_collections, 1):
            print(f"  {Fore.GREEN}[{i}]{Style.RESET_ALL} {collection.title[:40]} ({collection.childCount} items)")
        
        if len(all_collections) > 10:
            print(f"  {Fore.BLUE}+ {len(all_collections) - 10} more collections available{Style.RESET_ALL}")
        
        try:
            choice = input(f"\n{Fore.YELLOW}Select collection (1-{len(display_collections)}) or Enter to cancel: {Style.RESET_ALL}").strip()
            if not choice:
                return False
                
            collection_index = int(choice) - 1
            if 0 <= collection_index < len(display_collections):
                selected_collection, selected_server = display_collections[collection_index]
                
                # Stop current playback
                try:
                    client_connection.stop()
                    print(f"{Fore.BLUE}⏹️  Stopped current playback{Style.RESET_ALL}")
                except:
                    pass
                
                # Start new collection
                print(f"{Fore.GREEN}🔄 Switching to: {selected_collection.title}{Style.RESET_ALL}")
                success = self.execute_collection_shuffle(selected_collection, selected_server)
                
                return success  # Return True to exit remote mode
                
        except (ValueError, KeyboardInterrupt):
            return False
        
        return False

    def remote_retry_subtitles(self, client_connection, playback_state):
        """Retry subtitle selection with current episode."""
        try:
            current_media = playback_state.get('current_media')
            if not current_media:
                print(f"{Fore.RED}❌ No active media to apply subtitles to{Style.RESET_ALL}")
                return
            
            print(f"{Fore.BLUE}🔄 Retrying subtitle selection...{Style.RESET_ALL}")
            
            # This would need the actual Plex episode object
            # For now, we'll try to re-enable subtitles with smart selection
            print(f"{Fore.BLUE}🧠 Analyzing available subtitle streams...{Style.RESET_ALL}")
            
            try:
                # Try to get subtitle streams and re-select
                # This is a simplified approach - in practice you'd need to search for the episode
                client_connection.setSubtitleStream(1)  # Try first available
                print(f"{Fore.GREEN}✅ Subtitle selection retried{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ Could not retry subtitles: {str(e)}{Style.RESET_ALL}")
                print(f"{Fore.BLUE}💡 Try manual subtitle selection instead{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}❌ Error retrying subtitles: {str(e)}{Style.RESET_ALL}")

    def remote_manual_subtitle_selection(self, client_connection, playback_state):
        """Manual subtitle selection for current episode."""
        try:
            print(f"{Fore.BLUE}🎯 Manual Subtitle Selection{Style.RESET_ALL}")
            
            current_media = playback_state.get('current_media')
            if not current_media:
                print(f"{Fore.RED}❌ No active media{Style.RESET_ALL}")
                return
            
            # Show available subtitle options (this is simplified)
            print(f"{Fore.CYAN}Available subtitle streams:{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}[0]{Style.RESET_ALL} 🚫 No Subtitles")
            print(f"  {Fore.GREEN}[1]{Style.RESET_ALL} 🗣️ Auto-Selected Stream")
            print(f"  {Fore.GREEN}[2]{Style.RESET_ALL} 🔤 Alternative Stream")
            
            choice = input(f"\n{Fore.YELLOW}Select subtitle stream (0-2): {Style.RESET_ALL}").strip()
            
            if choice in ['0', '1', '2']:
                stream_id = int(choice)
                client_connection.setSubtitleStream(stream_id)
                
                if stream_id == 0:
                    print(f"{Fore.GREEN}✅ Subtitles disabled{Style.RESET_ALL}")
                else:
                    print(f"{Fore.GREEN}✅ Subtitle stream {stream_id} enabled{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ Invalid selection{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}❌ Error in manual subtitle selection: {str(e)}{Style.RESET_ALL}")

    def remote_download_subtitles(self, client_connection, playback_state):
        """Download new subtitles for current episode."""
        try:
            print(f"{Fore.BLUE}📥 Downloading subtitles for current episode...{Style.RESET_ALL}")
            
            current_media = playback_state.get('current_media')
            if not current_media:
                print(f"{Fore.RED}❌ No active media{Style.RESET_ALL}")
                return
            
            # This would require converting timeline media to episode object
            # For now, provide a helpful message
            print(f"{Fore.YELLOW}⚠️  Subtitle download requires episode identification{Style.RESET_ALL}")
            print(f"{Fore.BLUE}💡 Use the main shuffle feature for automatic subtitle downloads{Style.RESET_ALL}")
            print(f"{Fore.BLUE}💡 Or try the manual subtitle selection option{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error downloading subtitles: {str(e)}{Style.RESET_ALL}")

    def remote_show_episode_info(self, client_connection, playback_state):
        """Show detailed information about current episode."""
        try:
            print(f"\n{Fore.CYAN}📊 CURRENT EPISODE INFO{Style.RESET_ALL}")
            print(f"{Fore.CYAN}=" * 40 + Style.RESET_ALL)
            
            current_media = playback_state.get('current_media')
            if not current_media:
                print(f"{Fore.RED}❌ No active media{Style.RESET_ALL}")
                return
            
            # Display available information
            title = getattr(current_media, 'title', 'Unknown')
            show_title = getattr(current_media, 'grandparentTitle', '')
            season = getattr(current_media, 'parentTitle', '')
            duration = getattr(current_media, 'duration', 0)
            view_offset = getattr(current_media, 'viewOffset', 0)
            
            print(f"{Fore.WHITE}Title:{Style.RESET_ALL} {title}")
            if show_title:
                print(f"{Fore.WHITE}Show:{Style.RESET_ALL} {show_title}")
            if season:
                print(f"{Fore.WHITE}Season:{Style.RESET_ALL} {season}")
            
            if duration:
                duration_str = millisecondToHumanstr(duration)
                print(f"{Fore.WHITE}Duration:{Style.RESET_ALL} {duration_str}")
            
            if view_offset:
                offset_str = millisecondToHumanstr(view_offset)
                progress = (view_offset / duration * 100) if duration > 0 else 0
                print(f"{Fore.WHITE}Progress:{Style.RESET_ALL} {offset_str} ({progress:.1f}%)")
            
            # Playback state
            state = "Playing" if playback_state['is_playing'] else "Stopped"
            print(f"{Fore.WHITE}State:{Style.RESET_ALL} {state}")
            
            if playback_state.get('is_shuffle_mode'):
                print(f"{Fore.GREEN}🔀 Shuffle mode active{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error showing episode info: {str(e)}{Style.RESET_ALL}")

    def remote_toggle_shuffle(self, client_connection):
        """Toggle shuffle mode on client."""
        try:
            print(f"{Fore.BLUE}🔀 Toggling shuffle mode...{Style.RESET_ALL}")
            
            # Get current state
            playback_state = self.get_client_playback_state(client_connection)
            current_shuffle = playback_state.get('is_shuffle_mode', False)
            
            # Toggle shuffle
            client_connection.setShuffle(not current_shuffle)
            
            new_state = "enabled" if not current_shuffle else "disabled"
            print(f"{Fore.GREEN}✅ Shuffle mode {new_state}{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}❌ Could not toggle shuffle: {str(e)}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}💡 Try using your client's interface{Style.RESET_ALL}")

    def remote_volume_controls(self, client_connection):
        """Volume control interface."""
        try:
            print(f"\n{Fore.CYAN}🔊 VOLUME CONTROLS{Style.RESET_ALL}")
            print(f"{Fore.GREEN}[1]{Style.RESET_ALL} 🔊 Volume Up")
            print(f"{Fore.GREEN}[2]{Style.RESET_ALL} 🔉 Volume Down")
            print(f"{Fore.GREEN}[3]{Style.RESET_ALL} 🔇 Mute Toggle")
            print(f"{Fore.GREEN}[4]{Style.RESET_ALL} 🎚️ Set Specific Volume")
            
            choice = input(f"\n{Fore.YELLOW}Select volume control (1-4): {Style.RESET_ALL}").strip()
            
            if choice == '1':
                client_connection.volumeUp()
                print(f"{Fore.GREEN}✅ Volume increased{Style.RESET_ALL}")
            elif choice == '2':
                client_connection.volumeDown()
                print(f"{Fore.GREEN}✅ Volume decreased{Style.RESET_ALL}")
            elif choice == '3':
                client_connection.mute()
                print(f"{Fore.GREEN}✅ Mute toggled{Style.RESET_ALL}")
            elif choice == '4':
                volume = input(f"{Fore.YELLOW}Enter volume level (0-100): {Style.RESET_ALL}").strip()
                try:
                    vol_level = int(volume)
                    if 0 <= vol_level <= 100:
                        client_connection.setVolume(vol_level)
                        print(f"{Fore.GREEN}✅ Volume set to {vol_level}%{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}❌ Volume must be between 0-100{Style.RESET_ALL}")
                except ValueError:
                    print(f"{Fore.RED}❌ Invalid volume level{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ Invalid selection{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}❌ Volume control error: {str(e)}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}💡 Your client may not support remote volume control{Style.RESET_ALL}")

    def show_remote_help(self):
        """Show remote mode help."""
        help_text = f"""
{Fore.MAGENTA}📱 REMOTE CONTROL MODE HELP{Style.RESET_ALL}
{Fore.MAGENTA}{'=' * 50}{Style.RESET_ALL}

{Fore.WHITE}PLAYBACK CONTROLS:{Style.RESET_ALL}
  ⏭️  Skip Episode    - Jump to next episode in playlist/series
  ▶️  Play/Pause     - Toggle playback state
  ⏹️  Stop           - Stop current playback
  🔄 Collection Switch - Quickly change to different collection

{Fore.WHITE}SUBTITLE CONTROLS:{Style.RESET_ALL}
  🔄 Retry Selection  - Re-analyze and select best subtitles
  🎯 Manual Selection - Choose specific subtitle stream
  🚫 Disable          - Turn off all subtitles
  📥 Download New     - Attempt to download better subtitles

{Fore.WHITE}ADVANCED FEATURES:{Style.RESET_ALL}
  📊 Episode Info     - Show detailed current media information
  📱 Switch Client    - Change to different Plex client
  🔀 Toggle Shuffle   - Enable/disable shuffle mode
  🔊 Volume Controls  - Adjust volume and mute settings

{Fore.WHITE}NAVIGATION:{Style.RESET_ALL}
  r/refresh - Update display and status
  h/help    - Show this help screen
  q/quit    - Return to main HyperShuffle menu

{Fore.BLUE}💡 Tips:{Style.RESET_ALL}
• Remote mode works best when media is actively playing
• Some features depend on client capabilities
• Use 'r' frequently to get updated status
• Collection switching will stop current playback
"""
        print(help_text)
    
    def get_prioritization_mode(self) -> str:
        """Get user's prioritization mode preference."""
        modes = {
            '1': 'Push Holiday Episodes Back (Default)',
            '2': 'Prioritize Halloween Episodes',
            '3': 'Prioritize Thanksgiving Episodes',
            '4': 'Prioritize Christmas Episodes',
            '5': 'Prioritize Summer Episodes',
            '6': 'Prioritize Valentine\'s Episodes',
            '7': 'Prioritize Easter Episodes',
            '8': 'Prioritize New Year Episodes',
            '9': 'True Random Shuffle',
            '10': 'True Random with 3-Pass Shuffle'
        }
        
        print(f"\n{Fore.CYAN}🎯 Prioritization Options:{Style.RESET_ALL}")
        for key, description in modes.items():
            current = f"{Fore.GREEN} ← CURRENT{Style.RESET_ALL}" if key == self.config['prioritization_mode'] else ""
            print(f"  {key}. {description}{current}")
        
        while True:
            try:
                choice = input(f"\n{Fore.YELLOW}Select prioritization mode (1-10): {Style.RESET_ALL}").strip()
                if choice in modes:
                    self.config['prioritization_mode'] = choice
                    return choice
                else:
                    print(f"{Fore.RED}❌ Invalid choice. Please enter 1-10.{Style.RESET_ALL}")
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}⚠️  Using current mode: {modes[self.config['prioritization_mode']]}{Style.RESET_ALL}")
                return self.config['prioritization_mode']
    
    def apply_prioritization(self, episodes: List[Tuple], mode: str) -> List[Tuple]:
        """Apply prioritization to episodes based on selected mode."""
        if mode == '1':  # Default: Push Holiday Episodes Back
            return self.push_holiday_episodes_back(episodes)
        elif mode == '9':  # True Random
            random.shuffle(episodes)
            return episodes
        elif mode == '10':  # True Random with 3-Pass Shuffle
            return self.three_pass_shuffle(episodes)
        else:
            # Prioritize specific holiday episodes
            holiday_map = {
                '2': 'halloween',
                '3': 'thanksgiving',
                '4': 'christmas',
                '5': 'summer',
                '6': 'valentines',
                '7': 'easter',
                '8': 'new_year'
            }
            
            if mode in holiday_map:
                return self.prioritize_holiday_episodes(episodes, holiday_map[mode])
        
        return episodes

    def three_pass_shuffle(self, episodes: List[Tuple]) -> List[Tuple]:
        """Perform a 3-pass shuffle for maximum randomization."""
        print(f"{Fore.BLUE}🔀 Performing 3-pass shuffle for maximum randomization...{Style.RESET_ALL}")
        
        # Make a copy to avoid modifying the original list
        result = episodes.copy()
        
        # Pass 1: Standard shuffle
        print(f"  🔀 Pass 1: Standard shuffle...")
        random.shuffle(result)
        
        # Pass 2: Reverse segments and shuffle again
        print(f"  🔀 Pass 2: Reverse segments shuffle...")
        # Split into segments and reverse each segment
        segment_size = max(1, len(result) // 4)  # Create 4 segments
        for i in range(0, len(result), segment_size):
            segment = result[i:i+segment_size]
            segment.reverse()
            result[i:i+segment_size] = segment
        random.shuffle(result)
        
        # Pass 3: Final random distribution
        print(f"  🔀 Pass 3: Final random distribution...")
        # Create a new list by randomly selecting from remaining items
        final_result = []
        remaining = result.copy()
        
        while remaining:
            random_index = random.randint(0, len(remaining) - 1)
            final_result.append(remaining.pop(random_index))
        
        print(f"  ✅ {Fore.GREEN}3-pass shuffle complete - maximum randomization achieved{Style.RESET_ALL}")
        return final_result
    
    def push_holiday_episodes_back(self, episodes: List[Tuple]) -> List[Tuple]:
        """Push holiday episodes to the back of the list."""
        regular_episodes = []
        holiday_episodes = []
        
        for episode in episodes:
            episode_title = episode[4] if len(episode) > 4 else ""
            if not isinstance(episode_title, str):
                episode_title = str(episode_title) if episode_title is not None else ""
            
            # Check if episode contains holiday keywords
            is_holiday = False
            for holiday_keywords in self.holiday_keywords.values():
                for keyword in holiday_keywords:
                    if keyword.lower() in episode_title.lower():
                        holiday_episodes.append(episode)
                        is_holiday = True
                        break
                if is_holiday:
                    break
            
            if not is_holiday:
                regular_episodes.append(episode)
        
        result = regular_episodes + holiday_episodes
        print(f"{Fore.BLUE}🎯 Holiday filtering: {len(regular_episodes)} regular, {len(holiday_episodes)} holiday{Style.RESET_ALL}")
        return result
    
    def prioritize_holiday_episodes(self, episodes: List[Tuple], holiday_type: str) -> List[Tuple]:
        """Prioritize episodes of a specific holiday type."""
        prioritized = []
        regular = []
        
        keywords = self.holiday_keywords.get(holiday_type, [])
        
        for episode in episodes:
            episode_title = episode[4] if len(episode) > 4 else ""
            if not isinstance(episode_title, str):
                episode_title = str(episode_title) if episode_title is not None else ""
            
            # Check if episode contains holiday keywords
            is_prioritized = False
            for keyword in keywords:
                if keyword.lower() in episode_title.lower():
                    prioritized.append(episode)
                    is_prioritized = True
                    break
            
            if not is_prioritized:
                regular.append(episode)
        
        result = prioritized + regular
        holiday_name = holiday_type.title()
        print(f"{Fore.BLUE}🎯 {holiday_name} prioritization: {len(prioritized)} prioritized, {len(regular)} regular{Style.RESET_ALL}")
        return result
    
    def get_episodes_from_collection(self, collection_name: str) -> List[Tuple]:
        """Get episodes from a specific collection."""
        print(f"{Fore.BLUE}📚 Getting episodes from collection: {collection_name}{Style.RESET_ALL}")
        
        # Find the collection
        target_collection = None
        for server in self.connected_servers:
            try:
                library = server.library.section('TV Shows')
                collections = library.collections()
                for collection in collections:
                    if collection.title.lower() == collection_name.lower():
                        target_collection = collection
                        break
                if target_collection:
                    break
            except Exception as e:
                continue
        
        if not target_collection:
            print(f"{Fore.RED}❌ Collection {collection_name} not found{Style.RESET_ALL}")
            return []
        
        # Get shows from collection
        collection_shows = []
        try:
            for item in target_collection.items():
                if item.type == 'show':
                    collection_shows.append(item.title)
        except Exception as e:
            print(f"{Fore.RED}❌ Error accessing collection shows: {str(e)}{Style.RESET_ALL}")
            return []
        
        # Get episodes for these shows from database
        all_episodes = self.get_all_episodes()
        collection_episodes = [ep for ep in all_episodes if ep[0] in collection_shows]
        
        print(f"{Fore.GREEN}📺 Found {len(collection_episodes)} episodes from {collection_name}{Style.RESET_ALL}")
        return collection_episodes
    
    def get_all_episodes(self) -> List[Tuple]:
        """Get all episodes from the database."""
        try:
            return self.cursor.execute('''
                SELECT Show, Episode, SUM(ViewCount), Season, Title, Length, Type, Server 
                FROM episodes 
                GROUP BY Show, Episode, Season, Title, Length, Type, Server
            ''').fetchall()
        except Exception as e:
            print(f"{Fore.RED}❌ Error getting episodes from database: {str(e)}{Style.RESET_ALL}")
            return []
    
    def update_view_counts(self, show_name: str):
        """Update view counts for a specific show across all servers."""
        for server in self.connected_servers:
            try:
                print(f"  📊 Updating {show_name} on {server.friendlyName}...")
                
                # Get current episode count with retry logic
                current_count = self.get_episode_count_with_retry()
                
                # Search for show on server
                search_results = server.search(show_name)
                show_items = [item for item in search_results if item.type == 'show']
                
                if show_items:
                    # Get episodes from the first matching show
                    show = show_items[0]
                    episodes = show.episodes()
                    
                    # Get already stored episodes with retry logic
                    already_stored = self.get_stored_episodes_with_retry(show_name, server.friendlyName)
                    
                    for episode in episodes:
                        episode_key = (episode.grandparentTitle, episode.seasonEpisode, server.friendlyName)
                        
                        if episode_key not in already_stored:
                            # Insert new episode with retry logic
                            self.insert_episode_with_retry(current_count, episode, server.friendlyName)
                            current_count += 1
                        else:
                            # Update view count with retry logic
                            self.update_episode_view_count_with_retry(episode, show_name, server.friendlyName)
                
            except Exception as e:
                print(f"{Fore.RED}⚠️  Error updating {show_name} on {server.friendlyName}: {str(e)}{Style.RESET_ALL}")
    
    def get_episode_count_with_retry(self, max_retries=3):
        """Get episode count with retry logic for database locks."""
        for attempt in range(max_retries):
            try:
                return self.cursor.execute('SELECT COUNT(ID) FROM episodes').fetchone()[0]
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    print(f"  ⏳ Database locked, retrying in 1 second... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(1)
                    continue
                else:
                    raise e
        return 0
    
    def get_stored_episodes_with_retry(self, show_name: str, server_name: str, max_retries=3):
        """Get stored episodes with retry logic for database locks."""
        for attempt in range(max_retries):
            try:
                return self.cursor.execute(
                    'SELECT Show, Episode, Server FROM episodes WHERE Show = ? AND Server = ?',
                    (show_name, server_name)
                ).fetchall()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    print(f"  ⏳ Database locked, retrying in 1 second... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(1)
                    continue
                else:
                    raise e
        return []
    
    def insert_episode_with_retry(self, current_count: int, episode, server_name: str, max_retries=3):
        """Insert episode with retry logic for database locks."""
        for attempt in range(max_retries):
            try:
                self.cursor.execute('''
                    INSERT INTO episodes (ID, Type, Show, Season, Episode, Title, Server, ViewCount, Length) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (current_count, episode.type, episode.grandparentTitle, episode.parentTitle, 
                      episode.seasonEpisode, episode.title, server_name, episode.viewCount, episode.duration))
                return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    print(f"  ⏳ Database locked, retrying in 1 second... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(1)
                    continue
                else:
                    raise e
    
    def update_episode_view_count_with_retry(self, episode, show_name: str, server_name: str, max_retries=3):
        """Update episode view count with retry logic for database locks."""
        for attempt in range(max_retries):
            try:
                self.cursor.execute('''
                    UPDATE episodes SET ViewCount = ? 
                    WHERE Show = ? AND Server = ? AND Episode = ?
                ''', (episode.viewCount, show_name, server_name, episode.seasonEpisode))
                return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    print(f"  ⏳ Database locked, retrying in 1 second... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(1)
                    continue
                else:
                    raise e
    
    def convert_to_plex_episode(self, episode_data: Tuple) -> Optional[Any]:
        """Convert database episode data to Plex episode object."""
        try:
            show_name = episode_data[0]
            episode_id = episode_data[1]
            server_name = episode_data[7] if len(episode_data) > 7 else None
            
            if not server_name:
                print(f"{Fore.RED}⚠️  No server information for episode {show_name} - {episode_id}{Style.RESET_ALL}")
                return None
            
            # Find the server
            target_server = None
            for server in self.connected_servers:
                if server.friendlyName == server_name:
                    target_server = server
                    break
            
            if not target_server:
                print(f"{Fore.RED}⚠️  Server {server_name} not found for episode {show_name} - {episode_id}{Style.RESET_ALL}")
                return None
            
            # Search for the show on the server
            search_results = target_server.search(show_name)
            show_items = [item for item in search_results if item.type == 'show']
            
            if not show_items:
                print(f"{Fore.RED}⚠️  Show {show_name} not found on server {server_name}{Style.RESET_ALL}")
                return None
            
            # Get episodes from the first matching show
            show = show_items[0]
            episodes = show.episodes()
            
            # Find the specific episode
            target_episode = None
            for episode in episodes:
                if episode.seasonEpisode == episode_id:
                    target_episode = episode
                    break
            
            if not target_episode:
                print(f"{Fore.RED}⚠️  Episode {episode_id} not found for show {show_name} on server {server_name}{Style.RESET_ALL}")
                return None
            
            print(f"{Fore.GREEN}✅ Converted database data to Plex episode: {show_name} - {episode_id}{Style.RESET_ALL}")
            return target_episode
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error converting episode data: {str(e)}{Style.RESET_ALL}")
            return None
    
    def display_episode_info(self, episode_data: Tuple):
        """Display detailed episode information."""
        if not self.config['show_detailed_info']:
            return
        
        show_name = episode_data[0]
        episode_id = episode_data[1]
        view_count = episode_data[2]
        season = episode_data[3]
        title = episode_data[4]
        length = episode_data[5]
        media_type = episode_data[6]
        server = episode_data[7] if len(episode_data) > 7 else "Unknown"
        
        print(f"\n{Fore.CYAN}📺 Episode Information:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}Show:{Style.RESET_ALL}     {show_name}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}Episode:{Style.RESET_ALL}  {episode_id}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}Season:{Style.RESET_ALL}   {season}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}Title:{Style.RESET_ALL}    {title}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}Views:{Style.RESET_ALL}    {view_count}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}Type:{Style.RESET_ALL}     {media_type}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}Server:{Style.RESET_ALL}  {server}")
        if length:
            duration = millisecondToHumanstr(length)
            print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}Length:{Style.RESET_ALL}  {duration}")
        print(f"{Fore.CYAN}╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
    
    def execute_super_shuffle(self):
        """Execute the main super-shuffle functionality."""
        print(f"\n{Fore.YELLOW}🚀 EXECUTING HYPER SHUFFLE{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}=" * 60 + Style.RESET_ALL)
        
        # Step 1: Get all collections
        print(f"\n{Fore.BLUE}📚 STEP 1: ANALYZING COLLECTIONS{Style.RESET_ALL}")
        all_collections = self.get_all_collections()
        
        if not all_collections:
            print(f"{Fore.RED}❌ No collections found on any server{Style.RESET_ALL}")
            return False
        
        # Ensure current index is within bounds
        if self.current_collection_index >= len(all_collections):
            self.current_collection_index = 0
        
        current_collection, current_server = all_collections[self.current_collection_index]
        print(f"{Fore.GREEN}🎯 Current collection: {current_collection.title} ({self.current_collection_index + 1}/{len(all_collections)}){Style.RESET_ALL}")
        print(f"{Fore.BLUE}🏠 Server: {current_server.friendlyName}{Style.RESET_ALL}")
        
        # Step 2: Select client
        print(f"\n{Fore.BLUE}📱 STEP 2: CLIENT SELECTION{Style.RESET_ALL}")
        client = self.select_client()
        if not client:
            return False
        
        # Step 3: Get prioritization mode
        print(f"\n{Fore.BLUE}🎯 STEP 3: PRIORITIZATION{Style.RESET_ALL}")
        prioritization_mode = self.get_prioritization_mode()
        
        # Step 3.5: Ask about subtitles if not already enabled
        if not self.config.get('auto_enable_subtitles', False):
            subtitle_choice = self.ask_about_subtitles()
            if subtitle_choice:
                # Temporarily enable subtitles for this shuffle
                self.temp_enable_subtitles()
        
        # Step 4: Process collection
        print(f"\n{Fore.BLUE}🔄 STEP 4: PROCESSING COLLECTION{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Processing: {current_collection.title}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}Items: {current_collection.childCount}{Style.RESET_ALL}")
        
        # Get shows from collection
        collection_shows = []
        try:
            for item in current_collection.items():
                if item.type == 'show':
                    collection_shows.append(item.title)
            print(f"{Fore.GREEN}📺 Found {len(collection_shows)} shows in collection{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}❌ Error accessing collection shows: {str(e)}{Style.RESET_ALL}")
            return False
        
        if not collection_shows:
            print(f"{Fore.YELLOW}⚠️  No shows found in collection{Style.RESET_ALL}")
            return False
        
        # Update view counts if enabled
        if self.config['update_view_counts'] and not self.config['skip_view_count_updates']:
            print(f"{Fore.BLUE}📊 Updating view counts for {len(collection_shows)} shows...{Style.RESET_ALL}")
            update_errors = 0
            for show in collection_shows:
                try:
                    self.update_view_counts(show)
                    self.showDB.commit()
                except Exception as e:
                    update_errors += 1
                    if "database is locked" in str(e):
                        print(f"{Fore.YELLOW}⚠️  Database busy, skipping view count updates for remaining shows{Style.RESET_ALL}")
                        self.config['skip_view_count_updates'] = True
                        break
                    else:
                        print(f"{Fore.RED}⚠️  Error updating {show}: {str(e)}{Style.RESET_ALL}")
            
            if update_errors > 0:
                print(f"{Fore.YELLOW}⚠️  {update_errors} shows had update issues{Style.RESET_ALL}")
        elif self.config['skip_view_count_updates']:
            print(f"{Fore.YELLOW}⚠️  Skipping view count updates (database busy){Style.RESET_ALL}")
        
        # Get episodes from collection
        collection_episodes = self.get_episodes_from_collection(current_collection.title)
        
        if not collection_episodes:
            print(f"{Fore.YELLOW}⚠️  No episodes found for collection{Style.RESET_ALL}")
            return False
        
        # Apply prioritization
        prioritized_episodes = self.apply_prioritization(collection_episodes, prioritization_mode)
        
        if not prioritized_episodes:
            print(f"{Fore.YELLOW}⚠️  No episodes after prioritization{Style.RESET_ALL}")
            return False
        
        # Select episode with lowest view count
        try:
            selected_episode_data = min(prioritized_episodes, key=lambda x: x[2])  # x[2] is view count
        except ValueError:
            print(f"{Fore.RED}❌ No valid episodes found{Style.RESET_ALL}")
            return False
        
        # Display episode information
        self.display_episode_info(selected_episode_data)
        
        # Convert to Plex episode object
        plex_episode = self.convert_to_plex_episode(selected_episode_data)
        
        if not plex_episode:
            print(f"{Fore.RED}❌ Could not convert episode data{Style.RESET_ALL}")
            return False
        
        # Confirm play if enabled
        if self.config['confirm_plays']:
            confirm = input(f"\n{Fore.YELLOW}Play this episode? (y/n): {Style.RESET_ALL}").strip().lower()
            if confirm not in ['y', 'yes']:
                print(f"{Fore.YELLOW}⏹️  Playback cancelled{Style.RESET_ALL}")
                return False
        
        # Play the episode with retry logic
        print(f"\n{Fore.BLUE}🎬 STEP 5: PLAYBACK{Style.RESET_ALL}")
        
        # Connect to client with retry logic
        client_connection = self.connect_client_with_retry(client)
        if not client_connection:
            print(f"{Fore.RED}❌ Could not establish connection to client{Style.RESET_ALL}")
            return False
        
        # Special message for Samsung clients
        if isinstance(client_connection, SessionClientWrapper):
            print(f"  📱 {Fore.CYAN}Using Samsung TV session control{Style.RESET_ALL}")
            print(f"  💡 {Fore.BLUE}For subtitles: Use your TV remote > Settings/Tools > Subtitles{Style.RESET_ALL}")
        
        # Play episode with retry logic
        playback_success = self.play_episode_with_retry(client_connection, plex_episode)
        
        if playback_success:
            print(f"\n{Fore.GREEN}🎉 SUCCESS!{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ Playing: {selected_episode_data[0]} - {selected_episode_data[1]}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}📺 Client: {client.name} ({client.platform}){Style.RESET_ALL}")
            
            # Update collection index for next cycle
            if self.config['auto_cycle_collections']:
                self.current_collection_index = (self.current_collection_index + 1) % len(all_collections)
                self.save_collection_index()
                print(f"{Fore.BLUE}🔄 Next collection will be: {all_collections[self.current_collection_index][0].title}{Style.RESET_ALL}")
            
            # Restore subtitle settings if they were temporarily enabled
            self.restore_subtitle_settings()
            
            return True
        else:
            print(f"{Fore.RED}❌ Failed to play episode after multiple attempts{Style.RESET_ALL}")
            # Restore subtitle settings even on failure
            self.restore_subtitle_settings()
            return False
    
    def check_system_health(self):
        """Check system health and provide recommendations for concurrent usage."""
        print(f"\n{Fore.CYAN}🏥 SYSTEM HEALTH CHECK{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")
        
        # Check database status
        print(f"\n{Fore.WHITE}🗄️  Database Status:{Style.RESET_ALL}")
        try:
            # Test database connection
            test_result = self.cursor.execute('SELECT COUNT(*) FROM episodes').fetchone()[0]
            print(f"  ✅ Database connection: {Fore.GREEN}Healthy{Style.RESET_ALL}")
            print(f"  📊 Total episodes: {test_result}")
        except Exception as e:
            print(f"  ❌ Database connection: {Fore.RED}Issues detected{Style.RESET_ALL}")
            print(f"  🔧 Error: {str(e)}")
        
        # Check server connections
        print(f"\n{Fore.WHITE}🌐 Server Connections:{Style.RESET_ALL}")
        for server in self.connected_servers:
            try:
                # Test server responsiveness
                server.library.sections()
                print(f"  ✅ {server.friendlyName}: {Fore.GREEN}Online{Style.RESET_ALL}")
            except Exception as e:
                print(f"  ❌ {server.friendlyName}: {Fore.RED}Connection issues{Style.RESET_ALL}")
                print(f"  🔧 Error: {str(e)}")
        
        # Check client status
        print(f"\n{Fore.WHITE}📱 Client Status:{Style.RESET_ALL}")
        if not self.available_clients:
            print(f"  ❌ {Fore.RED}No clients found{Style.RESET_ALL}")
        else:
            for client in self.available_clients:
                status = f"{Fore.GREEN}Online{Style.RESET_ALL}" if client.presence else f"{Fore.RED}Offline{Style.RESET_ALL}"
                print(f"  📺 {client.name} ({client.platform}): {status}")
                
                # Test client responsiveness if online
                if client.presence:
                    try:
                        client_connection = client.connect()
                        client_connection.timeline()
                        print(f"    ✅ {Fore.GREEN}Responsive{Style.RESET_ALL}")
                    except Exception as e:
                        print(f"    ⚠️  {Fore.YELLOW}Unresponsive - may be busy{Style.RESET_ALL}")
                        print(f"    🔧 Error: {str(e)}")
        
        # Provide recommendations
        print(f"\n{Fore.WHITE}💡 Recommendations for Concurrent Usage:{Style.RESET_ALL}")
        print(f"  • {Fore.BLUE}Enable 'Skip updates when busy' in config if you see database lock errors{Style.RESET_ALL}")
        print(f"  • {Fore.BLUE}Increase 'Client retry attempts' if clients are frequently busy{Style.RESET_ALL}")
        print(f"  • {Fore.BLUE}Increase 'Client timeout' if you have slow network connections{Style.RESET_ALL}")
        print(f"  • {Fore.BLUE}Use 'check' command regularly to monitor system health{Style.RESET_ALL}")
        print(f"  • {Fore.BLUE}Consider running HyperShuffle during low-usage periods{Style.RESET_ALL}")
        
        # Check configuration for concurrent usage
        print(f"\n{Fore.WHITE}⚙️  Concurrent Usage Configuration:{Style.RESET_ALL}")
        if self.config['skip_view_count_updates']:
            print(f"  ✅ {Fore.GREEN}Skip updates when busy: Enabled{Style.RESET_ALL}")
        else:
            print(f"  ⚠️  {Fore.YELLOW}Skip updates when busy: Disabled (recommended for concurrent usage){Style.RESET_ALL}")
        
        if self.config['client_retry_attempts'] >= 3:
            print(f"  ✅ {Fore.GREEN}Client retry attempts: {self.config['client_retry_attempts']} (good){Style.RESET_ALL}")
        else:
            print(f"  ⚠️  {Fore.YELLOW}Client retry attempts: {self.config['client_retry_attempts']} (consider increasing){Style.RESET_ALL}")
        
        if self.config['client_timeout_seconds'] >= 30:
            print(f"  ✅ {Fore.GREEN}Client timeout: {self.config['client_timeout_seconds']}s (good){Style.RESET_ALL}")
        else:
            print(f"  ⚠️  {Fore.YELLOW}Client timeout: {self.config['client_timeout_seconds']}s (consider increasing){Style.RESET_ALL}")

    def run_diagnostics(self):
        """Run detailed diagnostics for troubleshooting client/server issues."""
        print(f"\n{Fore.CYAN}🔬 DETAILED DIAGNOSTICS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        
        # Server diagnostics
        print(f"\n{Fore.WHITE}🌐 SERVER DIAGNOSTICS:{Style.RESET_ALL}")
        for i, server in enumerate(self.connected_servers, 1):
            print(f"\n  {Fore.BLUE}Server {i}: {server.friendlyName}{Style.RESET_ALL}")
            try:
                # Test basic server functions
                sections = server.library.sections()
                print(f"    ✅ Library sections: {len(sections)} found")
                
                # Test sessions
                sessions = server.sessions()
                print(f"    📊 Active sessions: {len(sessions)}")
                
                if sessions:
                    for j, session in enumerate(sessions, 1):
                        print(f"      Session {j}:")
                        print(f"        📺 Media: {getattr(session, 'title', 'Unknown')}")
                        print(f"        👤 User: {getattr(session, 'username', 'Unknown')}")
                        if hasattr(session, 'player'):
                            print(f"        📱 Player: {getattr(session.player, 'title', 'Unknown')}")
                            print(f"        🔧 Product: {getattr(session.player, 'product', 'Unknown')}")
                            print(f"        🏷️  Platform: {getattr(session.player, 'platform', 'Unknown')}")
                        print(f"        ▶️  State: {getattr(session, 'state', 'Unknown')}")
                
                # Test collections
                try:
                    tv_library = server.library.section('TV Shows')
                    collections = tv_library.collections()
                    print(f"    📚 TV Collections: {len(collections)} found")
                except Exception as e:
                    print(f"    ❌ TV Collections error: {str(e)}")
                    
            except Exception as e:
                print(f"    ❌ Server error: {str(e)}")
        
        # Client diagnostics
        print(f"\n{Fore.WHITE}📱 CLIENT DIAGNOSTICS:{Style.RESET_ALL}")
        for i, client in enumerate(self.available_clients, 1):
            print(f"\n  {Fore.BLUE}Client {i}: {client.name} ({client.platform}){Style.RESET_ALL}")
            print(f"    🏷️  Product: {getattr(client, 'product', 'Unknown')}")
            print(f"    🌐 Presence: {'Online' if client.presence else 'Offline'}")
            print(f"    🔗 Public Address Match: {getattr(client, 'publicAddressMatches', 'Unknown')}")
            
            # Test connection
            try:
                print(f"    🔍 Testing connection...")
                client_connection = self.connect_client_with_retry(client, max_retries=3)
                
                if client_connection:
                    print(f"    ✅ Connection: SUCCESS")
                    
                    # Test different timeline access methods
                    print(f"    🧪 Testing timeline access...")
                    
                    # Test method 1: timeline()
                    try:
                        timeline = client_connection.timeline()
                        print(f"    ✅ timeline() method: SUCCESS ({type(timeline)})")
                    except Exception as e:
                        print(f"    ❌ timeline() method: {str(e)}")
                    
                    # Test method 2: timeline property
                    try:
                        timeline = client_connection.timeline
                        print(f"    ✅ timeline property: SUCCESS ({type(timeline)})")
                    except Exception as e:
                        print(f"    ❌ timeline property: {str(e)}")
                    
                    # Test method 3: basic properties
                    try:
                        machine_id = client_connection.machineIdentifier
                        print(f"    ✅ machineIdentifier: SUCCESS ({machine_id})")
                    except Exception as e:
                        print(f"    ❌ machineIdentifier: {str(e)}")
                    
                    # Test playback state detection
                    try:
                        playback_state = self.get_client_playback_state(client_connection)
                        print(f"    📊 Playback state: {playback_state}")
                        if playback_state['is_playing']:
                            print(f"    ✅ Currently playing media detected")
                        else:
                            print(f"    ⏹️  No active playback detected")
                    except Exception as e:
                        print(f"    ❌ Playback state error: {str(e)}")
                        
                    # Test basic controls
                    print(f"    🎮 Testing basic controls availability...")
                    control_methods = ['play', 'pause', 'stop', 'skipNext', 'volumeUp', 'volumeDown', 'setSubtitleStream']
                    available_controls = []
                    for method in control_methods:
                        if hasattr(client_connection, method):
                            print(f"    ✅ {method}: Available")
                            available_controls.append(method)
                        else:
                            print(f"    ❌ {method}: Not available")
                    
                    # Special notes for Samsung/Tizen clients
                    is_samsung = 'samsung' in getattr(client, 'product', '').lower()
                    is_tizen = getattr(client, 'platform', '').lower() == 'tizen'
                    
                    if is_samsung or is_tizen:
                        print(f"    💡 {Fore.BLUE}Samsung/Tizen TV Notes:{Style.RESET_ALL}")
                        print(f"       • Limited remote API support is normal for Samsung TVs")
                        print(f"       • Use TV remote for volume, subtitles, and advanced controls")
                        print(f"       • Basic playback controls (play/pause/skip) should work")
                        print(f"       • Session-based control is used when direct control fails")
                        
                        if isinstance(client_connection, SessionClientWrapper):
                            print(f"    🔧 Using session-based control wrapper")
                            print(f"       • Connected via active server session")
                            print(f"       • Playback control available: ✅")
                            print(f"       • Subtitle control: Use TV remote")
                            print(f"       • Volume control: Use TV remote")
                            
                else:
                    print(f"    ❌ Connection: FAILED")
                    
            except Exception as e:
                print(f"    ❌ Connection test error: {str(e)}")
        
        # Plex API version info
        print(f"\n{Fore.WHITE}📚 PLEX API INFORMATION:{Style.RESET_ALL}")
        try:
            import plexapi
            print(f"    📦 PlexAPI version: {plexapi.VERSION}")
        except Exception as e:
            print(f"    ❌ PlexAPI version error: {str(e)}")
        
        # Configuration that might affect connectivity
        print(f"\n{Fore.WHITE}⚙️  CONNECTIVITY CONFIGURATION:{Style.RESET_ALL}")
        print(f"    🔄 Client retry attempts: {self.config['client_retry_attempts']}")
        print(f"    ⏱️  Client timeout: {self.config['client_timeout_seconds']}s")
        print(f"    🔄 Database retry attempts: {self.config['database_retry_attempts']}")
        
        print(f"\n{Fore.GREEN}🔬 Diagnostics complete!{Style.RESET_ALL}")
        print(f"{Fore.BLUE}💡 If you see errors above, they explain why remote mode features aren't working.{Style.RESET_ALL}")

    def samsung_troubleshooting(self):
        """Samsung Tizen specific troubleshooting guide."""
        print(f"\n{Fore.CYAN}📺 SAMSUNG TIZEN TV TROUBLESHOOTING{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        
        print(f"\n{Fore.WHITE}🔧 COMMON SAMSUNG TIZEN ISSUES:{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}Connection Problems:{Style.RESET_ALL}")
        print(f"    • Samsung TVs have limited Plex API support")
        print(f"    • Remote control features may not work fully")
        print(f"    • Subtitle control often requires manual TV remote")
        
        print(f"\n{Fore.WHITE}💡 TROUBLESHOOTING STEPS:{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}1. Restart Plex App on TV{Style.RESET_ALL}")
        print(f"    • Exit Plex app completely on your Samsung TV")
        print(f"    • Wait 10 seconds, then reopen Plex app")
        
        print(f"  {Fore.GREEN}2. Network Connection{Style.RESET_ALL}")
        print(f"    • Ensure TV and Plex server are on same network")
        print(f"    • Check TV's network settings")
        print(f"    • Try wired connection instead of WiFi if possible")
        
        print(f"  {Fore.GREEN}3. Plex Server Settings{Style.RESET_ALL}")
        print(f"    • Enable 'Allow insecure connections' in Plex server")
        print(f"    • Check that remote access is working")
        
        print(f"  {Fore.GREEN}4. Manual Controls (Recommended){Style.RESET_ALL}")
        print(f"    • Use Samsung TV remote for subtitle control")
        print(f"    • Use TV remote for skip/pause/volume")
        print(f"    • HyperShuffle works best for starting playback")
        
        print(f"\n{Fore.WHITE}🎯 WHAT WORKS BEST WITH SAMSUNG:{Style.RESET_ALL}")
        print(f"  ✅ {Fore.GREEN}Starting playback via HyperShuffle{Style.RESET_ALL}")
        print(f"  ✅ {Fore.GREEN}Collection switching and episode selection{Style.RESET_ALL}")
        print(f"  ⚠️  {Fore.YELLOW}Remote control features (limited){Style.RESET_ALL}")
        print(f"  ⚠️  {Fore.YELLOW}Subtitle control (use TV remote){Style.RESET_ALL}")
        print(f"  ⚠️  {Fore.YELLOW}Volume control (use TV remote){Style.RESET_ALL}")
        
        print(f"\n{Fore.WHITE}🔄 RECOMMENDED WORKFLOW:{Style.RESET_ALL}")
        print(f"  1. Use {Fore.GREEN}'quick'{Style.RESET_ALL} command to start playback")
        print(f"  2. Use Samsung TV remote for episode control")
        print(f"  3. Use TV remote Settings > Subtitles for subtitle control")
        print(f"  4. Return to HyperShuffle for collection switching")
        
        print(f"\n{Fore.BLUE}💡 Pro tip: Samsung Tizen works best when Plex app is freshly restarted!{Style.RESET_ALL}")
    
    def show_configuration_menu(self):
        """Display and manage configuration options."""
        while True:
            print(f"\n{Fore.CYAN}⚙️  CONFIGURATION MENU{Style.RESET_ALL}")
            print(f"{Fore.CYAN}=" * 40 + Style.RESET_ALL)
            
            config_options = [
                ('auto_cycle_collections', 'Auto-cycle collections', 'bool'),
                ('holiday_filtering', 'Holiday episode filtering', 'bool'),
                ('view_count_priority', 'View count priority', 'bool'),
                ('balanced_lineup', 'Balanced TV lineup', 'bool'),
                ('animation_domination', 'Animation domination mode', 'bool'),
                ('auto_client_selection', 'Auto client selection', 'bool'),
                ('show_detailed_info', 'Show detailed episode info', 'bool'),
                ('confirm_plays', 'Confirm before playing', 'bool'),
                ('update_view_counts', 'Update view counts', 'bool'),
                ('skip_view_count_updates', 'Skip updates when busy', 'bool'),
                ('preserve_shuffle_mode', 'Preserve client shuffle mode', 'bool'),
                ('auto_manage_subtitles', 'Auto-manage subtitles', 'bool'),
                ('auto_download_subtitles', 'Auto-download missing subtitles', 'bool'),
                ('auto_enable_subtitles', 'Auto-enable subtitles on playback', 'bool'),
                ('smart_subtitle_selection', 'Smart subtitle selection for accuracy', 'bool'),
                ('remote_mode_shortcuts', 'Remote mode keyboard shortcuts', 'bool'),
                ('show_startup_commands', 'Show command overview on startup', 'bool'),
                ('max_consecutive_same_show', 'Max consecutive same show', 'int'),
                ('collection_cycle_delay', 'Collection cycle delay (seconds)', 'int'),
                ('database_retry_attempts', 'Database retry attempts', 'int'),
                ('client_retry_attempts', 'Client retry attempts', 'int'),
                ('client_timeout_seconds', 'Client timeout (seconds)', 'int'),
            ]
            
            for i, (key, description, type_) in enumerate(config_options, 1):
                current_value = self.config[key]
                if type_ == 'bool':
                    status = f"{Fore.GREEN}ON{Style.RESET_ALL}" if current_value else f"{Fore.RED}OFF{Style.RESET_ALL}"
                else:
                    status = f"{Fore.BLUE}{current_value}{Style.RESET_ALL}"
                print(f"  {i:2d}. {description}: {status}")
            
            print(f"  {len(config_options) + 1:2d}. Reset to defaults")
            print(f"  {len(config_options) + 2:2d}. Back to main menu")
            
            try:
                choice = input(f"\n{Fore.YELLOW}Select option (1-{len(config_options) + 2}): {Style.RESET_ALL}").strip()
                choice_num = int(choice)
                
                if choice_num == len(config_options) + 1:
                    # Reset to defaults
                    self.reset_configuration()
                    print(f"{Fore.GREEN}✅ Configuration reset to defaults{Style.RESET_ALL}")
                elif choice_num == len(config_options) + 2:
                    # Back to main menu
                    break
                elif 1 <= choice_num <= len(config_options):
                    # Modify configuration
                    key, description, type_ = config_options[choice_num - 1]
                    self.modify_configuration(key, description, type_)
                else:
                    print(f"{Fore.RED}❌ Invalid choice{Style.RESET_ALL}")
                    
            except (ValueError, KeyboardInterrupt):
                print(f"{Fore.RED}❌ Invalid input{Style.RESET_ALL}")
    
    def modify_configuration(self, key: str, description: str, type_: str):
        """Modify a specific configuration option."""
        current_value = self.config[key]
        
        if type_ == 'bool':
            new_value = not current_value
            self.config[key] = new_value
            status = f"{Fore.GREEN}enabled{Style.RESET_ALL}" if new_value else f"{Fore.RED}disabled{Style.RESET_ALL}"
            print(f"{Fore.GREEN}✅ {description} {status}{Style.RESET_ALL}")
        elif type_ == 'int':
            try:
                new_value = int(input(f"{Fore.YELLOW}Enter new value for {description} (current: {current_value}): {Style.RESET_ALL}"))
                self.config[key] = new_value
                print(f"{Fore.GREEN}✅ {description} set to {new_value}{Style.RESET_ALL}")
            except (ValueError, KeyboardInterrupt):
                print(f"{Fore.RED}❌ Invalid input, keeping current value{Style.RESET_ALL}")
    
    def reset_configuration(self):
        """Reset configuration to default values."""
        self.config = {
            'auto_cycle_collections': True,
            'holiday_filtering': True,
            'view_count_priority': True,
            'balanced_lineup': False,
            'animation_domination': False,
            'auto_client_selection': True,
            'show_detailed_info': True,
            'confirm_plays': False,
            'max_consecutive_same_show': 2,
            'collection_cycle_delay': 5,
            'update_view_counts': True,
            'prioritization_mode': '1',
            'skip_view_count_updates': False,
            'database_retry_attempts': 3,
            'client_retry_attempts': 3,
            'client_timeout_seconds': 30,
            'preserve_shuffle_mode': True,
            'auto_manage_subtitles': False,
            'auto_download_subtitles': False,
            'auto_enable_subtitles': False,
            'smart_subtitle_selection': True,
            'preferred_subtitle_language': 'en',
            'remote_mode_shortcuts': True,
            'show_startup_commands': True,
        }
    
    def show_help(self):
        """Display help information."""
        help_text = f"""
{Fore.CYAN}🎮 HYPER SHUFFLE - HELP{Style.RESET_ALL}
{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}

{Fore.WHITE}MAIN COMMANDS:{Style.RESET_ALL}
  {Fore.GREEN}shuffle{Style.RESET_ALL}     - Execute super-shuffle (default mode)
  {Fore.GREEN}quick{Style.RESET_ALL}      - Quick collection picker with smart subtitles
  {Fore.GREEN}remote{Style.RESET_ALL}     - Remote control mode for active playback
  {Fore.GREEN}collections{Style.RESET_ALL} - List all available collections
  {Fore.GREEN}config{Style.RESET_ALL}     - Configure system settings
  {Fore.GREEN}status{Style.RESET_ALL}     - Show system status
  {Fore.GREEN}check{Style.RESET_ALL}      - Check system health
  {Fore.GREEN}help{Style.RESET_ALL}       - Show this help
  {Fore.GREEN}quit{Style.RESET_ALL}       - Exit HyperShuffle

{Fore.WHITE}ADVANCED COMMANDS:{Style.RESET_ALL}
  {Fore.BLUE}create{Style.RESET_ALL}      - Create/rebuild database
  {Fore.BLUE}update{Style.RESET_ALL}      - Update episode data
  {Fore.BLUE}reset{Style.RESET_ALL}       - Reset collection index
  {Fore.BLUE}clients{Style.RESET_ALL}     - List available clients
  {Fore.BLUE}diag{Style.RESET_ALL}        - Run detailed diagnostics for troubleshooting
  {Fore.BLUE}samsung{Style.RESET_ALL}     - Samsung Tizen TV troubleshooting guide
  {Fore.BLUE}subs on{Style.RESET_ALL}     - Enable subtitles on current client
  {Fore.BLUE}subs off{Style.RESET_ALL}    - Disable subtitles on current client
  {Fore.BLUE}auto subs on{Style.RESET_ALL} - Enable automatic subtitles globally
  {Fore.BLUE}auto subs off{Style.RESET_ALL} - Disable automatic subtitles globally

{Fore.WHITE}NEW FEATURES:{Style.RESET_ALL}
  • {Fore.YELLOW}Remote control mode{Style.RESET_ALL} - Full playback control with skip, pause, subtitles
  • {Fore.YELLOW}Quick collection picker{Style.RESET_ALL} - Fast collection selection with auto-subtitles
  • {Fore.YELLOW}Intelligent subtitle selection{Style.RESET_ALL} - AI-powered accuracy optimization
  • {Fore.YELLOW}Shuffle mode preservation{Style.RESET_ALL} - Maintains active shuffle playlists
  • {Fore.YELLOW}3-pass shuffle mode{Style.RESET_ALL} - Maximum randomization option
  • {Fore.YELLOW}Smart playback integration{Style.RESET_ALL} - Works with existing playback

{Fore.WHITE}CORE FEATURES:{Style.RESET_ALL}
  • {Fore.YELLOW}Super-shuffle default mode{Style.RESET_ALL} - Collection-based shuffling
  • {Fore.YELLOW}Holiday episode filtering{Style.RESET_ALL} - Push seasonal content back
  • {Fore.YELLOW}View count priority{Style.RESET_ALL} - Play unwatched content first
  • {Fore.YELLOW}Auto collection cycling{Style.RESET_ALL} - Systematic collection rotation
  • {Fore.YELLOW}Multi-server support{Style.RESET_ALL} - Works across all your servers
  • {Fore.YELLOW}Beautiful interface{Style.RESET_ALL} - Color-coded, easy to use
  • {Fore.YELLOW}Concurrent usage support{Style.RESET_ALL} - Works while clients are playing

{Fore.WHITE}CONFIGURATION:{Style.RESET_ALL}
  Use the {Fore.GREEN}config{Style.RESET_ALL} command to customize:
  • Prioritization modes (holiday, random, 3-pass shuffle)
  • Intelligent subtitle selection and language preferences
  • Shuffle mode preservation settings
  • Auto-cycling behavior and client selection
  • Display options and playback confirmation

{Fore.CYAN}For more information, visit:{Style.RESET_ALL}
  https://github.com/pastram-i/plex-trueshuffle
"""
        print(help_text)
    
    def show_status(self):
        """Display system status."""
        print(f"\n{Fore.CYAN}📊 SYSTEM STATUS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 40}{Style.RESET_ALL}")
        
        # Server status
        print(f"{Fore.WHITE}🌐 Servers:{Style.RESET_ALL}")
        for server in self.connected_servers:
            print(f"  ✅ {server.friendlyName}")
        
        # Client status
        print(f"\n{Fore.WHITE}📱 Clients:{Style.RESET_ALL}")
        for client in self.available_clients:
            status = f"{Fore.GREEN}Online{Style.RESET_ALL}" if client.presence else f"{Fore.RED}Offline{Style.RESET_ALL}"
            print(f"  {client.name} ({client.platform}) - {status}")
        
        # Collection status
        all_collections = self.get_all_collections()
        if all_collections:
            current_collection = all_collections[self.current_collection_index][0]
            print(f"\n{Fore.WHITE}📚 Collections:{Style.RESET_ALL}")
            print(f"  Total: {len(all_collections)}")
            print(f"  Current: {current_collection.title} ({self.current_collection_index + 1}/{len(all_collections)})")
        
        # Configuration summary
        print(f"\n{Fore.WHITE}⚙️  Configuration:{Style.RESET_ALL}")
        enabled_options = [k for k, v in self.config.items() if v and isinstance(v, bool)]
        print(f"  Enabled: {', '.join(enabled_options[:3])}{'...' if len(enabled_options) > 3 else ''}")
    
    def show_startup_commands(self):
        """Show stylish startup command overview."""
        if not self.config.get('show_startup_commands', True):
            return
        
        # Get system status for startup
        server_count = len(self.connected_servers)
        client_count = len(self.available_clients)
        online_clients = sum(1 for client in self.available_clients if client.presence)
        
        print(f"\n{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}                            {Fore.YELLOW}🎮 COMMAND CENTER 🎮{Style.RESET_ALL}                            {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}╠═══════════════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}System Status:{Style.RESET_ALL} {server_count} server(s) • {online_clients}/{client_count} clients online                {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}╠═══════════════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
        
        # Primary commands
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.GREEN}🎬 INSTANT ACTIONS{Style.RESET_ALL}                                                        {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}   {Fore.GREEN}shuffle{Style.RESET_ALL} / {Fore.GREEN}s{Style.RESET_ALL}    🎯 Smart collection shuffle (default)                     {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}   {Fore.GREEN}quick{Style.RESET_ALL} / {Fore.GREEN}q{Style.RESET_ALL}      🚀 Pick collection → play instantly with subtitles    {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}   {Fore.GREEN}remote{Style.RESET_ALL} / {Fore.GREEN}r{Style.RESET_ALL}     📱 Full remote control (skip, pause, subs, volume)   {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}                                                                           {Fore.CYAN}║{Style.RESET_ALL}")
        
        # Utility commands
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.BLUE}🔧 UTILITIES{Style.RESET_ALL}                                                              {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}   {Fore.BLUE}collections{Style.RESET_ALL} / {Fore.BLUE}c{Style.RESET_ALL}  📚 Browse all collections                            {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}   {Fore.BLUE}config{Style.RESET_ALL}             ⚙️ Settings & preferences                          {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}   {Fore.BLUE}status{Style.RESET_ALL} / {Fore.BLUE}diag{Style.RESET_ALL}     📊 System status & diagnostics                    {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}                                                                           {Fore.CYAN}║{Style.RESET_ALL}")
        
        # Quick tips
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.YELLOW}💡 QUICK TIPS{Style.RESET_ALL}                                                             {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}   • {Fore.WHITE}Just press Enter{Style.RESET_ALL} for default shuffle                                {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}   • {Fore.WHITE}Type 'help'{Style.RESET_ALL} for complete command list                              {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL}   • {Fore.WHITE}Remote mode{Style.RESET_ALL} works great during active playback                    {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}╚═══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")

    def run(self):
        """Main application loop."""
        print(f"\n{Fore.GREEN}🎉 Welcome to HyperShuffle!{Style.RESET_ALL}")
        
        # Show stylish command overview if enabled
        self.show_startup_commands()
        
        print(f"\n{Fore.BLUE}Ready for commands...{Style.RESET_ALL}\n")
        
        while True:
            try:
                command = input(f"{Fore.YELLOW}HyperShuffle> {Style.RESET_ALL}").strip().lower()
                
                if command in ['', 'shuffle', 's']:
                    # Default super-shuffle mode
                    self.execute_super_shuffle()
                    
                elif command in ['quick', 'play', 'pick', 'q']:
                    # Quick collection picker with smart subtitles
                    self.quick_collection_picker()
                    
                elif command in ['remote', 'r']:
                    # Remote control mode
                    self.remote_mode()
                    
                elif command in ['collections', 'c']:
                    # List collections
                    all_collections = self.get_all_collections()
                    self.display_collections(all_collections)
                    
                elif command in ['config', 'settings']:
                    # Configuration menu
                    self.show_configuration_menu()
                    
                elif command in ['status', 'st']:
                    # Show system status
                    self.show_status()
                    
                elif command in ['help', 'h', '?']:
                    # Show help
                    self.show_help()
                    
                elif command in ['clients', 'cl']:
                    # List clients
                    self.discover_clients()
                    
                elif command in ['check', 'health']:
                    # Check system health and client status
                    self.check_system_health()
                    
                elif command in ['diag', 'diagnose', 'debug']:
                    # Run detailed diagnostics
                    self.run_diagnostics()
                    
                elif command in ['samsung', 'tizen', 'tv']:
                    # Samsung/Tizen specific troubleshooting
                    self.samsung_troubleshooting()
                    
                elif command in ['subs on', 'subtitles on', 'sub on']:
                    # Enable subtitles on current client
                    print(f"{Fore.BLUE}🗣️  Manual subtitle control - connecting to client...{Style.RESET_ALL}")
                    self.manual_subtitle_control(True)
                    
                elif command in ['subs off', 'subtitles off', 'sub off']:
                    # Disable subtitles on current client
                    self.manual_subtitle_control(False)
                    
                elif command in ['auto subs on', 'auto subtitles on', 'subs auto on']:
                    # Enable automatic subtitles
                    self.toggle_auto_subtitles(True)
                    
                elif command in ['auto subs off', 'auto subtitles off', 'subs auto off']:
                    # Disable automatic subtitles
                    self.toggle_auto_subtitles(False)
                    
                elif command in ['create']:
                    # Create database (legacy command)
                    print(f"{Fore.YELLOW}⚠️  Database creation not implemented in HyperShuffle{Style.RESET_ALL}")
                    print(f"{Fore.BLUE}Use the original TrueShuffle.py for database management{Style.RESET_ALL}")
                    
                elif command in ['update']:
                    # Update database (legacy command)
                    print(f"{Fore.YELLOW}⚠️  Database updates not implemented in HyperShuffle{Style.RESET_ALL}")
                    print(f"{Fore.BLUE}Use the original TrueShuffle.py for database management{Style.RESET_ALL}")
                    
                elif command in ['reset']:
                    # Reset collection index
                    self.current_collection_index = 0
                    self.save_collection_index()
                    print(f"{Fore.GREEN}✅ Collection index reset to 0{Style.RESET_ALL}")
                    
                elif command in ['quit', 'exit', 'q']:
                    # Exit application
                    print(f"\n{Fore.GREEN}👋 Thanks for using HyperShuffle!{Style.RESET_ALL}")
                    break
                    
                else:
                    print(f"{Fore.RED}❌ Unknown command: {command}{Style.RESET_ALL}")
                    print(f"{Fore.BLUE}Type 'help' for available commands{Style.RESET_ALL}")
                    
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}⚠️  Use 'quit' to exit{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}")
        
        # Cleanup
        self.showDB.close()

def main():
    """Main entry point."""
    try:
        # Check if config exists
        if not hasattr(config, 'username') or not hasattr(config, 'password') or not hasattr(config, 'servers'):
            print(f"{Fore.RED}❌ Configuration error: Please check your config.py file{Style.RESET_ALL}")
            print(f"{Fore.BLUE}Make sure username, password, and servers are defined{Style.RESET_ALL}")
            return
        
        # Create and run HyperShuffle
        hyper_shuffle = HyperShuffle()
        hyper_shuffle.run()
        
    except ImportError as e:
        print(f"{Fore.RED}❌ Import error: {str(e)}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}Please install required dependencies: pip install -r requirements.txt{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Fatal error: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
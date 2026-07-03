from plexapi.myplex import MyPlexAccount
from plexapi.utils import millisecondToHumanstr
from plexapi.library import Library, Hub
import plexapi.video, plexapi.audio
import config, sqlite3
from datetime import datetime

showDB = sqlite3.connect('myShows.db')
c = showDB.cursor()
myAccount = MyPlexAccount(config.username,config.password)

def CallDB (query, args=()):
    return c.execute(query, args).fetchall()
def ServerConnect(server):
    print(f'Connecting to {server}...')
    try:
        serv = myAccount.resource(server).connect()
    except:
        print(f"Could not connect to server: {server} :(")
        serv = ':('
    return serv
def SearchServer(server, search):
    return server.search(search) if server != ':(' else []
def ShowsPerServer(server):
    if server == ':(':
        return []
    print(f'Getting shows from playlist(s) and collection(s) on {server.friendlyName}...')
    ### Needs to be updated for new media types
    MyShows = [[ep.grandparentTitle if ep.type == 'episode' else ep.originalTitle for ep in pla] for pla in server.playlists()]
    
    # Also get shows from collections
    collection_count = 0
    try:
        # Try different methods to access collections
        collections = []
        try:
            # Try accessing through library first (this works based on diagnostic)
            library = server.library.section('TV Shows')
            collections = library.collections()
        except:
            try:
                collections = server.collections()
            except:
                try:
                    # Try direct search for collection titles
                    collection_titles = ['Adult Swim Daily', 'Adult Swim Ultra', 'Swim Mix']
                    for title in collection_titles:
                        search_results = server.search(title)
                        if search_results:
                            collections.extend(search_results)
                except:
                    pass
        
        if collections:
            print(f'  ✓ Found {len(collections)} collections on {server.friendlyName}')
            for collection in collections:
                try:
                    if hasattr(collection, 'items'):
                        collection_count += 1
                        print(f'    - Collection: {collection.title} ({collection.childCount} items)')
                        for item in collection.items():
                            if item.type == 'show':
                                MyShows.append([item.title])
                            elif item.type == 'movie':
                                MyShows.append([item.title])
                    elif hasattr(collection, 'title'):
                        # Handle individual shows that might be returned
                        if collection.type == 'show':
                            MyShows.append([collection.title])
                except Exception as e:
                    print(f'    ⚠️  Error processing collection {collection.title if hasattr(collection, "title") else "unknown"}: {str(e)}')
                    continue
            print(f'  ✓ Successfully processed {collection_count} collections')
        else:
            # Fallback: try to get shows directly from TV Shows library
            print(f'  🔄 Collections not accessible, trying direct library access...')
            try:
                library = server.library.section('TV Shows')
                shows = library.all()
                for show in shows:
                    MyShows.append([show.title])
                print(f'  ✓ Found {len(shows)} shows directly from TV Shows library')
            except Exception as e:
                print(f'  ⚠️  Direct library access also failed: {str(e)}')
                
    except Exception as e:
        print(f"  ✗ Could not access collections on {server.friendlyName}: {str(e)}")
        # Try fallback method
        try:
            print(f'  🔄 Trying fallback method...')
            search_results = server.search('Adult Swim')
            if search_results:
                for item in search_results:
                    if item.type == 'show':
                        MyShows.append([item.title])
                print(f'  ✓ Found {len([x for x in search_results if x.type == "show"])} shows via search fallback')
        except Exception as e2:
            print(f'  ✗ Fallback method also failed: {str(e2)}')
    
    total_shows = len(list({item for sublist in MyShows for item in sublist}))
    print(f'  ✓ Total unique shows found: {total_shows}')
    return list({item for sublist in MyShows for item in sublist})
def ShowsIFollow(servershows):
    for show in servershows:
        CallDB('''INSERT INTO shows (Show) SELECT ? WHERE NOT EXISTS(SELECT 1 FROM shows WHERE Show = ?)''',(show,show))
def Welcome():
    print('Type "help" for a list of commands.')
def PlayInfo(play):
    ### Needs to be updated for new media types
    if play.type == 'episode':
        print(
    '''
----------------------------
Now playing:            {} {}
Season:                 {}
Episode:                {}
Length (HH:MM:SS:MMMM): {}
----------------------------
    '''.format(play.grandparentTitle,play.seasonEpisode, play.parentTitle,play.title,millisecondToHumanstr(play.duration))
    )
        # Note: Audio and subtitle stream selection is handled automatically by Plex
        # The streams will be selected based on your Plex client settings
        print(f'🎵 Audio streams available: {len(play.audioStreams()) if play.audioStreams() else 0}')
        print(f'📝 Subtitle streams available: {len(play.subtitleStreams()) if play.subtitleStreams() else 0}')
    elif play.type == 'track':
        print(
    '''
----------------------------
Now playing:            {}
Album/Book:             {}
Track/Chapter:          {}
Length (HH:MM:SS:MMMM): {}
----------------------------
    '''.format(play.originalTitle,play.parentTitle,play.title,millisecondToHumanstr(play.duration))
    )
    else:
        print('Media type currently not supported.')
def ViewCountUpdate(show):
    servers_checked = 0
    episodes_updated = 0
    
    for serv in conservs:
        if serv != ':(':
            servers_checked += 1
            i = CallDB('''SELECT COUNT(ID) FROM episodes''')[0][0]
            print(f'  🔍 Checking server: {serv.friendlyName}')
            
            ### Needs to be updated for new media types
            alleps = [item.episodes() for item in SearchServer(serv, show) if item.type == 'show']+[item.tracks() for item in SearchServer(serv, show) if item.type == 'artist']
            if alleps:
                print(f'    ✓ Server {serv.friendlyName} is receptive - found {len(alleps[0])} episodes')
                alreadyin = CallDB('''SELECT Show, Episode, Server FROM episodes WHERE Show = ? AND Server = ?''',(show,serv.friendlyName))
                for ep in alleps[0]:
                    ### Needs to be updated for new media types
                    if ep.type=='episode':
                        if (ep.grandparentTitle, ep.seasonEpisode, serv.friendlyName) not in alreadyin:
                            CallDB('''INSERT INTO episodes (ID, Type, Show, Season, Episode, Title, Server, ViewCount, Length) VALUES (?,?,?,?,?,?,?,?,?)''',(i,ep.type,ep.grandparentTitle,ep.parentTitle,ep.seasonEpisode,ep.title,serv.friendlyName,ep.viewCount,ep.duration))
                            i+=1
                            episodes_updated += 1
                        else:
                            CallDB('''UPDATE episodes SET ViewCount = ? WHERE Show = ? AND Server = ? AND Episode = ?''',(ep.viewCount, show,serv.friendlyName,ep.seasonEpisode))
                            episodes_updated += 1
                    elif ep.type=='track':
                        if (ep.originalTitle, ep.index, serv.friendlyName) not in alreadyin:
                            CallDB('''INSERT INTO episodes (ID, Type, Show, Season, Episode, Title, Server, ViewCount, Length) VALUES (?,?,?,?,?,?,?,?,?)''',(i,ep.type,ep.originalTitle,ep.parentTitle,ep.index,ep.title,serv.friendlyName,ep.viewCount,ep.duration))
                            i+=1
                            episodes_updated += 1
                        else:
                            CallDB('''UPDATE episodes SET ViewCount = ? WHERE Show = ? AND Server = ? AND Episode = ?''',(ep.viewCount, show,serv.friendlyName,ep.index))
                            episodes_updated += 1
            else:
                print(f'    ⚠️  Server {serv.friendlyName} - no episodes found for {show}')
    
    print(f'  📈 View count update complete: {servers_checked} servers checked, {episodes_updated} episodes updated')
def CommandsInfo():
    print('''
    ****************************
Type "help" for this list of commands
Type "create" to build DB
    - Required to run first time
    - If one exists it will overwrite it; use to reset as needed
Type "update" to refresh DB
    - Updates the DB with all episodes from all servers for your shows in playlists
    - Can be used to find new or missing episodes as well
    - May take a while to complete
Type "collections" to list available collections
    - Shows all collections on your Plex servers
    - Useful for seeing what's available to shuffle
Type "clients" to list available Plex clients
    - Shows all Plex clients and their online status
    - Useful for troubleshooting client connections
Type "shuffle-collections" to shuffle from all collections
    - Randomly picks from all available collections
    - Ensures maximum variety between shows
Type "debug-episodes" to check episode data in database
    - Shows episode information for debugging
Type "filter-stats" to see episode filtering statistics
    - Shows how episodes are being filtered and prioritized
Type "shuffle-collections" to shuffle from collections
    - Randomly picks from all available collections
    - Ensures maximum variety between shows
Type "collection-holiday-wash" to clean all holiday episodes
    - Scans all collections and TV shows for holiday keywords
    - Pushes all holiday episodes to the back efficiently
Type "tv-lineup" to balance show shuffles
    - Ensures no more than 2 episodes of the same show play back-to-back
    - Creates balanced and diverse viewing lineups
Type "animation-domination" for Adult Swim Ultra lineup
    - Creates specific lineup: 4 Simpsons, 4 Family Guy, 4 American Dad, 4 South Park, 2 Cleveland Show, 4 Mixed
Type "super-shuffle" for refined collection-based shuffling
    - Works with collections one at a time, starting with current collection
    - Multiple operation modes: current, next, all, or specific collection
    - Client selection with various prioritization modes
Type "collection-status" to see current collection tracking
    - Shows which collection is currently active
    - Displays all available collections and their status
Type "reset-collections" to reset collection index
    - Resets collection tracking to start from the first collection
    - Useful for starting fresh or troubleshooting
Type "upcoming" to check next 20 episodes
    - Shows next 20 episodes from the collection currently playing
    - Sorted by view count (lowest first) for shuffle prediction
Type "system-check" for comprehensive validation
    - Validates database integrity, server connections, and performance
    - Tests massive file handling capabilities and memory usage
    - Ensures all video files are being read properly
Type "detect-orphans" to find orphaned episodes
    - Identifies episodes without corresponding shows in database
    - Provides detailed analysis of orphaned episodes by show
    - Safe detection only - no changes made to database
Type "fix-orphans" to correct orphaned episodes
    - Automatically finds and adds missing shows to database
    - Safely removes episodes that cannot be corrected
    - Includes backup and export options for safety
Type "db-integrity" for comprehensive database repair
    - Checks for orphaned episodes, duplicates, and invalid data
    - Offers automatic repair of all database issues
    - Ensures database consistency and performance
Type "quit" to exit
    ****************************\n''')
def ProvideMilk():
    print('''
This make take a little while....

    Take a milk while you wait
            _____
           j_____j
          /_____/_\\
          |_(~)_| |
          | )"( | |
          |(@_@)| |  
          |_____|,'
''')

def ListCollections():
    print('Available collections:')
    for serv in conservs:
        if serv != ':(':
            print(f'\nOn {serv.friendlyName}:')
            try:
                # Try multiple methods to access collections
                collections = []
                method_used = "direct"
                
                try:
                    # Try library method first (this works based on diagnostic)
                    library = serv.library.section('TV Shows')
                    collections = library.collections()
                    method_used = "library"
                except Exception as e1:
                    print(f'  ⚠️  Library collection access failed: {str(e1)}')
                    try:
                        collections = serv.collections()
                        method_used = "direct"
                    except Exception as e2:
                        print(f'  ⚠️  Direct collection access failed: {str(e2)}')
                        try:
                            # Try searching for specific collection names
                            collection_titles = ['Adult Swim Daily', 'Adult Swim Ultra', 'Swim Mix']
                            for title in collection_titles:
                                search_results = serv.search(title)
                                if search_results:
                                    collections.extend(search_results)
                            method_used = "search"
                        except Exception as e3:
                            print(f'  ⚠️  Search method failed: {str(e3)}')
                
                if collections:
                    print(f'  ✓ Found {len(collections)} collections using {method_used} method:')
                    for collection in collections:
                        try:
                            if hasattr(collection, 'title'):
                                if hasattr(collection, 'childCount'):
                                    print(f'    - {collection.title} ({collection.childCount} items)')
                                else:
                                    print(f'    - {collection.title} (type: {collection.type})')
                        except Exception as e:
                            print(f'    - Error displaying collection: {str(e)}')
                else:
                    print(f'  ❌ No collections found using any method')
                    
            except Exception as e:
                print(f'  ❌ Could not access collections on {serv.friendlyName}: {str(e)}')

def ListClients():
    print('Available Plex clients:')
    all_clients = [x for x in myAccount.resources() if "player" in x.provides]
    if all_clients:
        for i, cl in enumerate(all_clients):
            status = "Online" if cl.presence else "Offline"
            print(f'  {i+1}. {cl.name} ({cl.platform}) - {status}')
        print('\nTo connect to a client, make sure it\'s running and online.')
    else:
        print('No Plex clients found.')

def DebugEpisodes():
    print('🔍 DEBUG: Episode Data in Database')
    print('=' * 50)
    
    try:
        # Get all shows
        shows = c.execute('''SELECT DISTINCT Show FROM shows ORDER BY Show''').fetchall()
        print(f'📺 Found {len(shows)} shows in database')
        
        for show in shows[:3]:  # Show first 3 shows
            show_name = show[0]
            print(f'\n🎬 Show: {show_name}')
            
            # Get episodes for this show
            episodes = c.execute('''SELECT Episode, Title, ViewCount, Server FROM episodes WHERE Show = ? ORDER BY Episode LIMIT 10''', (show_name,)).fetchall()
            print(f'  📋 Found {len(episodes)} episodes:')
            
            for ep in episodes:
                print(f'    - {ep[0]} | {ep[1]} | Views: {ep[2]} | Server: {ep[3]}')
                
    except Exception as e:
        print(f'❌ Error accessing database: {str(e)}')

def FilterEpisodes(episodes, show_name):
    """
    Filter episodes based on special rules:
    - Push holiday episodes to the back for ALL shows (keyword-based)
    - Push early Simpsons seasons 0, 1, 2 to the back entirely
    """
    if not episodes:
        return episodes
    
    print(f'🎭 Applying episode filters for {show_name}...')
    
    # Separate episodes into different categories
    regular_episodes = []
    holiday_episodes = []
    early_simpsons = []
    
    # Specific holiday keywords for filtering
    holiday_keywords = [
        'christmas', 'x-mas', 'xmas', 'holy night', 'horror', 'treehouse', 'thanksgiving', 'halloween'
    ]
    
    for episode in episodes:
        episode_id = episode[1]  # Episode identifier (e.g., "s01e01")
        episode_title = episode[4] if len(episode) > 4 else ""  # Episode title
        
        # Check if it's early Simpsons (seasons 0, 1, 2) - push to back entirely
        if show_name.lower() == 'the simpsons':
            try:
                season_num = int(episode_id[1:3])  # Extract season number from "s01e01"
                if season_num <= 2:
                    early_simpsons.append(episode)
                    print(f'    ⚠️  Early Simpsons (S{season_num}): {episode_id} - {episode_title}')
                    continue
            except:
                pass
        
        # Check if it's a holiday episode (for ALL shows - keyword-based)
        is_holiday = False
        for keyword in holiday_keywords:
            if keyword.lower() in episode_title.lower():
                holiday_episodes.append(episode)
                print(f'    🎃 Holiday episode ({show_name}): {episode_id} - {episode_title}')
                is_holiday = True
                break
        
        if not is_holiday:
            regular_episodes.append(episode)
    
    # Apply reordering
    filtered_episodes = []
    
    # Add regular episodes first (highest priority)
    filtered_episodes.extend(regular_episodes)
    
    # Add early Simpsons episodes (seasons 0, 1, 2) - pushed to back entirely
    filtered_episodes.extend(early_simpsons)
    if early_simpsons:
        print(f'    ⚠️  Pushed {len(early_simpsons)} early Simpsons episodes (S0-2) to back for {show_name}')
    
    # Add holiday episodes last (lowest priority) - for ALL shows
    filtered_episodes.extend(holiday_episodes)
    print(f'    🎃 Pushed {len(holiday_episodes)} holiday episodes to back for {show_name}')
    
    print(f'    📊 Filtered episodes: {len(regular_episodes)} regular, {len(early_simpsons)} early Simpsons, {len(holiday_episodes)} holiday')
    print(f'    🎯 Final episode count: {len(filtered_episodes)}')
    
    return filtered_episodes

def GetAllFilteredEpisodes():
    """
    Get all episodes from all shows with holiday filtering applied.
    This ensures holiday episodes are pushed to the back across ALL shows.
    """
    print('🎭 Applying holiday filtering to ALL shows in database...')
    
    # Get all episodes from all shows
    all_episodes = c.execute('''SELECT Show, Episode, SUM(ViewCount), Season, Title, Length, Type FROM episodes GROUP BY Show, Episode ORDER BY Show, Episode;''').fetchall()
    print(f'📺 Found {len(all_episodes)} total episodes across all shows')
    
    if not all_episodes:
        return []
    
    # Separate episodes into different categories
    regular_episodes = []
    holiday_episodes = []
    early_simpsons = []
    
    # Specific holiday keywords for filtering
    holiday_keywords = [
        'christmas', 'x-mas', 'xmas', 'holy night', 'horror', 'treehouse', 'thanksgiving', 'halloween'
    ]
    
    for episode in all_episodes:
        show_name = episode[0]
        episode_id = episode[1]  # Episode identifier (e.g., "s01e01")
        episode_title = episode[4] if len(episode) > 4 else ""  # Episode title (index 4, not 5)
        
        # Ensure episode_title is a string
        if not isinstance(episode_title, str):
            episode_title = str(episode_title) if episode_title is not None else ""
        
        # Check if it's early Simpsons (seasons 0, 1, 2) - push to back entirely
        if show_name.lower() == 'the simpsons':
            try:
                season_num = int(episode_id[1:3])  # Extract season number from "s01e01"
                if season_num <= 2:
                    early_simpsons.append(episode)
                    continue
            except:
                pass
        
        # Check if it's a holiday episode (for ALL shows - keyword-based)
        is_holiday = False
        for keyword in holiday_keywords:
            if keyword.lower() in episode_title.lower():
                holiday_episodes.append(episode)
                is_holiday = True
                break
        
        if not is_holiday:
            regular_episodes.append(episode)
    
    # Apply reordering
    filtered_episodes = []
    
    # Add regular episodes first (highest priority)
    filtered_episodes.extend(regular_episodes)
    
    # Add early Simpsons episodes (seasons 0, 1, 2) - pushed to back entirely
    filtered_episodes.extend(early_simpsons)
    
    # Add holiday episodes last (lowest priority) - for ALL shows
    filtered_episodes.extend(holiday_episodes)
    
    print(f'    📊 Filtered episodes: {len(regular_episodes)} regular, {len(early_simpsons)} early Simpsons, {len(holiday_episodes)} holiday')
    print(f'    🎯 Final episode count: {len(filtered_episodes)}')
    
    return filtered_episodes

def CollectionHolidayWash():
    """
    Comprehensive holiday episode cleaning operation.
    Scans all collections and TV shows for holiday keywords and pushes all holiday episodes to the back.
    """
    print('🧹 COLLECTION HOLIDAY WASH - COMPREHENSIVE CLEANING')
    print('=' * 60)
    
    # Specific holiday keywords for filtering
    holiday_keywords = [
        'christmas', 'x-mas', 'xmas', 'holy night', 'horror', 'treehouse', 'thanksgiving', 'halloween'
    ]
    
    print(f'🎯 Scanning for holiday keywords: {", ".join(holiday_keywords)}')
    print()
    
    # Step 1: Update view counts for all shows
    print('📊 STEP 1: UPDATING VIEW COUNTS FOR ALL SHOWS')
    showlist = CallDB('''SELECT Show FROM shows''')
    total_shows = len(showlist)
    print(f'📺 Found {total_shows} shows to process')
    
    for i, show in enumerate(showlist, 1):
        show_name = show[0]
        print(f'  [{i}/{total_shows}] Updating {show_name}...')
        ViewCountUpdate(show_name)
        showDB.commit()
    
    print('✅ View count update complete!')
    print()
    
    # Step 2: Get all episodes from all shows
    print('📋 STEP 2: COLLECTING ALL EPISODES FROM DATABASE')
    all_episodes = c.execute('''SELECT Show, Episode, SUM(ViewCount), Season, Title, Length, Type FROM episodes GROUP BY Show, Episode ORDER BY Show, Episode;''').fetchall()
    print(f'📺 Found {len(all_episodes)} total episodes across all shows')
    print()
    
    # Step 3: Analyze and categorize episodes
    print('🔍 STEP 3: ANALYZING EPISODES FOR HOLIDAY CONTENT')
    regular_episodes = []
    holiday_episodes = []
    early_simpsons = []
    
    holiday_shows = set()  # Track shows that have holiday episodes
    early_simpsons_count = 0
    holiday_count = 0
    
    for episode in all_episodes:
        show_name = episode[0]
        episode_id = episode[1]  # Episode identifier (e.g., "s01e01")
        episode_title = episode[4] if len(episode) > 4 else ""  # Episode title
        
        # Ensure episode_title is a string
        if not isinstance(episode_title, str):
            episode_title = str(episode_title) if episode_title is not None else ""
        
        # Check if it's early Simpsons (seasons 0, 1, 2) - push to back entirely
        if show_name.lower() == 'the simpsons':
            try:
                season_num = int(episode_id[1:3])  # Extract season number from "s01e01"
                if season_num <= 2:
                    early_simpsons.append(episode)
                    early_simpsons_count += 1
                    continue
            except:
                pass
        
        # Check if it's a holiday episode (for ALL shows - keyword-based)
        is_holiday = False
        for keyword in holiday_keywords:
            if keyword.lower() in episode_title.lower():
                holiday_episodes.append(episode)
                holiday_shows.add(show_name)
                holiday_count += 1
                is_holiday = True
                break
        
        if not is_holiday:
            regular_episodes.append(episode)
    
    print(f'✅ Analysis complete!')
    print(f'  📺 Regular episodes: {len(regular_episodes)}')
    print(f'  ⚠️  Early Simpsons (S0-2): {early_simpsons_count}')
    print(f'  🎃 Holiday episodes: {holiday_count}')
    print(f'  📺 Shows with holiday episodes: {len(holiday_shows)}')
    print()
    
    # Step 4: Show detailed breakdown
    print('📊 STEP 4: DETAILED HOLIDAY EPISODE BREAKDOWN')
    if holiday_shows:
        print('🎃 Shows containing holiday episodes:')
        for show in sorted(holiday_shows):
            show_holiday_eps = [ep for ep in holiday_episodes if ep[0] == show]
            print(f'  • {show}: {len(show_holiday_eps)} holiday episodes')
    else:
        print('✅ No holiday episodes found!')
    print()
    
    # Step 5: Create reordered episode list
    print('🔄 STEP 5: CREATING REORDERED EPISODE LIST')
    reordered_episodes = []
    
    # Add regular episodes first (highest priority)
    reordered_episodes.extend(regular_episodes)
    
    # Add early Simpsons episodes (seasons 0, 1, 2) - pushed to back entirely
    reordered_episodes.extend(early_simpsons)
    
    # Add holiday episodes last (lowest priority) - for ALL shows
    reordered_episodes.extend(holiday_episodes)
    
    print(f'✅ Reordering complete!')
    print(f'  📺 Final episode count: {len(reordered_episodes)}')
    print(f'  🎯 Priority order: Regular → Early Simpsons → Holiday')
    print()
    
    # Step 6: Save the reordered list for future use
    print('💾 STEP 6: SAVING REORDERED EPISODE LIST')
    try:
        # Create a temporary table with the reordered episodes
        c.execute('''DROP TABLE IF EXISTS episodes_reordered''')
        c.execute('''CREATE TABLE episodes_reordered AS SELECT * FROM episodes WHERE 1=0''')
        
        # Insert reordered episodes
        for episode in reordered_episodes:
            c.execute('''INSERT INTO episodes_reordered (ID, Type, Show, Season, Episode, Title, Server, ViewCount, Length) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', episode)
        
        showDB.commit()
        print('✅ Reordered episode list saved successfully!')
    except Exception as e:
        print(f'⚠️  Warning: Could not save reordered list: {str(e)}')
    print()
    
    # Step 7: Summary
    print('🎉 HOLIDAY WASH COMPLETE!')
    print('=' * 60)
    print(f'📊 Summary:')
    print(f'  • Total episodes processed: {len(all_episodes)}')
    print(f'  • Regular episodes: {len(regular_episodes)} (highest priority)')
    print(f'  • Early Simpsons (S0-2): {early_simpsons_count} (pushed to back)')
    print(f'  • Holiday episodes: {holiday_count} (lowest priority)')
    print(f'  • Shows with holiday content: {len(holiday_shows)}')
    print()
    print(f'🎯 All holiday episodes have been pushed to the back!')
    print(f'🎃 Keywords detected: {", ".join(holiday_keywords)}')
    print()
    
    return True

def TVLineup():
    """
    Creates a balanced TV lineup ensuring no more than 2 episodes of the same show play back-to-back.
    This creates a diverse viewing experience across all collections.
    """
    print('📺 TV LINEUP - BALANCED SHOW SHUFFLE')
    print('=' * 50)
    
    # Get all collections from all servers
    all_collections = []
    for serv in conservs:
        if serv != ':(':
            try:
                library = serv.library.section('TV Shows')
                collections = library.collections()
                for collection in collections:
                    all_collections.append((collection, serv))
            except Exception as e:
                print(f'  ⚠️  Could not access collections on {serv.friendlyName}: {str(e)}')
    
    if not all_collections:
        print('❌ No collections found on any server')
        return False
    
    print(f'📚 Found {len(all_collections)} collections across all servers:')
    for i, (collection, server) in enumerate(all_collections):
        print(f'  {i+1}. {collection.title} ({collection.childCount} items) - {server.friendlyName}')
    print()
    
    # Get shows from all collections
    all_collection_shows = []
    collection_show_map = {}  # Maps shows to their collections
    
    for collection, server in all_collections:
        try:
            collection_shows = []
            for item in collection.items():
                if item.type == 'show':
                    collection_shows.append(item.title)
                    all_collection_shows.append(item.title)
                    if item.title not in collection_show_map:
                        collection_show_map[item.title] = []
                    collection_show_map[item.title].append(collection.title)
            print(f'📺 {collection.title}: {len(collection_shows)} shows')
        except Exception as e:
            print(f'❌ Error accessing collection {collection.title}: {str(e)}')
    
    # Remove duplicates while preserving order
    unique_shows = []
    seen = set()
    for show in all_collection_shows:
        if show not in seen:
            unique_shows.append(show)
            seen.add(show)
    
    print(f'\n📊 Total unique shows across all collections: {len(unique_shows)}')
    print()
    
    # Create balanced lineup
    print('🎯 Creating balanced TV lineup...')
    balanced_lineup = []
    show_count = {}  # Track consecutive episodes per show
    max_consecutive = 2  # Maximum consecutive episodes allowed
    
    # Get all episodes from all shows with holiday filtering applied
    allFilteredEps = GetAllFilteredEpisodes()
    print(f'📺 Found {len(allFilteredEps)} total episodes after holiday filtering')
    
    if not allFilteredEps:
        print('❌ No episodes found after filtering')
        return False
    
    # Group episodes by show
    episodes_by_show = {}
    for episode in allFilteredEps:
        show_name = episode[0]
        if show_name not in episodes_by_show:
            episodes_by_show[show_name] = []
        episodes_by_show[show_name].append(episode)
    
    print(f'📺 Episodes grouped by {len(episodes_by_show)} shows')
    print()
    
    # Create balanced lineup algorithm
    print('🔄 Building balanced lineup...')
    import random
    
    # Initialize show counts
    for show in episodes_by_show:
        show_count[show] = 0
    
    # Create lineup ensuring no more than 2 consecutive episodes of the same show
    lineup_length = min(50, len(allFilteredEps))  # Limit to 50 episodes for lineup
    consecutive_count = 0
    last_show = None
    
    for i in range(lineup_length):
        # Find eligible shows (those that haven't exceeded consecutive limit)
        eligible_shows = []
        for show, episodes in episodes_by_show.items():
            if show_count[show] < max_consecutive and episodes:
                eligible_shows.append(show)
        
        if not eligible_shows:
            # Reset counts if no eligible shows
            for show in show_count:
                show_count[show] = 0
            eligible_shows = list(episodes_by_show.keys())
        
        # Select a random eligible show
        selected_show = random.choice(eligible_shows)
        
        # Get the next episode for this show (lowest view count first)
        if episodes_by_show[selected_show]:
            selected_episode = episodes_by_show[selected_show].pop(0)  # Take first episode (lowest view count)
            balanced_lineup.append(selected_episode)
            
            # Update consecutive count
            if selected_show == last_show:
                consecutive_count += 1
            else:
                consecutive_count = 1
                last_show = selected_show
            
            show_count[selected_show] = consecutive_count
            
            print(f'  [{i+1:2d}] {selected_show} - {selected_episode[1]} (consecutive: {consecutive_count})')
    
    print(f'\n✅ Balanced lineup created with {len(balanced_lineup)} episodes!')
    print()
    
    # Analyze the lineup
    print('📊 LINEUP ANALYSIS:')
    print('=' * 30)
    
    # Count episodes per show in the lineup
    lineup_show_counts = {}
    consecutive_sequences = []
    current_sequence = []
    
    for episode in balanced_lineup:
        show_name = episode[0]
        if show_name not in lineup_show_counts:
            lineup_show_counts[show_name] = 0
        lineup_show_counts[show_name] += 1
        
        # Track consecutive sequences
        if not current_sequence or current_sequence[-1] == show_name:
            current_sequence.append(show_name)
        else:
            if len(current_sequence) > 1:
                consecutive_sequences.append(current_sequence.copy())
            current_sequence = [show_name]
    
    # Add the last sequence
    if len(current_sequence) > 1:
        consecutive_sequences.append(current_sequence)
    
    # Show episode distribution
    print('📺 Episode distribution:')
    for show, count in sorted(lineup_show_counts.items(), key=lambda x: x[1], reverse=True):
        collections = collection_show_map.get(show, ['Unknown'])
        print(f'  • {show}: {count} episodes (from: {", ".join(collections)})')
    
    print()
    
    # Show consecutive sequences
    print('🔄 Consecutive sequences:')
    if consecutive_sequences:
        for i, sequence in enumerate(consecutive_sequences, 1):
            if len(sequence) <= max_consecutive:
                print(f'  ✅ Sequence {i}: {sequence[0]} x{len(sequence)} (within limit)')
            else:
                print(f'  ⚠️  Sequence {i}: {sequence[0]} x{len(sequence)} (exceeds limit!)')
    else:
        print('  ✅ No consecutive sequences found')
    
    print()
    
    # Show lineup preview
    print('📋 LINEUP PREVIEW (first 20 episodes):')
    print('=' * 40)
    for i, episode in enumerate(balanced_lineup[:20], 1):
        show_name = episode[0]
        episode_id = episode[1]
        episode_title = episode[4] if len(episode) > 4 else "Unknown"
        view_count = episode[2]
        print(f'  {i:2d}. {show_name} - {episode_id} - {episode_title} (views: {view_count})')
    
    if len(balanced_lineup) > 20:
        print(f'  ... and {len(balanced_lineup) - 20} more episodes')
    
    print()
    
    # Save the lineup for future use
    print('💾 Saving balanced lineup...')
    try:
        # Create a table for the balanced lineup
        c.execute('''DROP TABLE IF EXISTS tv_lineup''')
        c.execute('''CREATE TABLE tv_lineup 
                    (ID INTEGER PRIMARY KEY, Show TEXT, Episode TEXT, Title TEXT, ViewCount INT, Collection TEXT)''')
        
        for i, episode in enumerate(balanced_lineup):
            show_name = episode[0]
            episode_id = episode[1]
            episode_title = episode[4] if len(episode) > 4 else ""
            view_count = episode[2]
            collections = collection_show_map.get(show_name, ['Unknown'])
            collection_str = ", ".join(collections)
            
            c.execute('''INSERT INTO tv_lineup (ID, Show, Episode, Title, ViewCount, Collection) 
                        VALUES (?, ?, ?, ?, ?, ?)''', (i+1, show_name, episode_id, episode_title, view_count, collection_str))
        
        showDB.commit()
        print('✅ Balanced lineup saved successfully!')
    except Exception as e:
        print(f'⚠️  Warning: Could not save lineup: {str(e)}')
    
    print()
    print('🎉 TV LINEUP COMPLETE!')
    print('=' * 50)
    print(f'📊 Summary:')
    print(f'  • Total episodes in lineup: {len(balanced_lineup)}')
    print(f'  • Unique shows: {len(lineup_show_counts)}')
    print(f'  • Maximum consecutive episodes: {max_consecutive}')
    print(f'  • Collections processed: {len(all_collections)}')
    print()
    print(f'🎯 The lineup ensures no more than {max_consecutive} episodes of the same show play consecutively!')
    print()
    
    return balanced_lineup

def AnimationDomination():
    """
    Creates a specific lineup for Adult Swim Ultra collection with the pattern:
    x4 The Simpsons, x4 Family Guy, x4 American Dad, x4 South Park, x2 The Cleveland Show, x4 Mixed No Repeats, Repeat
    """
    print('🎬 ANIMATION DOMINATION - ADULT SWIM ULTRA LINEUP')
    print('=' * 60)
    
    # Define the specific lineup pattern
    lineup_pattern = [
        ('The Simpsons', 4),
        ('Family Guy', 4),
        ('American Dad', 4),
        ('South Park', 4),
        ('The Cleveland Show', 2),
        ('Mixed No Repeats', 4)
    ]
    
    print('🎯 Target lineup pattern:')
    for show, count in lineup_pattern:
        print(f'  • {show}: {count} episodes')
    print()
    
    # Find the Adult Swim Ultra collection
    adult_swim_ultra_collection = None
    adult_swim_ultra_server = None
    
    for serv in conservs:
        if serv != ':(':
            try:
                library = serv.library.section('TV Shows')
                collections = library.collections()
                for collection in collections:
                    if collection.title.lower() == 'adult swim ultra':
                        adult_swim_ultra_collection = collection
                        adult_swim_ultra_server = serv
                        break
                if adult_swim_ultra_collection:
                    break
            except Exception as e:
                print(f'  ⚠️  Could not access collections on {serv.friendlyName}: {str(e)}')
    
    if not adult_swim_ultra_collection:
        print('❌ Adult Swim Ultra collection not found on any server')
        return False
    
    print(f'✅ Found Adult Swim Ultra collection on {adult_swim_ultra_server.friendlyName}')
    print(f'📺 Collection contains {adult_swim_ultra_collection.childCount} items')
    print()
    
    # Get shows from Adult Swim Ultra collection
    collection_shows = []
    try:
        for item in adult_swim_ultra_collection.items():
            if item.type == 'show':
                collection_shows.append(item.title)
        print(f'📺 Found {len(collection_shows)} shows in Adult Swim Ultra:')
        for show in collection_shows:
            print(f'  • {show}')
    except Exception as e:
        print(f'❌ Error accessing Adult Swim Ultra shows: {str(e)}')
        return False
    
    print()
    
    # Get all episodes from all shows with holiday filtering applied
    allFilteredEps = GetAllFilteredEpisodes()
    print(f'📺 Found {len(allFilteredEps)} total episodes after holiday filtering')
    
    if not allFilteredEps:
        print('❌ No episodes found after filtering')
        return False
    
    # Group episodes by show
    episodes_by_show = {}
    for episode in allFilteredEps:
        show_name = episode[0]
        if show_name not in episodes_by_show:
            episodes_by_show[show_name] = []
        episodes_by_show[show_name].append(episode)
    
    print(f'📺 Episodes grouped by {len(episodes_by_show)} shows')
    print()
    
    # Create the specific lineup
    print('🎬 Creating Animation Domination lineup...')
    animation_lineup = []
    mixed_episodes = []
    
    # Track used episodes to avoid repeats in mixed section
    used_episodes = set()
    
    for show_name, episode_count in lineup_pattern:
        if show_name == 'Mixed No Repeats':
            # For mixed section, select episodes from shows not already used in this cycle
            print(f'🎲 Selecting {episode_count} mixed episodes (no repeats)...')
            
            # Get all shows that haven't been used in this cycle
            used_shows_in_cycle = {pattern[0] for pattern in lineup_pattern[:lineup_pattern.index((show_name, episode_count))]}
            available_shows = [show for show in episodes_by_show.keys() if show not in used_shows_in_cycle]
            
            mixed_selected = 0
            for available_show in available_shows:
                if mixed_selected >= episode_count:
                    break
                    
                for episode in episodes_by_show[available_show]:
                    episode_key = f"{episode[0]}_{episode[1]}"  # show_episode_id
                    if episode_key not in used_episodes:
                        mixed_episodes.append(episode)
                        used_episodes.add(episode_key)
                        mixed_selected += 1
                        print(f'    [{mixed_selected}] {episode[0]} - {episode[1]} (mixed)')
                        if mixed_selected >= episode_count:
                            break
            
            animation_lineup.extend(mixed_episodes)
            
        else:
            # For specific shows, select the requested number of episodes
            print(f'📺 Selecting {episode_count} episodes from {show_name}...')
            
            if show_name in episodes_by_show:
                show_episodes = episodes_by_show[show_name]
                selected_episodes = []
                
                for i in range(min(episode_count, len(show_episodes))):
                    episode = show_episodes[i]
                    selected_episodes.append(episode)
                    episode_key = f"{episode[0]}_{episode[1]}"
                    used_episodes.add(episode_key)
                    print(f'    [{i+1}] {episode[1]} - {episode[4] if len(episode) > 4 else "Unknown"} (views: {episode[2]})')
                
                animation_lineup.extend(selected_episodes)
            else:
                print(f'    ⚠️  {show_name} not found in episodes')
    
    print(f'\n✅ Animation Domination lineup created with {len(animation_lineup)} episodes!')
    print()
    
    # Analyze the lineup
    print('📊 LINEUP ANALYSIS:')
    print('=' * 30)
    
    # Count episodes per show in the lineup
    lineup_show_counts = {}
    for episode in animation_lineup:
        show_name = episode[0]
        if show_name not in lineup_show_counts:
            lineup_show_counts[show_name] = 0
        lineup_show_counts[show_name] += 1
    
    # Show episode distribution
    print('📺 Episode distribution:')
    for show, count in sorted(lineup_show_counts.items(), key=lambda x: x[1], reverse=True):
        print(f'  • {show}: {count} episodes')
    
    print()
    
    # Show the complete lineup
    print('📋 COMPLETE ANIMATION DOMINATION LINEUP:')
    print('=' * 50)
    
    current_show = None
    show_count = 0
    
    for i, episode in enumerate(animation_lineup, 1):
        show_name = episode[0]
        episode_id = episode[1]
        episode_title = episode[4] if len(episode) > 4 else "Unknown"
        view_count = episode[2]
        
        # Track show transitions
        if show_name != current_show:
            if current_show:
                print(f'  ── End of {current_show} ({show_count} episodes) ──')
            current_show = show_name
            show_count = 1
            print(f'  ── {show_name} ──')
        else:
            show_count += 1
        
        print(f'  {i:2d}. {episode_id} - {episode_title} (views: {view_count})')
    
    if current_show:
        print(f'  ── End of {current_show} ({show_count} episodes) ──')
    
    print()
    
    # Save the lineup for future use
    print('💾 Saving Animation Domination lineup...')
    try:
        # Create a table for the animation domination lineup
        c.execute('''DROP TABLE IF EXISTS animation_domination_lineup''')
        c.execute('''CREATE TABLE animation_domination_lineup 
                    (ID INTEGER PRIMARY KEY, Show TEXT, Episode TEXT, Title TEXT, ViewCount INT, Pattern_Order INT)''')
        
        for i, episode in enumerate(animation_lineup):
            show_name = episode[0]
            episode_id = episode[1]
            episode_title = episode[4] if len(episode) > 4 else ""
            view_count = episode[2]
            
            # Determine pattern order (which part of the pattern this episode belongs to)
            pattern_order = 0
            current_count = 0
            for pattern_show, pattern_count in lineup_pattern:
                if pattern_show == 'Mixed No Repeats':
                    # For mixed episodes, check if it's in the mixed section
                    if show_name not in [p[0] for p in lineup_pattern[:lineup_pattern.index((pattern_show, pattern_count))]]:
                        pattern_order = lineup_pattern.index((pattern_show, pattern_count))
                        break
                else:
                    if show_name == pattern_show:
                        pattern_order = lineup_pattern.index((pattern_show, pattern_count))
                        break
                    current_count += pattern_count
            
            c.execute('''INSERT INTO animation_domination_lineup (ID, Show, Episode, Title, ViewCount, Pattern_Order) 
                        VALUES (?, ?, ?, ?, ?, ?)''', (i+1, show_name, episode_id, episode_title, view_count, pattern_order))
        
        showDB.commit()
        print('✅ Animation Domination lineup saved successfully!')
    except Exception as e:
        print(f'⚠️  Warning: Could not save lineup: {str(e)}')
    
    print()
    print('🎉 ANIMATION DOMINATION COMPLETE!')
    print('=' * 60)
    print(f'📊 Summary:')
    print(f'  • Total episodes in lineup: {len(animation_lineup)}')
    print(f'  • Unique shows: {len(lineup_show_counts)}')
    print(f'  • Collection: Adult Swim Ultra')
    print(f'  • Pattern: {sum(count for _, count in lineup_pattern)} episodes total')
    print()
    print(f'🎯 The lineup follows the exact pattern:')
    for show, count in lineup_pattern:
        print(f'  • {show}: {count} episodes')
    print()
    print(f'🔄 This pattern can be repeated for continuous Animation Domination!')
    print()
    
    return animation_lineup

def SuperShuffle():
    """
    Refined super shuffle system that works with collections one at a time,
    starting with the currently playing collection and cycling through systematically.
    """
    print('🚀 SUPER SHUFFLE - REFINED COLLECTION SYSTEM')
    print('=' * 60)
    
    # Step 1: Get all collections and determine current collection
    print('🔄 STEP 1: ANALYZING COLLECTIONS')
    print('=' * 35)
    
    # Get all collections from all servers
    all_collections = []
    for serv in conservs:
        if serv != ':(':
            try:
                library = serv.library.section('TV Shows')
                collections = library.collections()
                for collection in collections:
                    all_collections.append((collection, serv))
            except Exception as e:
                print(f'  ⚠️  Could not access collections on {serv.friendlyName}: {str(e)}')
    
    if not all_collections:
        print('❌ No collections found on any server')
        return False
    
    print(f'📚 Found {len(all_collections)} collections across all servers')
    
    # Get current collection index from tracking file
    try:
        with open('collection_index.txt', 'r') as f:
            current_index = int(f.read().strip())
    except:
        current_index = 0
    
    # Ensure current_index is within bounds
    if current_index >= len(all_collections):
        current_index = 0
    
    current_collection, current_server = all_collections[current_index]
    print(f'🎯 Currently active collection: {current_collection.title} (Index: {current_index + 1}/{len(all_collections)})')
    print(f'🏠 Server: {current_server.friendlyName}')
    print()
    
    # Step 2: Collection operation mode selection
    print('🎲 STEP 2: COLLECTION OPERATION MODE')
    print('=' * 40)
    print('Select how you want to work with collections:')
    print('1. Work with current collection only')
    print('2. Cycle to next collection')
    print('3. Work through all collections systematically')
    print('4. Select specific collection')
    
    while True:
        try:
            mode_choice = input('Enter your choice (1-4): ').strip()
            if mode_choice in ['1', '2', '3', '4']:
                break
            else:
                print('❌ Invalid choice. Please enter 1-4.')
        except KeyboardInterrupt:
            print('\n❌ Operation cancelled.')
            return False
    
    # Step 3: Determine target collection(s)
    target_collections = []
    
    if mode_choice == '1':
        # Work with current collection only
        target_collections = [(current_collection, current_server, current_index)]
        print(f'✅ Working with current collection: {current_collection.title}')
        
    elif mode_choice == '2':
        # Cycle to next collection
        next_index = (current_index + 1) % len(all_collections)
        next_collection, next_server = all_collections[next_index]
        target_collections = [(next_collection, next_server, next_index)]
        
        # Update the tracking file
        try:
            with open('collection_index.txt', 'w') as f:
                f.write(str(next_index))
        except:
            pass
        
        print(f'✅ Cycling to next collection: {next_collection.title}')
        
    elif mode_choice == '3':
        # Work through all collections systematically
        target_collections = []
        for i, (collection, server) in enumerate(all_collections):
            target_collections.append((collection, server, i))
        print(f'✅ Working through all {len(target_collections)} collections systematically')
        
    elif mode_choice == '4':
        # Select specific collection
        print('\n📚 Available collections:')
        for i, (collection, server) in enumerate(all_collections, 1):
            status = " (CURRENT)" if i-1 == current_index else ""
            print(f'{i}. {collection.title} ({collection.childCount} items) - {server.friendlyName}{status}')
        
        while True:
            try:
                collection_choice = input(f'Select collection (1-{len(all_collections)}): ').strip()
                collection_index = int(collection_choice) - 1
                if 0 <= collection_index < len(all_collections):
                    selected_collection, selected_server = all_collections[collection_index]
                    target_collections = [(selected_collection, selected_server, collection_index)]
                    
                    # Update the tracking file if different from current
                    if collection_index != current_index:
                        try:
                            with open('collection_index.txt', 'w') as f:
                                f.write(str(collection_index))
                        except:
                            pass
                    
                    print(f'✅ Selected collection: {selected_collection.title}')
                    break
                else:
                    print(f'❌ Invalid choice. Please enter 1-{len(all_collections)}.')
            except (ValueError, KeyboardInterrupt):
                print('❌ Invalid input or operation cancelled.')
                return False
    
    print()
    
    # Step 4: Client selection
    print('📱 STEP 4: CLIENT SELECTION')
    print('=' * 30)
    
    all_clients = [x for x in myAccount.resources() if "player" in x.provides]
    if not all_clients:
        print('❌ No Plex clients found.')
        return False
    
    print('Available Plex clients:')
    for i, client in enumerate(all_clients, 1):
        status = "Online" if client.presence else "Offline"
        print(f'{i}. {client.name} ({client.platform}) - {status}')
    
    while True:
        try:
            client_choice = input(f'Select client (1-{len(all_clients)}): ').strip()
            client_index = int(client_choice) - 1
            if 0 <= client_index < len(all_clients):
                selected_client = all_clients[client_index]
                break
            else:
                print(f'❌ Invalid choice. Please enter 1-{len(all_clients)}.')
        except (ValueError, KeyboardInterrupt):
            print('❌ Invalid input or operation cancelled.')
            return False
    
    print(f'✅ Selected client: {selected_client.name} ({selected_client.platform})')
    
    # Step 5: Prioritization options
    print('\n🎯 STEP 5: PRIORITIZATION OPTIONS')
    print('=' * 35)
    print('Select prioritization mode:')
    print('1. Push Holiday Episodes Back (Default)')
    print('2. Prioritize Halloween Episodes')
    print('3. Prioritize Thanksgiving Episodes')
    print('4. Prioritize Christmas Episodes')
    print('5. Prioritize Summer Episodes')
    print('6. Prioritize True Random')
    
    while True:
        try:
            priority_choice = input('Enter your choice (1-6): ').strip()
            if priority_choice in ['1', '2', '3', '4', '5', '6']:
                break
            else:
                print('❌ Invalid choice. Please enter 1-6.')
        except KeyboardInterrupt:
            print('\n❌ Operation cancelled.')
            return False
    
    # Step 6: Execute collection processing
    print('\n🚀 STEP 6: EXECUTING SUPER SHUFFLE')
    print('=' * 40)
    
    try:
        # Connect to selected client
        if selected_client.presence:
            client_connection = selected_client.connect()
            print(f'✅ Connected to {selected_client.name}')
        else:
            print(f'⚠️  Client {selected_client.name} is offline')
            client_connection = None
        
        # Process each target collection
        successful_plays = 0
        total_collections = len(target_collections)
        
        for i, (collection, server, collection_index) in enumerate(target_collections, 1):
            print(f'\n🔄 Processing collection {i}/{total_collections}: {collection.title}')
            print(f'🏠 Server: {server.friendlyName}')
            print(f'📊 Items: {collection.childCount}')
            
            # Get shows from this collection
            collection_shows = []
            try:
                for item in collection.items():
                    if item.type == 'show':
                        collection_shows.append(item.title)
                print(f'📺 Found {len(collection_shows)} shows in {collection.title}')
            except Exception as e:
                print(f'❌ Error accessing collection shows: {str(e)}')
                continue
            
            if not collection_shows:
                print(f'⚠️  No shows found in {collection.title}, skipping...')
                continue
            
            # Update view counts for all shows in this collection
            print(f'📊 Updating view counts for {len(collection_shows)} shows...')
            for show in collection_shows:
                try:
                    ViewCountUpdate(show)
                    showDB.commit()  # Commit after each show update
                except Exception as e:
                    print(f'⚠️  Error updating view counts for {show}: {str(e)}')
                    continue
            
            # Get episodes from this collection
            collection_episodes = GetEpisodesFromCollection(collection.title)
            
            if not collection_episodes:
                print(f'⚠️  No episodes found for {collection.title}, skipping...')
                continue
            
            # Apply prioritization
            prioritized_episodes = ApplyPrioritization(collection_episodes, priority_choice)
            
            if not prioritized_episodes:
                print(f'⚠️  No episodes after prioritization for {collection.title}, skipping...')
                continue
            
            # Select episode with lowest view count
            try:
                selected_episode_data = min(prioritized_episodes, key=lambda x: x[2])  # x[2] is view count
            except ValueError:
                print(f'⚠️  No valid episodes found for {collection.title}, skipping...')
                continue
            
            # Convert database data to Plex episode object
            plex_episode = ConvertToPlexEpisode(selected_episode_data)
            
            if not plex_episode:
                print(f'⚠️  Could not convert episode data for {collection.title}, skipping...')
                continue
            
            # Play the episode
            if client_connection:
                try:
                    client_connection.playMedia(plex_episode)
                    print(f'✅ Playing from {collection.title}: {selected_episode_data[0]} - {selected_episode_data[1]}')
                    print(f'📊 View count: {selected_episode_data[2]}')
                    successful_plays += 1
                    
                    # If working with multiple collections, ask if user wants to continue
                    if total_collections > 1 and i < total_collections:
                        print(f'\n🎯 {total_collections - i} collection(s) remaining...')
                        continue_choice = input('Continue to next collection? (y/n): ').strip().lower()
                        if continue_choice not in ['y', 'yes']:
                            print('⏹️  Stopping at user request.')
                            break
                    
                except Exception as e:
                    print(f'❌ Error playing episode from {collection.title}: {str(e)}')
                    continue
            else:
                print(f'⚠️  Client not available, would play: {selected_episode_data[0]} - {selected_episode_data[1]}')
                successful_plays += 1
        
        # Summary
        print(f'\n🎉 SUPER SHUFFLE COMPLETE!')
        print('=' * 40)
        print(f'📊 Summary:')
        print(f'  • Collections processed: {len(target_collections)}')
        print(f'  • Successful plays: {successful_plays}')
        print(f'  • Current collection index: {current_index + 1}/{len(all_collections)}')
        
        if successful_plays > 0:
            print(f'✅ Episode(s) successfully queued on {selected_client.name}')
        else:
            print(f'❌ No episodes were played successfully')
            
    except Exception as e:
        print(f'❌ Error during super shuffle execution: {str(e)}')
        return False
    
    return True

def ShowCurrentCollectionStatus():
    """
    Display the current collection status and tracking information.
    """
    print('📊 CURRENT COLLECTION STATUS')
    print('=' * 40)
    
    # Get all collections from all servers
    all_collections = []
    for serv in conservs:
        if serv != ':(':
            try:
                library = serv.library.section('TV Shows')
                collections = library.collections()
                for collection in collections:
                    all_collections.append((collection, serv))
            except Exception as e:
                print(f'  ⚠️  Could not access collections on {serv.friendlyName}: {str(e)}')
    
    if not all_collections:
        print('❌ No collections found on any server')
        return False
    
    # Get current collection index from tracking file
    try:
        with open('collection_index.txt', 'r') as f:
            current_index = int(f.read().strip())
    except:
        current_index = 0
    
    # Ensure current_index is within bounds
    if current_index >= len(all_collections):
        current_index = 0
    
    current_collection, current_server = all_collections[current_index]
    
    print(f'📚 Total collections available: {len(all_collections)}')
    print(f'🎯 Currently active collection: {current_collection.title}')
    print(f'🏠 Server: {current_server.friendlyName}')
    print(f'📊 Collection index: {current_index + 1}/{len(all_collections)}')
    print(f'📺 Items in collection: {current_collection.childCount}')
    
    # Show next collection
    next_index = (current_index + 1) % len(all_collections)
    next_collection, next_server = all_collections[next_index]
    print(f'🔄 Next collection: {next_collection.title} ({next_server.friendlyName})')
    
    print()
    print('📋 All collections:')
    for i, (collection, server) in enumerate(all_collections):
        status = " ← CURRENT" if i == current_index else ""
        print(f'  {i+1:2d}. {collection.title} ({collection.childCount} items) - {server.friendlyName}{status}')
    
    return True

def ResetCollectionIndex():
    """
    Reset the collection index to start from the beginning.
    """
    print('🔄 RESETTING COLLECTION INDEX')
    print('=' * 35)
    
    try:
        with open('collection_index.txt', 'w') as f:
            f.write('0')
        print('✅ Collection index reset to 0 (first collection)')
        print('💡 Next collection shuffle will start from the first collection')
        return True
    except Exception as e:
        print(f'❌ Error resetting collection index: {str(e)}')
        return False

def ExecuteBasicReshuffle(selected_collection, use_all_collections, priority_choice, client_connection):
    """Execute basic reshuffle with selected options."""
    print('🎲 Basic reshuffle execution...')
    
    # Get episodes based on collection selection
    if use_all_collections:
        episodes = GetAllFilteredEpisodes()
    else:
        collection_name = selected_collection[0].title
        episodes = GetEpisodesFromCollection(collection_name)
    
    if not episodes:
        print('❌ No episodes found')
        return False
    
    # Apply prioritization
    prioritized_episodes = ApplyPrioritization(episodes, priority_choice)
    
    if not prioritized_episodes:
        print('❌ No episodes after prioritization')
        return False
    
    # Select random episode
    import random
    selected_episode_data = random.choice(prioritized_episodes)
    
    # Convert database data to Plex episode object
    plex_episode = ConvertToPlexEpisode(selected_episode_data)
    
    if not plex_episode:
        print('❌ Could not convert episode data to Plex object')
        return False
    
    # Play the episode
    if client_connection:
        try:
            client_connection.playMedia(plex_episode)
            print(f'✅ Playing: {selected_episode_data[0]} - {selected_episode_data[1]}')
            return True
        except Exception as e:
            print(f'❌ Error playing episode: {str(e)}')
            return False
    
    return False

def ExecuteTVLineupReshuffle(selected_collection, use_all_collections, priority_choice, client_connection):
    """Execute reshuffle with TV-Lineup integration."""
    print('📺 TV-Lineup reshuffle execution...')
    
    # Create TV lineup
    tv_lineup = TVLineup()
    if not tv_lineup:
        print('❌ Failed to create TV lineup')
        return False
    
    # Apply prioritization to lineup
    prioritized_lineup = ApplyPrioritization(tv_lineup, priority_choice)
    
    if not prioritized_lineup:
        print('❌ No episodes in lineup after prioritization')
        return False
    
    # Select episode from lineup
    import random
    selected_episode_data = random.choice(prioritized_lineup)
    
    # Convert database data to Plex episode object
    plex_episode = ConvertToPlexEpisode(selected_episode_data)
    
    if not plex_episode:
        print('❌ Could not convert episode data to Plex object')
        return False
    
    # Play the episode
    if client_connection:
        try:
            client_connection.playMedia(plex_episode)
            print(f'✅ Playing from TV-Lineup: {selected_episode_data[0]} - {selected_episode_data[1]}')
            return True
        except Exception as e:
            print(f'❌ Error playing episode: {str(e)}')
            return False
    
    return False

def ExecuteAnimationDominationReshuffle(selected_collection, use_all_collections, priority_choice, client_connection):
    """Execute reshuffle with Animation Domination integration."""
    print('🎬 Animation Domination reshuffle execution...')
    
    # Create Animation Domination lineup
    animation_lineup = AnimationDomination()
    if not animation_lineup:
        print('❌ Failed to create Animation Domination lineup')
        return False
    
    # Apply prioritization to lineup
    prioritized_lineup = ApplyPrioritization(animation_lineup, priority_choice)
    
    if not prioritized_lineup:
        print('❌ No episodes in lineup after prioritization')
        return False
    
    # Select episode from lineup
    import random
    selected_episode_data = random.choice(prioritized_lineup)
    
    # Convert database data to Plex episode object
    plex_episode = ConvertToPlexEpisode(selected_episode_data)
    
    if not plex_episode:
        print('❌ Could not convert episode data to Plex object')
        return False
    
    # Play the episode
    if client_connection:
        try:
            client_connection.playMedia(plex_episode)
            print(f'✅ Playing from Animation Domination: {selected_episode_data[0]} - {selected_episode_data[1]}')
            return True
        except Exception as e:
            print(f'❌ Error playing episode: {str(e)}')
            return False
    
    return False

def GetEpisodesFromCollection(collection_name):
    """Get episodes from a specific collection."""
    print(f'📚 Getting episodes from collection: {collection_name}')
    
    # Find the collection
    target_collection = None
    for serv in conservs:
        if serv != ':(':
            try:
                library = serv.library.section('TV Shows')
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
        print(f'❌ Collection {collection_name} not found')
        return []
    
    # Get shows from collection
    collection_shows = []
    try:
        for item in target_collection.items():
            if item.type == 'show':
                collection_shows.append(item.title)
    except Exception as e:
        print(f'❌ Error accessing collection shows: {str(e)}')
        return []
    
    # Get episodes for these shows
    all_episodes = GetAllFilteredEpisodes()
    collection_episodes = [ep for ep in all_episodes if ep[0] in collection_shows]
    
    print(f'📺 Found {len(collection_episodes)} episodes from {collection_name}')
    return collection_episodes

def ApplyPrioritization(episodes, priority_choice):
    """Apply the selected prioritization to episodes."""
    print(f'🎯 Applying prioritization mode {priority_choice}...')
    
    if priority_choice == '1':
        # Push Holiday Episodes Back (default behavior)
        return episodes
    
    elif priority_choice == '2':
        # Prioritize Halloween Episodes
        halloween_keywords = ['halloween', 'horror', 'treehouse', 'spooky', 'scary', 'ghost', 'witch', 'vampire']
        return PrioritizeByKeywords(episodes, halloween_keywords, 'Halloween')
    
    elif priority_choice == '3':
        # Prioritize Thanksgiving Episodes
        thanksgiving_keywords = ['thanksgiving', 'turkey', 'pilgrim', 'harvest', 'feast']
        return PrioritizeByKeywords(episodes, thanksgiving_keywords, 'Thanksgiving')
    
    elif priority_choice == '4':
        # Prioritize Christmas Episodes
        christmas_keywords = ['christmas', 'x-mas', 'xmas', 'holy night', 'santa', 'elf']
        return PrioritizeByKeywords(episodes, christmas_keywords, 'Christmas')
    
    elif priority_choice == '5':
        # Prioritize Summer Episodes
        summer_keywords = ['summer', 'beach', 'vacation', 'hot', 'sun', 'pool', 'barbecue', 'bbq']
        return PrioritizeByKeywords(episodes, summer_keywords, 'Summer')
    
    elif priority_choice == '6':
        # Prioritize True Random
        import random
        random.shuffle(episodes)
        print('🎲 Applied true random prioritization')
        return episodes
    
    return episodes

def PrioritizeByKeywords(episodes, keywords, season_name):
    """Prioritize episodes containing specific keywords."""
    prioritized = []
    regular = []
    
    for episode in episodes:
        episode_title = episode[4] if len(episode) > 4 else ""
        if not isinstance(episode_title, str):
            episode_title = str(episode_title) if episode_title is not None else ""
        
        # Check if episode contains any of the keywords
        is_prioritized = False
        for keyword in keywords:
            if keyword.lower() in episode_title.lower():
                prioritized.append(episode)
                is_prioritized = True
                break
        
        if not is_prioritized:
            regular.append(episode)
    
    # Return prioritized episodes first, then regular episodes
    result = prioritized + regular
    print(f'🎯 {season_name} prioritization: {len(prioritized)} prioritized, {len(regular)} regular')
    return result

def ConvertToPlexEpisode(episode_data):
    """Convert database episode data back to a Plex episode object."""
    try:
        show_name = episode_data[0]
        episode_id = episode_data[1]  # e.g., "s01e01"
        server_name = episode_data[6] if len(episode_data) > 6 else None
        
        if not server_name:
            print(f'⚠️  No server information for episode {show_name} - {episode_id}')
            return None
        
        # Find the server
        target_server = None
        for serv in conservs:
            if serv != ':(' and serv.friendlyName == server_name:
                target_server = serv
                break
        
        if not target_server:
            print(f'⚠️  Server {server_name} not found for episode {show_name} - {episode_id}')
            return None
        
        # Search for the show on the server
        search_results = SearchServer(target_server, show_name)
        show_items = [item for item in search_results if item.type == 'show']
        
        if not show_items:
            print(f'⚠️  Show {show_name} not found on server {server_name}')
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
            print(f'⚠️  Episode {episode_id} not found for show {show_name} on server {server_name}')
            return None
        
        print(f'✅ Converted database data to Plex episode: {show_name} - {episode_id}')
        return target_episode
        
    except Exception as e:
        print(f'❌ Error converting episode data: {str(e)}')
        return None

def FilterStats():
    print('📊 EPISODE FILTERING STATISTICS')
    print('=' * 50)
    
    try:
        # Get all shows
        shows = c.execute('''SELECT DISTINCT Show FROM shows ORDER BY Show''').fetchall()
        
        for show in shows:
            show_name = show[0]
            episodes = c.execute('''SELECT Episode, Title FROM episodes WHERE Show = ? ORDER BY Episode''', (show_name,)).fetchall()
            
            if not episodes:
                continue
                
            regular_count = 0
            holiday_count = 0
            early_simpsons_count = 0
            
            # Specific holiday keywords for filtering
            holiday_keywords = [
                'christmas', 'x-mas', 'xmas', 'holy night', 'horror', 'treehouse', 'thanksgiving', 'halloween'
            ]
            
            for episode in episodes:
                episode_id = episode[0]
                episode_title = episode[1]
                
                # Check early Simpsons
                if show_name.lower() == 'the simpsons':
                    try:
                        season_num = int(episode_id[1:3])
                        if season_num <= 2:
                            early_simpsons_count += 1
                            continue
                    except:
                        pass
                
                # Check holiday episodes (for ALL shows - keyword-based)
                is_holiday = False
                for keyword in holiday_keywords:
                    if keyword.lower() in episode_title.lower():
                        holiday_count += 1
                        is_holiday = True
                        break
                
                if not is_holiday:
                    regular_count += 1
            
            if early_simpsons_count > 0 or holiday_count > 0:
                print(f'\n🎬 {show_name}:')
                print(f'  📺 Regular episodes: {regular_count}')
                if early_simpsons_count > 0:
                    print(f'  ⚠️  Early Simpsons (S0-2): {early_simpsons_count} (pushed to back)')
                if holiday_count > 0:
                    print(f'  🎃 Holiday episodes: {holiday_count} (pushed to back)')
        
        print(f'\n📋 Filtering Rules:')
        print(f'  • Early Simpsons (S0-2): Pushed to back entirely')
        print(f'  • Holiday episodes pushed to back for ALL shows (keyword-based)')
        print(f'  • Keywords: Christmas, X-Mas, XMAS, Holy Night, Horror, Treehouse, Thanksgiving, Halloween')
        
    except Exception as e:
        print(f'❌ Error getting filter statistics: {str(e)}')

def ShuffleCollections():
    print('🎲 SHUFFLING FROM ALL COLLECTIONS')
    print('=' * 50)
    
    # Get all collections from all servers
    all_collections = []
    for serv in conservs:
        if serv != ':(':
            try:
                library = serv.library.section('TV Shows')
                collections = library.collections()
                for collection in collections:
                    all_collections.append((collection, serv))
            except Exception as e:
                print(f'  ⚠️  Could not access collections on {serv.friendlyName}: {str(e)}')
    
    if not all_collections:
        print('❌ No collections found on any server')
        return False
    
    print(f'📚 Found {len(all_collections)} collections across all servers:')
    for i, (collection, server) in enumerate(all_collections):
        print(f'  {i+1}. {collection.title} ({collection.childCount} items) - {server.friendlyName}')
    
    # Get the current collection index from a file, or start at 0
    try:
        with open('collection_index.txt', 'r') as f:
            current_index = int(f.read().strip())
    except:
        current_index = 0
    
    # Cycle to the next collection
    current_index = (current_index + 1) % len(all_collections)
    
    # Save the current index
    try:
        with open('collection_index.txt', 'w') as f:
            f.write(str(current_index))
    except:
        pass
    
    # Select the current collection
    selected_collection, selected_server = all_collections[current_index]
    print(f'\n🎯 Cycling to collection {current_index + 1}/{len(all_collections)}: {selected_collection.title}')
    print(f'🏠 From server: {selected_server.friendlyName}')
    
    # Get shows from the selected collection
    collection_shows = []
    try:
        for item in selected_collection.items():
            if item.type == 'show':
                collection_shows.append(item.title)
        print(f'📺 Found {len(collection_shows)} shows in {selected_collection.title}')
    except Exception as e:
        print(f'❌ Error accessing collection shows: {str(e)}')
        return False
    
    if not collection_shows:
        print('❌ No shows found in selected collection')
        return False
    
    # Randomly select a show from the collection
    import random
    selected_show = random.choice(collection_shows)
    print(f'🎬 Randomly selected show: {selected_show}')
    
    # Update view counts for the selected show
    print(f'📊 Updating view counts for {selected_show}...')
    ViewCountUpdate(selected_show)
    
    # Get ALL episodes from ALL shows with holiday filtering applied
    allFilteredEps = GetAllFilteredEpisodes()
    print(f'📺 Found {len(allFilteredEps)} total episodes across all shows after filtering')
    
    if not allFilteredEps:
        print('❌ No episodes found in database after filtering')
        return False
    
    # Filter to only episodes from the selected show
    showEps = [ep for ep in allFilteredEps if selected_show.lower() in ep[0].lower()]
    print(f'📺 Found {len(showEps)} episodes for {selected_show} after global filtering')
    
    if not showEps:
        print('❌ No episodes found for selected show after global filtering')
        return False
    
    # Move specials to the end
    for ep in showEps:
        if type(ep[1]) == str and ep[1].startswith('s00'):
            showEps.append(showEps.pop(showEps.index(ep)))
    
    # Find episode with lowest view count
    v = 1
    while v != len(showEps):
        if showEps[v-1][2] < showEps[v][2]:
            selected_ep = showEps[v-1]
            print(f'✅ Collection shuffle successful! Selected episode with lowest view count: {selected_ep[1]} (View count: {selected_ep[2]})')
            return selected_ep
        else:
            v += 1
    
    selected_ep = showEps[0] if showEps[0][2] == 0 else showEps[-1]
    print(f'✅ Collection shuffle successful! Selected episode: {selected_ep[1]} (View count: {selected_ep[2]})')
    return selected_ep
def RandomShow():
    # Get total number of shows available for shuffling
    total_shows = c.execute('''SELECT COUNT(DISTINCT Show) FROM shows''').fetchone()[0]
    print(f'🎲 Shuffling from {total_shows} available shows...')
    
    randShow = c.execute('''SELECT Show from shows GROUP BY Show ORDER BY RANDOM() LIMIT 1;''').fetchone()[0]
    print(f'🎯 Randomly selected: {randShow}')
    print(f'📊 Updating view counts for {randShow}...')
    
    ViewCountUpdate(randShow)
    
    showEps = c.execute('''SELECT Show, Episode, SUM(ViewCount), Season, Title, Length, Type FROM episodes WHERE Show LIKE ? GROUP BY Episode ORDER BY Episode;''',('%'+randShow+'%',)).fetchall()
    print(f'📺 Found {len(showEps)} episodes for {randShow}')
    
    # Apply episode filtering (early Simpsons reduction, holiday episode prioritization)
    showEps = FilterEpisodes(showEps, randShow)
    
    if not showEps:
        print('❌ No episodes remaining after filtering')
        return False
    
    for ep in showEps:
        if type(ep[1]) == str and ep[1].startswith('s00'):
            showEps.append(showEps.pop(showEps.index(ep)))
    
    v=1
    while v!=len(showEps):
        if showEps[v-1][2]<showEps[v][2]:
            selected_ep = showEps[v-1]
            print(f'✅ Shuffle successful! Selected episode with lowest view count: {selected_ep[1]} (View count: {selected_ep[2]})')
            return selected_ep
        else:
            v+=1
    
    selected_ep = showEps[0] if showEps[0][2]==0 else showEps[-1]
    print(f'✅ Shuffle successful! Selected episode: {selected_ep[1]} (View count: {selected_ep[2]})')
    return selected_ep
def PlayMedia(upnext):
    print(f'🎬 Searching for {upnext[0]} on available servers...')
    servers_searched = 0
    
    for serv in conservs:
        if serv != ':(':
            servers_searched += 1
            print(f'  🔍 Searching server: {serv.friendlyName}')
            
            # Try to find the show and episode
            try:
                # Search for the show
                search_results = SearchServer(serv, upnext[0])
                show_items = [item for item in search_results if item.type == 'show']
                
                if show_items:
                    print(f'    ✅ Found show "{upnext[0]}" on {serv.friendlyName}')
                    
                    # Get episodes from the show
                    for show in show_items:
                        try:
                            episodes = show.episodes()
                            print(f'    📺 Found {len(episodes)} episodes for {show.title}')
                            
                            # Look for the specific episode
                            target_episode = upnext[1]  # This is the episode identifier (e.g., "s01e01")
                            print(f'    🔍 Looking for episode: {target_episode}')
                            
                            # Show first few episodes for debugging
                            print(f'    📋 First 5 episodes available:')
                            for i, episode in enumerate(episodes[:5]):
                                print(f'      {i+1}. {episode.seasonEpisode} - {episode.title}')
                            
                            # Try exact match first
                            for episode in episodes:
                                if episode.seasonEpisode == target_episode:
                                    print(f'    ✅ Found exact match for episode {target_episode} on {serv.friendlyName} - server is receptive')
                                    return [episode]
                            
                            # Try case-insensitive match
                            for episode in episodes:
                                if episode.seasonEpisode.lower() == target_episode.lower():
                                    print(f'    ✅ Found case-insensitive match for episode {target_episode} on {serv.friendlyName} - server is receptive')
                                    return [episode]
                            
                            # Try partial match (in case of formatting differences)
                            for episode in episodes:
                                if target_episode.lower() in episode.seasonEpisode.lower() or episode.seasonEpisode.lower() in target_episode.lower():
                                    print(f'    ✅ Found partial match for episode {target_episode} (matched: {episode.seasonEpisode}) on {serv.friendlyName} - server is receptive')
                                    return [episode]
                            
                            print(f'    ⚠️  Episode {target_episode} not found in {len(episodes)} episodes')
                            
                        except Exception as e:
                            print(f'    ⚠️  Error accessing episodes for {show.title}: {str(e)}')
                            continue
                else:
                    print(f'    ⚠️  Show "{upnext[0]}" not found on {serv.friendlyName}')
                    
            except Exception as e:
                print(f'    ⚠️  Error searching server {serv.friendlyName}: {str(e)}')
                continue
    
    print(f'❌ Couldn\'t find episode on any of the {servers_searched} servers searched')
    return False

def CheckUpcomingEpisodes():
    """
    Check the next 20 upcoming episodes on the collection currently playing on the selected client.
    """
    print('📺 CHECKING UPCOMING EPISODES')
    print('=' * 40)
    
    # Step 1: Client selection
    print('📱 STEP 1: CLIENT SELECTION')
    print('=' * 30)
    
    all_clients = [x for x in myAccount.resources() if "player" in x.provides]
    if not all_clients:
        print('❌ No Plex clients found.')
        return False
    
    print('Available Plex clients:')
    for i, client in enumerate(all_clients, 1):
        status = "Online" if client.presence else "Offline"
        print(f'{i}. {client.name} ({client.platform}) - {status}')
    
    while True:
        try:
            client_choice = input(f'Select client (1-{len(all_clients)}): ').strip()
            client_index = int(client_choice) - 1
            if 0 <= client_index < len(all_clients):
                selected_client = all_clients[client_index]
                break
            else:
                print(f'❌ Invalid choice. Please enter 1-{len(all_clients)}.')
        except (ValueError, KeyboardInterrupt):
            print('❌ Invalid input or operation cancelled.')
            return False
    
    print(f'✅ Selected client: {selected_client.name} ({selected_client.platform})')
    
    # Step 2: Connect to client and get current playback info
    print('\n🔍 STEP 2: ANALYZING CURRENT PLAYBACK')
    print('=' * 40)
    
    try:
        if not selected_client.presence:
            print(f'❌ Client {selected_client.name} is offline')
            return False
        
        client_connection = selected_client.connect()
        print(f'✅ Connected to {selected_client.name}')
        
        # Get current playback info
        try:
            # Try different methods to get current playback info
            current_item = None
            
            # Method 1: Try to get current session
            try:
                sessions = client_connection.sessions()
                if sessions:
                    current_item = sessions[0]
                    print(f'🎬 Currently playing: {current_item.title}')
                else:
                    print('❌ No active sessions found')
                    return False
            except:
                pass
            
            # Method 2: Try to get current media info
            if not current_item:
                try:
                    # Try to get media info from the client
                    if hasattr(client_connection, 'media'):
                        current_item = client_connection.media
                        print(f'🎬 Currently playing: {current_item.title}')
                except:
                    pass
            
            # Method 3: Try to get current playback state
            if not current_item:
                try:
                    # Try to get playback state
                    if hasattr(client_connection, 'playbackState'):
                        state = client_connection.playbackState
                        if state and hasattr(state, 'media'):
                            current_item = state.media
                            print(f'🎬 Currently playing: {current_item.title}')
                except:
                    pass
            
            if not current_item:
                print('❌ Could not determine what is currently playing')
                print('💡 Make sure something is actively playing on the client')
                return False
            
            # Determine the show and collection
            if hasattr(current_item, 'grandparentTitle'):
                current_show = current_item.grandparentTitle
                print(f'📺 Show: {current_show}')
            elif hasattr(current_item, 'title'):
                # If it's a movie or other media type
                current_show = current_item.title
                print(f'📺 Media: {current_show}')
            else:
                print('❌ Could not determine current show')
                return False
                
        except Exception as e:
            print(f'❌ Error getting current playback info: {str(e)}')
            return False
        
    except Exception as e:
        print(f'❌ Error connecting to client: {str(e)}')
        return False
    
    # Step 3: Find the collection containing the current show
    print('\n📚 STEP 3: FINDING CURRENT COLLECTION')
    print('=' * 40)
    
    current_collection = None
    current_server = None
    
    for serv in conservs:
        if serv != ':(':
            try:
                library = serv.library.section('TV Shows')
                collections = library.collections()
                for collection in collections:
                    try:
                        for item in collection.items():
                            if item.type == 'show' and item.title == current_show:
                                current_collection = collection
                                current_server = serv
                                break
                        if current_collection:
                            break
                    except Exception as e:
                        continue
                if current_collection:
                    break
            except Exception as e:
                continue
    
    if not current_collection:
        print(f'❌ Could not find collection containing {current_show}')
        print('💡 This might happen if the show is not in a collection')
        
        # Offer to manually select a collection
        print('\n🔄 Would you like to manually select a collection?')
        print('Available collections:')
        
        all_collections = []
        for serv in conservs:
            if serv != ':(':
                try:
                    library = serv.library.section('TV Shows')
                    collections = library.collections()
                    for collection in collections:
                        all_collections.append((collection, serv))
                except Exception as e:
                    continue
        
        if not all_collections:
            print('❌ No collections available')
            return False
        
        for i, (collection, server) in enumerate(all_collections, 1):
            print(f'{i}. {collection.title} ({collection.childCount} items) - {server.friendlyName}')
        
        while True:
            try:
                choice = input(f'Select collection (1-{len(all_collections)}) or press Enter to cancel: ').strip()
                if not choice:
                    print('❌ Operation cancelled')
                    return False
                
                collection_index = int(choice) - 1
                if 0 <= collection_index < len(all_collections):
                    current_collection, current_server = all_collections[collection_index]
                    print(f'✅ Manually selected collection: {current_collection.title}')
                    break
                else:
                    print(f'❌ Invalid choice. Please enter 1-{len(all_collections)}.')
            except (ValueError, KeyboardInterrupt):
                print('❌ Invalid input or operation cancelled.')
                return False
    
    print(f'✅ Found collection: {current_collection.title}')
    print(f'🏠 Server: {current_server.friendlyName}')
    print(f'📊 Items in collection: {current_collection.childCount}')
    
    # Step 4: Get shows from the current collection
    print('\n📺 STEP 4: GETTING COLLECTION SHOWS')
    print('=' * 40)
    
    collection_shows = []
    try:
        for item in current_collection.items():
            if item.type == 'show':
                collection_shows.append(item.title)
        print(f'📺 Found {len(collection_shows)} shows in {current_collection.title}')
    except Exception as e:
        print(f'❌ Error accessing collection shows: {str(e)}')
        return False
    
    if not collection_shows:
        print('❌ No shows found in current collection')
        return False
    
    # Step 5: Update view counts and get episodes
    print('\n📊 STEP 5: UPDATING EPISODE DATA')
    print('=' * 40)
    
    print(f'📊 Updating view counts for {len(collection_shows)} shows...')
    for show in collection_shows:
        try:
            ViewCountUpdate(show)
            showDB.commit()
        except Exception as e:
            print(f'⚠️  Error updating view counts for {show}: {str(e)}')
            continue
    
    # Get episodes from the current collection
    collection_episodes = GetEpisodesFromCollection(current_collection.title)
    
    if not collection_episodes:
        print('❌ No episodes found for current collection')
        return False
    
    print(f'📺 Found {len(collection_episodes)} episodes in {current_collection.title}')
    
    # Step 6: Apply holiday filtering and sort by view count
    print('\n🎭 STEP 6: APPLYING FILTERING AND SORTING')
    print('=' * 45)
    
    # Apply holiday filtering to all episodes
    filtered_episodes = GetAllFilteredEpisodes()
    collection_filtered_episodes = [ep for ep in filtered_episodes if ep[0] in collection_shows]
    
    if not collection_filtered_episodes:
        print('❌ No episodes found after filtering')
        return False
    
    print(f'📺 Found {len(collection_filtered_episodes)} episodes after filtering')
    
    # Sort by view count (lowest first) and take next 20
    sorted_episodes = sorted(collection_filtered_episodes, key=lambda x: x[2])  # x[2] is view count
    upcoming_episodes = sorted_episodes[:20]
    
    # Step 7: Display upcoming episodes
    print('\n📋 UPCOMING 20 EPISODES')
    print('=' * 40)
    print(f'🎯 Collection: {current_collection.title}')
    print(f'🏠 Server: {current_server.friendlyName}')
    print(f'📺 Client: {selected_client.name}')
    print()
    
    for i, episode in enumerate(upcoming_episodes, 1):
        show_name = episode[0]
        episode_id = episode[1]
        episode_title = episode[4] if len(episode) > 4 else "Unknown"
        view_count = episode[2]
        episode_length = episode[5] if len(episode) > 5 else 0
        
        # Format episode length
        if episode_length:
            length_str = millisecondToHumanstr(episode_length)
        else:
            length_str = "Unknown"
        
        print(f'{i:2d}. {show_name} - {episode_id}')
        print(f'    📝 {episode_title}')
        print(f'    👁️  Views: {view_count} | ⏱️  Length: {length_str}')
        
        # Add spacing between episodes
        if i < len(upcoming_episodes):
            print()
    
    # Step 8: Summary statistics
    print('\n📊 SUMMARY STATISTICS')
    print('=' * 30)
    
    # Count episodes per show
    show_counts = {}
    for episode in upcoming_episodes:
        show_name = episode[0]
        if show_name not in show_counts:
            show_counts[show_name] = 0
        show_counts[show_name] += 1
    
    print('📺 Episodes per show:')
    for show, count in sorted(show_counts.items(), key=lambda x: x[1], reverse=True):
        print(f'  • {show}: {count} episodes')
    
    # View count statistics
    view_counts = [ep[2] for ep in upcoming_episodes]
    avg_views = sum(view_counts) / len(view_counts) if view_counts else 0
    min_views = min(view_counts) if view_counts else 0
    max_views = max(view_counts) if view_counts else 0
    
    print(f'\n👁️  View count statistics:')
    print(f'  • Average views: {avg_views:.1f}')
    print(f'  • Minimum views: {min_views}')
    print(f'  • Maximum views: {max_views}')
    
    print(f'\n✅ Upcoming episodes check complete!')
    print(f'💡 These episodes are sorted by view count (lowest first)')
    print(f'🎯 Next shuffle will likely select one of these episodes')
    
    return True

def RecursiveSystemCheck():
    """
    Comprehensive recursive check to ensure the script can handle massive amounts of video files
    and verify that all are being read properly.
    """
    print('🔍 RECURSIVE SYSTEM CHECK - MASSIVE FILE HANDLING VALIDATION')
    print('=' * 70)
    
    import time
    import psutil
    import gc
    from datetime import datetime
    
    start_time = time.time()
    initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    
    print(f'⏰ Check started at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'💾 Initial memory usage: {initial_memory:.2f} MB')
    print()
    
    # Step 1: Database integrity check
    print('🗄️  STEP 1: DATABASE INTEGRITY CHECK')
    print('=' * 40)
    
    try:
        # Check database connection
        db_test = c.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table"').fetchone()
        print(f'✅ Database connection: OK ({db_test[0]} tables found)')
        
        # Check shows table
        shows_count = c.execute('SELECT COUNT(*) FROM shows').fetchone()[0]
        print(f'📺 Shows in database: {shows_count:,}')
        
        # Check episodes table
        episodes_count = c.execute('SELECT COUNT(*) FROM episodes').fetchone()[0]
        print(f'🎬 Episodes in database: {episodes_count:,}')
        
        # Check for data integrity issues
        orphaned_episodes = c.execute('''
            SELECT COUNT(*) FROM episodes e 
            LEFT JOIN shows s ON e.Show = s.Show 
            WHERE s.Show IS NULL
        ''').fetchone()[0]
        
        if orphaned_episodes > 0:
            print(f'⚠️  Orphaned episodes found: {orphaned_episodes:,}')
        else:
            print('✅ No orphaned episodes found')
        
        # Check for duplicate episodes
        duplicate_episodes = c.execute('''
            SELECT COUNT(*) FROM (
                SELECT Show, Episode, Server, COUNT(*) as cnt
                FROM episodes 
                GROUP BY Show, Episode, Server
                HAVING cnt > 1
            )
        ''').fetchone()[0]
        
        if duplicate_episodes > 0:
            print(f'⚠️  Duplicate episodes found: {duplicate_episodes:,}')
        else:
            print('✅ No duplicate episodes found')
        
    except Exception as e:
        print(f'❌ Database check failed: {str(e)}')
        return False
    
    print()
    
    # Step 2: Server connection and collection validation
    print('🌐 STEP 2: SERVER CONNECTION AND COLLECTION VALIDATION')
    print('=' * 55)
    
    total_collections = 0
    total_shows = 0
    total_items = 0
    
    for i, serv in enumerate(conservs, 1):
        if serv == ':(':
            print(f'❌ Server {i}: Connection failed')
            continue
        
        print(f'🔍 Checking server {i}: {serv.friendlyName}')
        
        try:
            # Test server response time
            server_start = time.time()
            library = serv.library.section('TV Shows')
            server_response = time.time() - server_start
            print(f'  ⏱️  Response time: {server_response:.3f}s')
            
            # Get collections
            collections = library.collections()
            server_collections = len(collections)
            total_collections += server_collections
            print(f'  📚 Collections: {server_collections}')
            
            # Validate each collection
            server_shows = 0
            server_items = 0
            
            for j, collection in enumerate(collections, 1):
                try:
                    items = collection.items()
                    collection_items = len(items)
                    server_items += collection_items
                    
                    # Count shows in collection
                    collection_shows = sum(1 for item in items if item.type == 'show')
                    server_shows += collection_shows
                    
                    if j <= 5:  # Show first 5 collections in detail
                        print(f'    📁 {collection.title}: {collection_shows} shows, {collection_items} items')
                    
                except Exception as e:
                    print(f'    ❌ Collection {collection.title}: Error - {str(e)}')
                    continue
            
            total_shows += server_shows
            total_items += server_items
            
            print(f'  📊 Server summary: {server_shows} shows, {server_items} items')
            
        except Exception as e:
            print(f'  ❌ Server check failed: {str(e)}')
            continue
    
    print(f'\n📈 Total across all servers: {total_collections} collections, {total_shows} shows, {total_items:,} items')
    print()
    
    # Step 3: Memory and performance monitoring
    print('💾 STEP 3: MEMORY AND PERFORMANCE MONITORING')
    print('=' * 45)
    
    current_memory = psutil.Process().memory_info().rss / 1024 / 1024
    memory_increase = current_memory - initial_memory
    
    print(f'💾 Current memory usage: {current_memory:.2f} MB')
    print(f'📈 Memory increase: {memory_increase:.2f} MB')
    
    # Check system resources
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    
    print(f'🖥️  CPU usage: {cpu_percent:.1f}%')
    print(f'💾 System memory usage: {memory_percent:.1f}%')
    
    # Memory warning thresholds
    if memory_increase > 500:  # 500MB
        print('⚠️  High memory usage detected (>500MB increase)')
    elif memory_increase > 200:  # 200MB
        print('💡 Moderate memory usage detected (>200MB increase)')
    else:
        print('✅ Memory usage is within normal limits')
    
    print()
    
    # Step 4: Recursive episode processing test
    print('🔄 STEP 4: RECURSIVE EPISODE PROCESSING TEST')
    print('=' * 45)
    
    # Test with a subset of shows to avoid overwhelming the system
    test_shows = c.execute('SELECT Show FROM shows LIMIT 10').fetchall()
    
    if not test_shows:
        print('❌ No shows found for testing')
        return False
    
    print(f'🧪 Testing with {len(test_shows)} shows...')
    
    processed_episodes = 0
    successful_updates = 0
    failed_updates = 0
    
    for i, (show_name,) in enumerate(test_shows, 1):
        print(f'  [{i}/{len(test_shows)}] Testing: {show_name}')
        
        try:
            # Test view count update
            start_update = time.time()
            ViewCountUpdate(show_name)
            update_time = time.time() - start_update
            
            # Count episodes for this show
            show_episodes = c.execute('SELECT COUNT(*) FROM episodes WHERE Show = ?', (show_name,)).fetchone()[0]
            processed_episodes += show_episodes
            
            print(f'    ✅ Updated {show_episodes} episodes in {update_time:.3f}s')
            successful_updates += 1
            
        except Exception as e:
            print(f'    ❌ Failed: {str(e)}')
            failed_updates += 1
            continue
    
    print(f'\n📊 Processing test results:')
    print(f'  • Shows tested: {len(test_shows)}')
    print(f'  • Successful updates: {successful_updates}')
    print(f'  • Failed updates: {failed_updates}')
    print(f'  • Total episodes processed: {processed_episodes:,}')
    
    print()
    
    # Step 5: File access and search performance test
    print('🔍 STEP 5: FILE ACCESS AND SEARCH PERFORMANCE TEST')
    print('=' * 50)
    
    # Test search performance across servers
    search_times = []
    search_results = []
    
    for serv in conservs:
        if serv == ':(':
            continue
        
        try:
            # Test search performance
            search_start = time.time()
            results = SearchServer(serv, 'The Simpsons')  # Common show for testing
            search_time = time.time() - search_start
            
            search_times.append(search_time)
            search_results.append(len(results))
            
            print(f'🔍 {serv.friendlyName}: {len(results)} results in {search_time:.3f}s')
            
        except Exception as e:
            print(f'❌ {serv.friendlyName}: Search failed - {str(e)}')
    
    if search_times:
        avg_search_time = sum(search_times) / len(search_times)
        print(f'\n📊 Search performance:')
        print(f'  • Average search time: {avg_search_time:.3f}s')
        print(f'  • Total search results: {sum(search_results)}')
        
        if avg_search_time > 5.0:
            print('⚠️  Slow search performance detected (>5s average)')
        elif avg_search_time > 2.0:
            print('💡 Moderate search performance (>2s average)')
        else:
            print('✅ Good search performance (<2s average)')
    
    print()
    
    # Step 6: Database performance test
    print('🗄️  STEP 6: DATABASE PERFORMANCE TEST')
    print('=' * 40)
    
    # Test complex queries
    query_tests = [
        ('Simple count', 'SELECT COUNT(*) FROM episodes'),
        ('Group by show', 'SELECT Show, COUNT(*) FROM episodes GROUP BY Show LIMIT 10'),
        ('View count analysis', 'SELECT Show, AVG(ViewCount) FROM episodes GROUP BY Show LIMIT 10'),
        ('Complex join', '''
            SELECT s.Show, COUNT(e.Episode) as episode_count, AVG(e.ViewCount) as avg_views
            FROM shows s
            LEFT JOIN episodes e ON s.Show = e.Show
            GROUP BY s.Show
            LIMIT 10
        ''')
    ]
    
    for test_name, query in query_tests:
        try:
            start_time_query = time.time()
            result = c.execute(query).fetchall()
            query_time = time.time() - start_time_query
            
            print(f'  🔍 {test_name}: {len(result)} results in {query_time:.3f}s')
            
            if query_time > 1.0:
                print(f'    ⚠️  Slow query detected (>1s)')
            
        except Exception as e:
            print(f'  ❌ {test_name}: Failed - {str(e)}')
    
    print()
    
    # Step 7: Memory cleanup and final check
    print('🧹 STEP 7: MEMORY CLEANUP AND FINAL CHECK')
    print('=' * 45)
    
    # Force garbage collection
    gc.collect()
    
    final_memory = psutil.Process().memory_info().rss / 1024 / 1024
    total_memory_change = final_memory - initial_memory
    
    print(f'💾 Final memory usage: {final_memory:.2f} MB')
    print(f'📊 Total memory change: {total_memory_change:.2f} MB')
    
    # Calculate total time
    total_time = time.time() - start_time
    
    print(f'⏱️  Total check time: {total_time:.2f} seconds')
    
    # Final assessment
    print('\n📋 FINAL ASSESSMENT')
    print('=' * 25)
    
    issues_found = 0
    warnings = []
    
    # Check for critical issues
    if failed_updates > 0:
        issues_found += 1
        warnings.append(f'❌ {failed_updates} show updates failed')
    
    if orphaned_episodes > 0:
        issues_found += 1
        warnings.append(f'❌ {orphaned_episodes} orphaned episodes found')
    
    if duplicate_episodes > 0:
        issues_found += 1
        warnings.append(f'❌ {duplicate_episodes} duplicate episodes found')
    
    if total_memory_change > 1000:  # 1GB
        issues_found += 1
        warnings.append(f'❌ High memory usage: {total_memory_change:.2f} MB increase')
    
    # Check for warnings
    if total_memory_change > 500:  # 500MB
        warnings.append(f'⚠️  Moderate memory usage: {total_memory_change:.2f} MB increase')
    
    if total_time > 60:  # 1 minute
        warnings.append(f'⚠️  Slow performance: {total_time:.2f} seconds total')
    
    # Display results
    if issues_found == 0:
        print('✅ SYSTEM CHECK PASSED - All systems operational')
        print('🎯 Your massive video file collection is being handled properly!')
    else:
        print(f'⚠️  SYSTEM CHECK COMPLETED - {issues_found} issues found')
    
    if warnings:
        print('\n📋 Issues and warnings:')
        for warning in warnings:
            print(f'  {warning}')
    
    print(f'\n📊 Summary:')
    print(f'  • Total collections: {total_collections}')
    print(f'  • Total shows: {total_shows:,}')
    print(f'  • Total episodes: {episodes_count:,}')
    print(f'  • Database integrity: {"✅ Good" if orphaned_episodes == 0 and duplicate_episodes == 0 else "⚠️  Issues found"}')
    print(f'  • Memory efficiency: {"✅ Good" if total_memory_change < 500 else "⚠️  High usage"}')
    print(f'  • Performance: {"✅ Good" if total_time < 60 else "⚠️  Slow"}')
    
    print(f'\n🎉 Recursive system check complete!')
    print(f'💡 Use this check periodically to monitor system health')
    
    return True

def DetectOrphanedEpisodes():
    """
    Detect and analyze orphaned episodes in the database.
    Orphaned episodes are episodes that exist in the episodes table but don't have
    a corresponding show in the shows table.
    """
    print('🔍 ORPHANED EPISODE DETECTION')
    print('=' * 40)
    
    try:
        # Get all orphaned episodes
        orphaned_episodes = c.execute('''
            SELECT e.Show, e.Episode, e.Title, e.Server, e.ViewCount, e.Type
            FROM episodes e 
            LEFT JOIN shows s ON e.Show = s.Show 
            WHERE s.Show IS NULL
            ORDER BY e.Show, e.Episode
        ''').fetchall()
        
        if not orphaned_episodes:
            print('✅ No orphaned episodes found!')
            return []
        
        print(f'⚠️  Found {len(orphaned_episodes)} orphaned episodes')
        print()
        
        # Analyze orphaned episodes by show
        orphaned_shows = {}
        for episode in orphaned_episodes:
            show_name = episode[0]
            if show_name not in orphaned_shows:
                orphaned_shows[show_name] = []
            orphaned_shows[show_name].append(episode)
        
        print('📊 Orphaned episodes by show:')
        for show_name, episodes in orphaned_shows.items():
            print(f'  • {show_name}: {len(episodes)} episodes')
        
        print()
        print('📋 Sample orphaned episodes (first 10):')
        for i, episode in enumerate(orphaned_episodes[:10], 1):
            show_name, episode_id, title, server, view_count, episode_type = episode
            print(f'  {i:2d}. {show_name} - {episode_id} ({server}) - Views: {view_count}')
            if title:
                print(f'      Title: {title}')
        
        if len(orphaned_episodes) > 10:
            print(f'      ... and {len(orphaned_episodes) - 10} more orphaned episodes')
        
        return orphaned_episodes
        
    except Exception as e:
        print(f'❌ Error detecting orphaned episodes: {str(e)}')
        return []

def CorrectOrphanedEpisodes():
    """
    Safely correct orphaned episodes by either:
    1. Adding missing shows to the shows table
    2. Removing orphaned episodes that can't be corrected
    """
    print('🔧 ORPHANED EPISODE CORRECTION')
    print('=' * 40)
    
    # First, detect orphaned episodes
    orphaned_episodes = DetectOrphanedEpisodes()
    
    if not orphaned_episodes:
        print('✅ No orphaned episodes to correct!')
        return True
    
    print(f'\n🛠️  Starting correction process for {len(orphaned_episodes)} orphaned episodes...')
    
    # Group orphaned episodes by show
    orphaned_shows = {}
    for episode in orphaned_episodes:
        show_name = episode[0]
        if show_name not in orphaned_shows:
            orphaned_shows[show_name] = []
        orphaned_shows[show_name].append(episode)
    
    print(f'📺 Found {len(orphaned_shows)} orphaned shows to process')
    print()
    
    # Step 1: Try to find shows on servers and add them to shows table
    print('🔍 STEP 1: SEARCHING FOR ORPHANED SHOWS ON SERVERS')
    print('=' * 55)
    
    shows_found = 0
    shows_not_found = 0
    episodes_corrected = 0
    
    for show_name in orphaned_shows.keys():
        print(f'🔍 Searching for show: {show_name}')
        
        show_found_on_server = False
        
        # Search for the show on all servers
        for serv in conservs:
            if serv == ':(':
                continue
            
            try:
                search_results = SearchServer(serv, show_name)
                show_items = [item for item in search_results if item.type == 'show']
                
                if show_items:
                    print(f'  ✅ Found on {serv.friendlyName}')
                    
                    # Add the show to the shows table
                    try:
                        CallDB('''INSERT INTO shows (Show) SELECT ? WHERE NOT EXISTS(SELECT 1 FROM shows WHERE Show = ?)''', (show_name, show_name))
                        showDB.commit()
                        print(f'  ✅ Added {show_name} to shows table')
                        shows_found += 1
                        show_found_on_server = True
                        break
                        
                    except Exception as e:
                        print(f'  ❌ Error adding show to database: {str(e)}')
                        continue
                        
            except Exception as e:
                print(f'  ⚠️  Error searching {serv.friendlyName}: {str(e)}')
                continue
        
        if not show_found_on_server:
            print(f'  ❌ Not found on any server')
            shows_not_found += 1
    
    print(f'\n📊 Step 1 Results:')
    print(f'  • Shows found and added: {shows_found}')
    print(f'  • Shows not found: {shows_not_found}')
    
    # Step 2: Verify which orphaned episodes are now corrected
    print(f'\n🔍 STEP 2: VERIFYING CORRECTIONS')
    print('=' * 35)
    
    remaining_orphaned = c.execute('''
        SELECT e.Show, e.Episode, e.Title, e.Server, e.ViewCount, e.Type
        FROM episodes e 
        LEFT JOIN shows s ON e.Show = s.Show 
        WHERE s.Show IS NULL
    ''').fetchall()
    
    episodes_corrected = len(orphaned_episodes) - len(remaining_orphaned)
    
    print(f'✅ Episodes corrected: {episodes_corrected}')
    print(f'⚠️  Remaining orphaned: {len(remaining_orphaned)}')
    
    if remaining_orphaned:
        print(f'\n📋 Remaining orphaned episodes (first 10):')
        for i, episode in enumerate(remaining_orphaned[:10], 1):
            show_name, episode_id, title, server, view_count, episode_type = episode
            print(f'  {i:2d}. {show_name} - {episode_id} ({server}) - Views: {view_count}')
        
        if len(remaining_orphaned) > 10:
            print(f'      ... and {len(remaining_orphaned) - 10} more')
    
    # Step 3: Offer to remove remaining orphaned episodes
    if remaining_orphaned:
        print(f'\n⚠️  STEP 3: CLEANUP OPTIONS')
        print('=' * 30)
        print(f'There are {len(remaining_orphaned)} episodes that could not be corrected.')
        print('These episodes may be from:')
        print('  • Shows that were deleted from Plex')
        print('  • Shows that were renamed')
        print('  • Database inconsistencies')
        print()
        
        print('Options:')
        print('1. Remove all remaining orphaned episodes (recommended)')
        print('2. Keep orphaned episodes for manual review')
        print('3. Export orphaned episodes to file for backup')
        
        while True:
            try:
                choice = input('\nEnter your choice (1-3): ').strip()
                if choice in ['1', '2', '3']:
                    break
                else:
                    print('❌ Invalid choice. Please enter 1, 2, or 3.')
            except KeyboardInterrupt:
                print('\n❌ Operation cancelled.')
                return False
        
        if choice == '1':
            # Remove orphaned episodes
            print(f'\n🗑️  Removing {len(remaining_orphaned)} orphaned episodes...')
            
            try:
                c.execute('''
                    DELETE FROM episodes 
                    WHERE Show IN (
                        SELECT e.Show 
                        FROM episodes e 
                        LEFT JOIN shows s ON e.Show = s.Show 
                        WHERE s.Show IS NULL
                    )
                ''')
                showDB.commit()
                print('✅ Orphaned episodes removed successfully!')
                
            except Exception as e:
                print(f'❌ Error removing orphaned episodes: {str(e)}')
                return False
        
        elif choice == '2':
            print('✅ Orphaned episodes kept for manual review.')
            print('💡 You can run this correction again later.')
        
        elif choice == '3':
            # Export orphaned episodes to file
            print(f'\n📁 Exporting orphaned episodes to file...')
            
            try:
                with open('orphaned_episodes_backup.txt', 'w', encoding='utf-8') as f:
                    f.write('Orphaned Episodes Backup\n')
                    f.write('=' * 30 + '\n')
                    f.write(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
                    f.write(f'Total orphaned episodes: {len(remaining_orphaned)}\n\n')
                    
                    for episode in remaining_orphaned:
                        show_name, episode_id, title, server, view_count, episode_type = episode
                        f.write(f'Show: {show_name}\n')
                        f.write(f'Episode: {episode_id}\n')
                        f.write(f'Title: {title}\n')
                        f.write(f'Server: {server}\n')
                        f.write(f'View Count: {view_count}\n')
                        f.write(f'Type: {episode_type}\n')
                        f.write('-' * 40 + '\n')
                
                print('✅ Orphaned episodes exported to orphaned_episodes_backup.txt')
                
            except Exception as e:
                print(f'❌ Error exporting orphaned episodes: {str(e)}')
    
    # Final verification
    print(f'\n🔍 FINAL VERIFICATION')
    print('=' * 25)
    
    final_orphaned = c.execute('''
        SELECT COUNT(*) FROM episodes e 
        LEFT JOIN shows s ON e.Show = s.Show 
        WHERE s.Show IS NULL
    ''').fetchone()[0]
    
    if final_orphaned == 0:
        print('✅ All orphaned episodes have been corrected!')
        print('🎉 Database integrity restored.')
    else:
        print(f'⚠️  {final_orphaned} orphaned episodes remain.')
        print('💡 You may need to manually review these episodes.')
    
    return True

def DatabaseIntegrityCheck():
    """
    Comprehensive database integrity check and repair.
    """
    print('🗄️  DATABASE INTEGRITY CHECK')
    print('=' * 35)
    
    try:
        # Check for orphaned episodes
        orphaned_count = c.execute('''
            SELECT COUNT(*) FROM episodes e 
            LEFT JOIN shows s ON e.Show = s.Show 
            WHERE s.Show IS NULL
        ''').fetchone()[0]
        
        # Check for duplicate episodes
        duplicate_count = c.execute('''
            SELECT COUNT(*) FROM (
                SELECT Show, Episode, Server, COUNT(*) as cnt
                FROM episodes 
                GROUP BY Show, Episode, Server
                HAVING cnt > 1
            )
        ''').fetchone()[0]
        
        # Check for shows with no episodes
        shows_without_episodes = c.execute('''
            SELECT COUNT(*) FROM shows s
            LEFT JOIN episodes e ON s.Show = e.Show
            WHERE e.Show IS NULL
        ''').fetchone()[0]
        
        # Check for episodes with invalid data
        invalid_episodes = c.execute('''
            SELECT COUNT(*) FROM episodes 
            WHERE Show IS NULL OR Show = '' OR Episode IS NULL OR Episode = ''
        ''').fetchone()[0]
        
        print('📊 Database Integrity Analysis:')
        print(f'  • Orphaned episodes: {orphaned_count:,}')
        print(f'  • Duplicate episodes: {duplicate_count:,}')
        print(f'  • Shows without episodes: {shows_without_episodes:,}')
        print(f'  • Invalid episodes: {invalid_episodes:,}')
        
        total_issues = orphaned_count + duplicate_count + shows_without_episodes + invalid_episodes
        
        if total_issues == 0:
            print('\n✅ Database integrity is perfect!')
            return True
        else:
            print(f'\n⚠️  Found {total_issues:,} integrity issues.')
            
            # Offer to fix issues
            print('\n🔧 Would you like to attempt automatic repair?')
            print('1. Yes, fix all issues automatically')
            print('2. No, just show the issues')
            
            while True:
                try:
                    choice = input('\nEnter your choice (1-2): ').strip()
                    if choice in ['1', '2']:
                        break
                    else:
                        print('❌ Invalid choice. Please enter 1 or 2.')
                except KeyboardInterrupt:
                    print('\n❌ Operation cancelled.')
                    return False
            
            if choice == '1':
                print('\n🛠️  Starting automatic repair...')
                
                # Fix orphaned episodes
                if orphaned_count > 0:
                    print(f'\n🔧 Fixing {orphaned_count} orphaned episodes...')
                    CorrectOrphanedEpisodes()
                
                # Fix duplicate episodes (keep the one with highest view count)
                if duplicate_count > 0:
                    print(f'\n🔧 Fixing {duplicate_count} duplicate episodes...')
                    c.execute('''
                        DELETE FROM episodes 
                        WHERE rowid NOT IN (
                            SELECT MAX(rowid) 
                            FROM episodes 
                            GROUP BY Show, Episode, Server
                        )
                    ''')
                    showDB.commit()
                    print('✅ Duplicate episodes removed.')
                
                # Fix invalid episodes
                if invalid_episodes > 0:
                    print(f'\n🔧 Removing {invalid_episodes} invalid episodes...')
                    c.execute('''
                        DELETE FROM episodes 
                        WHERE Show IS NULL OR Show = '' OR Episode IS NULL OR Episode = ''
                    ''')
                    showDB.commit()
                    print('✅ Invalid episodes removed.')
                
                print('\n✅ Automatic repair completed!')
                
                # Final verification
                final_orphaned = c.execute('''
                    SELECT COUNT(*) FROM episodes e 
                    LEFT JOIN shows s ON e.Show = s.Show 
                    WHERE s.Show IS NULL
                ''').fetchone()[0]
                
                final_duplicates = c.execute('''
                    SELECT COUNT(*) FROM (
                        SELECT Show, Episode, Server, COUNT(*) as cnt
                        FROM episodes 
                        GROUP BY Show, Episode, Server
                        HAVING cnt > 1
                    )
                ''').fetchone()[0]
                
                print(f'\n📊 Final status:')
                print(f'  • Remaining orphaned episodes: {final_orphaned}')
                print(f'  • Remaining duplicates: {final_duplicates}')
                
            return True
            
    except Exception as e:
        print(f'❌ Error during database integrity check: {str(e)}')
        return False

print('Welcome to the Plex Queue Shuffle!')
startime = datetime.now()
print('Connecting to your servers real quick...')
conservs = [ServerConnect(server) for server in config.servers]
print('Servers Connected!')
print('Connecting to your client real quick...')
plextv_clients = [x for x in myAccount.resources() if "player" in x.provides and x.presence and x.publicAddressMatches]
if plextv_clients:
    client = plextv_clients[0].connect()
    print('Client Connected!')
else:
    # Try to find any available clients, even if not currently online
    all_clients = [x for x in myAccount.resources() if "player" in x.provides]
    online_clients = [x for x in all_clients if x.presence]
    if all_clients:
        if online_clients:
            print(f'Found {len(all_clients)} client(s), {len(online_clients)} are online:')
            for i, cl in enumerate(all_clients):
                status = "Online" if cl.presence else "Offline"
                print(f'  {i+1}. {cl.name} ({cl.platform}) - {status}')
            print('\nTrying to connect to the first online client...')
            try:
                client = online_clients[0].connect()
                print('Client Connected!')
            except:
                print('Failed to connect to client. You can still use the script to manage your library.')
                client = None
        else:
            print(f'Found {len(all_clients)} client(s) but none are currently online:')
            for i, cl in enumerate(all_clients):
                print(f'  {i+1}. {cl.name} ({cl.platform}) - Offline')
            print('\nTo use a client, make sure it\'s running and online.')
            client = None
    else:
        print('No Plex clients found. You can still use the script to manage your library.')
        client = None
endtime = datetime.now()
print(f'Startup done! Time elapsed: {round(((endtime-startime).seconds)/60,2)} minutes')

while True:
    Welcome()
    command = input('> ')
    if command.lower() == 'help':
        CommandsInfo()
    elif command.lower() == 'create':
        startime = datetime.now()
        CallDB(''' DROP TABLE IF EXISTS shows''')
        CallDB(''' DROP TABLE IF EXISTS episodes''')
        CallDB('''CREATE TABLE episodes
        (ID int, Type TEXT, Show TEXT, Season TEXT, Episode TEXT, Title TEXT, Server TEXT, ViewCount INT, Length INT)''')
        CallDB('''CREATE TABLE shows
        (Type TEXT, Show TEXT)''')
        for serv in conservs:
            if serv != ':(':
                ShowsIFollow(ShowsPerServer(serv))
            showDB.commit()
        endtime = datetime.now()
        print(f'DB created! Time elapsed: {round(((endtime-startime).seconds)/60,2)} minutes')
    elif command.lower() == 'update':
        ProvideMilk()
        startime = datetime.now()
        showlist = CallDB('''SELECT Show FROM shows''')
        for show in showlist:
            print(f'Searching for {show[0]} on...')
            ViewCountUpdate(show[0])
            showDB.commit()
        endtime = datetime.now()
        print(f'DB updated! Time elapsed: {round(((endtime-startime).seconds)/60,2)} minutes')
    elif command.lower() == 'collections':
        ListCollections()
    elif command.lower() == 'clients':
        ListClients()
    elif command.lower() == 'shuffle-collections':
        if client is None:
            print('❌ No Plex client available. Please ensure a Plex client is online and try again.')
            continue
        
        print('🎲 Starting collection shuffle process...')
        upnext = ShuffleCollections()
        
        if upnext:
            epS = PlayMedia(upnext)
            if epS:
                PlayInfo(epS[0])
                print(f'🎮 Connecting to {plextv_clients[0].name} on {plextv_clients[0].platform}, {plextv_clients[0].device} using {plextv_clients[0].product}...')
                client.playMedia(epS[0])
                print('🎉 COLLECTION SHUFFLE COMPLETE! Episode is now playing on your Plex client.')
                print('📊 Summary: Collections shuffled ✓ | Server receptive ✓ | Episode queued ✓')
            else:
                print('❌ Could not find episode on any server')
        else:
            print('❌ Collection shuffle failed')
    elif command.lower() == 'debug-episodes':
        DebugEpisodes()
    elif command.lower() == 'filter-stats':
        FilterStats()
    elif command.lower() == 'collection-holiday-wash':
        print('🧹 Starting comprehensive holiday episode cleaning...')
        print('⚠️  This may take a while as it processes all shows and episodes.')
        print('💡 Make sure you have a stable connection to your Plex servers.')
        print()
        
        startime = datetime.now()
        success = CollectionHolidayWash()
        endtime = datetime.now()
        
        if success:
            print(f'⏱️  Holiday wash completed in {round(((endtime-startime).seconds)/60,2)} minutes')
        else:
            print('❌ Holiday wash failed')
    elif command.lower() == 'tv-lineup':
        print('📺 Starting balanced TV lineup creation...')
        print('🎯 This will create a lineup ensuring no more than 2 episodes of the same show play consecutively.')
        print()
        
        startime = datetime.now()
        lineup = TVLineup()
        endtime = datetime.now()
        
        if lineup:
            print(f'⏱️  TV lineup created in {round(((endtime-startime).seconds)/60,2)} minutes')
            print('💡 The lineup has been saved and can be used for balanced shuffling!')
        else:
            print('❌ TV lineup creation failed')
    elif command.lower() == 'animation-domination':
        print('🎬 Starting Animation Domination lineup creation...')
        print('🎯 This will create a specific lineup for Adult Swim Ultra with the exact pattern you specified.')
        print()
        
        startime = datetime.now()
        lineup = AnimationDomination()
        endtime = datetime.now()
        
        if lineup:
            print(f'⏱️  Animation Domination lineup created in {round(((endtime-startime).seconds)/60,2)} minutes')
            print('💡 The lineup has been saved and follows the exact pattern!')
        else:
            print('❌ Animation Domination lineup creation failed')
    elif command.lower() == 'super-shuffle':
        print('🚀 Starting Super Shuffle system...')
        print('🎯 This comprehensive system will process all collections and provide multiple options.')
        print('⚠️  This may take a while as it processes everything.')
        print()
        
        startime = datetime.now()
        success = SuperShuffle()
        endtime = datetime.now()
        
        if success:
            print(f'⏱️  Super Shuffle completed in {round(((endtime-startime).seconds)/60,2)} minutes')
        else:
            print('❌ Super Shuffle failed')
    elif command.lower() == 'collection-status':
        print('📊 Checking current collection status...')
        ShowCurrentCollectionStatus()
    elif command.lower() == 'reset-collections':
        print('🔄 Resetting collection index...')
        ResetCollectionIndex()
    elif command.lower() == 'upcoming':
        print('📺 Checking upcoming episodes...')
        CheckUpcomingEpisodes()
    elif command.lower() == 'system-check':
        print('🔍 Starting comprehensive system check...')
        print('⚠️  This may take several minutes to complete.')
        RecursiveSystemCheck()
    elif command.lower() == 'detect-orphans':
        print('🔍 Detecting orphaned episodes...')
        DetectOrphanedEpisodes()
    elif command.lower() == 'fix-orphans':
        print('🔧 Fixing orphaned episodes...')
        print('⚠️  This will modify the database. Make sure you have a backup.')
        CorrectOrphanedEpisodes()
    elif command.lower() == 'db-integrity':
        print('🗄️  Running database integrity check...')
        DatabaseIntegrityCheck()
    elif command == '':
        print('❌ Random show selection has been disabled.')
        print('💡 Use "shuffle-collections" to shuffle from collections instead.')
        print('💡 Or type "help" to see all available commands.')
    elif command.lower() in ['exit', 'quit']:
        break
    else:
        input('Invalid command. Press enter to continue.')
        continue
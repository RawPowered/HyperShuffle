from plexapi.myplex import MyPlexAccount
import config, sqlite3

def run_diagnostics():
    print("🔍 PLEX SHUFFLE DIAGNOSTIC TOOL")
    print("=" * 50)
    
    # Test 1: Account Connection
    print("\n1. Testing Plex Account Connection...")
    try:
        myAccount = MyPlexAccount(config.username, config.password)
        print("   ✅ Plex account connection successful")
    except Exception as e:
        print(f"   ❌ Plex account connection failed: {str(e)}")
        return
    
    # Test 2: Server Connection
    print("\n2. Testing Server Connection...")
    try:
        server = myAccount.resource(config.servers[0]).connect()
        print(f"   ✅ Server '{config.servers[0]}' connection successful")
        print(f"   📊 Server friendly name: {server.friendlyName}")
    except Exception as e:
        print(f"   ❌ Server connection failed: {str(e)}")
        return
    
    # Test 3: Database Check
    print("\n3. Testing Database...")
    try:
        showDB = sqlite3.connect('myShows.db')
        c = showDB.cursor()
        
        # Check if tables exist
        tables = c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        print(f"   📊 Found {len(tables)} tables: {[t[0] for t in tables]}")
        
        if 'shows' in [t[0] for t in tables]:
            show_count = c.execute("SELECT COUNT(*) FROM shows").fetchone()[0]
            print(f"   📺 Shows in database: {show_count}")
            
            if show_count > 0:
                sample_shows = c.execute("SELECT Show FROM shows LIMIT 5").fetchall()
                print(f"   📋 Sample shows: {[s[0] for s in sample_shows]}")
            else:
                print("   ⚠️  No shows in database - run 'create' command first")
        else:
            print("   ❌ 'shows' table not found - run 'create' command first")
            
        if 'episodes' in [t[0] for t in tables]:
            episode_count = c.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            print(f"   🎬 Episodes in database: {episode_count}")
        else:
            print("   ❌ 'episodes' table not found - run 'create' command first")
            
    except Exception as e:
        print(f"   ❌ Database check failed: {str(e)}")
    
    # Test 4: Collections Access
    print("\n4. Testing Collections Access...")
    try:
        collections = server.collections()
        print(f"   ✅ Found {len(collections)} collections via direct method")
        for coll in collections[:3]:  # Show first 3
            print(f"      - {coll.title} ({coll.childCount} items)")
    except Exception as e:
        print(f"   ⚠️  Direct collections access failed: {str(e)}")
        try:
            library = server.library.section('TV Shows')
            collections = library.collections()
            print(f"   ✅ Found {len(collections)} collections via library method")
        except Exception as e2:
            print(f"   ❌ Library collections access also failed: {str(e2)}")
    
    # Test 5: Playlists Access
    print("\n5. Testing Playlists Access...")
    try:
        playlists = server.playlists()
        print(f"   ✅ Found {len(playlists)} playlists")
        for pl in playlists[:3]:  # Show first 3
            print(f"      - {pl.title} ({len(pl.items())} items)")
    except Exception as e:
        print(f"   ❌ Playlists access failed: {str(e)}")
    
    # Test 6: Client Access
    print("\n6. Testing Client Access...")
    try:
        all_clients = [x for x in myAccount.resources() if "player" in x.provides]
        online_clients = [x for x in all_clients if x.presence]
        print(f"   📱 Total clients: {len(all_clients)}")
        print(f"   🟢 Online clients: {len(online_clients)}")
        
        for i, cl in enumerate(all_clients):
            status = "🟢 Online" if cl.presence else "🔴 Offline"
            print(f"      {i+1}. {cl.name} ({cl.platform}) - {status}")
            
        if online_clients:
            try:
                test_client = online_clients[0].connect()
                print(f"   ✅ Successfully connected to {online_clients[0].name}")
            except Exception as e:
                print(f"   ❌ Failed to connect to client: {str(e)}")
        else:
            print("   ⚠️  No online clients available")
            
    except Exception as e:
        print(f"   ❌ Client access failed: {str(e)}")
    
    # Test 7: Search Functionality
    print("\n7. Testing Search Functionality...")
    try:
        search_results = server.search('Family Guy')
        print(f"   ✅ Search successful - found {len(search_results)} results")
        for result in search_results[:3]:
            print(f"      - {result.title} (type: {result.type})")
    except Exception as e:
        print(f"   ❌ Search failed: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🔍 DIAGNOSTIC COMPLETE")
    print("\nNext steps:")
    print("1. If database is empty, run 'create' command")
    print("2. If collections not found, try 'collections' command")
    print("3. If client not connected, ensure Plex client is online")
    print("4. If all tests pass, try the shuffle again")

if __name__ == "__main__":
    run_diagnostics() 
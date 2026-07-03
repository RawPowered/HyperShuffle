# HyperShuffle - Advanced Plex Collection Shuffling System

A refined and enhanced version of TrueShuffle with **super-shuffle as the default mode**, featuring a beautiful interface and comprehensive customization options.

## 🎬 What is HyperShuffle?

HyperShuffle is an advanced Plex media shuffling system that takes the powerful collection-based shuffling from TrueShuffle and enhances it with:

- **Beautiful, color-coded interface** for an excellent user experience
- **Super-shuffle as default mode** - no need to remember complex commands
- **Comprehensive configuration options** for fine-tuning your experience
- **Advanced holiday episode filtering** with multiple seasonal options
- **Multi-server support** across all your Plex servers
- **Intelligent collection cycling** with automatic progression

## ✨ Key Features

### 🎯 **Super-Shuffle Default Mode**
- Collection-based shuffling is the primary operation
- Automatic cycling through collections systematically
- View count priority to play unwatched content first
- Holiday episode filtering to push seasonal content back

### 🎨 **Beautiful Interface**
- Color-coded output for easy reading
- Unicode emojis and symbols for visual appeal
- Structured information display with borders and formatting
- Cross-platform compatibility with colorama

### ⚙️ **Comprehensive Configuration**
- **Prioritization Modes**: 9 different options including holiday-specific and random
- **Auto-cycling**: Automatic progression through collections
- **Client Selection**: Auto-select or manual client choice
- **Display Options**: Detailed episode information and confirmation prompts
- **Performance Settings**: View count updates and cycle delays

### 🎄 **Advanced Holiday Filtering**
- **Halloween**: horror, spooky, ghost, witch, vampire, monster
- **Thanksgiving**: turkey, pilgrim, harvest, feast, gratitude
- **Christmas**: christmas, santa, elf, reindeer, snowman
- **Summer**: beach, vacation, hot, sun, pool, barbecue
- **Valentine's**: love, romance, heart, cupid
- **Easter**: bunny, egg, spring, resurrection
- **New Year**: celebration, fireworks, resolution

### 🌐 **Multi-Server Support**
- Works across all your Plex servers simultaneously
- Automatic server discovery and connection
- Cross-server episode selection and playback
- Unified view count tracking

## 🚀 Installation

### Prerequisites
- Python 3.7 or higher
- Plex Media Server with collections set up
- Plex account with access to your servers

### Quick Installation
1. **Clone or download** this repository
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure your Plex credentials** in `config.py`:
   ```python
   username = "your_plex_username"
   password = "your_plex_password"
   servers = ["your_server_name"]
   ```

### Manual Installation
```bash
# Install required packages
pip install plexapi>=4.15.0
pip install psutil>=5.9.0
pip install colorama>=0.4.6
```

## 🎮 Usage

### Starting HyperShuffle
```bash
python HyperShuffle.py
```

### Main Commands

#### **Default Super-Shuffle Mode**
```bash
HyperShuffle> shuffle    # Execute super-shuffle (default)
HyperShuffle> s          # Short command
HyperShuffle>            # Just press Enter for default
```

#### **Collection Management**
```bash
HyperShuffle> collections    # List all available collections
HyperShuffle> c             # Short command
```

#### **Configuration**
```bash
HyperShuffle> config        # Access configuration menu
HyperShuffle> settings      # Alternative command
```

#### **System Information**
```bash
HyperShuffle> status        # Show system status
HyperShuffle> st           # Short command
HyperShuffle> check        # Check system health
HyperShuffle> help         # Show help information
HyperShuffle> clients      # List available clients
```

#### **System Control**
```bash
HyperShuffle> reset         # Reset collection index
HyperShuffle> quit          # Exit HyperShuffle
HyperShuffle> exit          # Alternative exit command
```

## ⚙️ Configuration Options

### **Prioritization Modes**
1. **Push Holiday Episodes Back** (Default) - Regular episodes first
2. **Prioritize Halloween Episodes** - Spooky content first
3. **Prioritize Thanksgiving Episodes** - Turkey day content first
4. **Prioritize Christmas Episodes** - Holiday content first
5. **Prioritize Summer Episodes** - Beach/vacation content first
6. **Prioritize Valentine's Episodes** - Romantic content first
7. **Prioritize Easter Episodes** - Spring content first
8. **Prioritize New Year Episodes** - Celebration content first
9. **True Random Shuffle** - Completely random selection

### **System Settings**
- **Auto-cycle collections**: Automatically progress to next collection
- **Holiday episode filtering**: Enable/disable holiday content filtering
- **View count priority**: Prioritize unwatched content
- **Balanced TV lineup**: Ensure variety in show selection
- **Animation domination mode**: Special mode for animation collections
- **Auto client selection**: Automatically select available client
- **Show detailed info**: Display comprehensive episode information
- **Confirm plays**: Ask for confirmation before playing
- **Update view counts**: Refresh view counts before selection
- **Skip updates when busy**: Skip database updates when clients are active
- **Max consecutive same show**: Limit consecutive episodes from same show
- **Collection cycle delay**: Delay between collection switches
- **Database retry attempts**: Number of retries for database operations
- **Client retry attempts**: Number of retries for client operations
- **Client timeout**: Timeout for client operations (seconds)

## 🎯 How It Works

### **1. Collection Analysis**
- Discovers all collections across your Plex servers
- Tracks current collection position
- Displays collection information and statistics

### **2. Episode Selection**
- Retrieves episodes from the current collection
- Updates view counts from all servers
- Applies selected prioritization mode
- Selects episode with lowest view count

### **3. Client Management**
- Discovers available Plex clients
- Connects to selected client
- Handles offline/online status

### **4. Playback**
- Converts database data to Plex episode objects
- Displays detailed episode information
- Plays episode on selected client
- Updates collection index for next cycle

## 🎨 Interface Examples

### **Beautiful Banner**
```
╔══════════════════════════════════════════════════════════════╗
║                    🎬 HYPER SHUFFLE 🎬                        ║
║              Advanced Plex Collection Shuffling System       ║
║                    Super-Shuffle Default Mode                ║
╚══════════════════════════════════════════════════════════════╝
```

### **Collection Display**
```
📚 Available Collections (5 total):
╔══════════════════════════════════════════════════════════════╗
║  1. Comedy Shows                    (45 items) - MyServer    🎯 CURRENT
║  2. Action Series                   (32 items) - MyServer    
║  3. Drama Collection                (28 items) - MyServer    
║  4. Animation Ultra                 (67 items) - MyServer    
║  5. Documentary Series              (23 items) - MyServer    
╚══════════════════════════════════════════════════════════════╝
```

### **Episode Information**
```
📺 Episode Information:
╔══════════════════════════════════════════════════════════════╗
║ Show:     The Office
║ Episode:  s03e15
║ Season:   Season 3
║ Title:    Business School
║ Views:    2
║ Type:     episode
║ Server:   MyServer
║ Length:   00:22:15
╚══════════════════════════════════════════════════════════════╝
```

## 🔧 Advanced Features

### **Database Integration**
- Uses existing TrueShuffle database (`myShows.db`)
- Compatible with TrueShuffle1.py database structure
- Automatic view count synchronization
- Cross-server episode tracking

### **Error Handling**
- Graceful connection failures
- Client availability checking
- Database integrity validation
- Comprehensive error messages

### **Performance Optimization**
- Efficient collection processing
- Minimal server API calls
- Smart caching of collection data
- Memory-efficient episode handling

### **Concurrent Usage Support**
- **Database retry logic**: Handles database locks gracefully
- **Client retry logic**: Manages busy clients with retry attempts
- **Smart update skipping**: Skips view count updates when database is busy
- **Connection timeout handling**: Configurable timeouts for client operations
- **System health monitoring**: Built-in health check command
- **Graceful degradation**: Continues operation even with partial failures

## 🆚 Comparison with TrueShuffle

| Feature | TrueShuffle | HyperShuffle |
|---------|-------------|--------------|
| **Default Mode** | Basic shuffle | Super-shuffle |
| **Interface** | Text-based | Color-coded, beautiful |
| **Configuration** | Limited | Comprehensive menu |
| **Holiday Filtering** | Basic | Advanced (7 holidays) |
| **Client Selection** | Auto-only | Auto + manual |
| **Collection Display** | None | Beautiful listing |
| **Episode Info** | Basic | Detailed with formatting |
| **Error Handling** | Basic | Comprehensive |
| **User Experience** | Functional | Polished |

## 🛠️ Troubleshooting

### **Common Issues**

#### **"No collections found"**
- Ensure you have collections set up in Plex
- Check that collections contain TV shows
- Verify server access permissions

#### **"No available clients"**
- Make sure Plex clients are online
- Check network connectivity
- Verify client discovery settings

#### **"Configuration error"**
- Ensure `config.py` exists and is properly formatted
- Check username, password, and server names
- Verify Plex account credentials

#### **"Database error"**
- Run TrueShuffle1.py first to create database
- Check file permissions for `myShows.db`
- Ensure sufficient disk space

### **Concurrent Usage Issues**

#### **"Database is locked" errors**
- Enable "Skip updates when busy" in configuration
- Increase "Database retry attempts" setting
- Run `check` command to monitor system health
- Consider running during low-usage periods

#### **"Read timed out" or "Client busy" errors**
- Increase "Client retry attempts" setting
- Increase "Client timeout" setting
- Check if client is actively playing content
- Use `check` command to test client responsiveness

#### **Performance with active clients**
- Use `check` command regularly to monitor system health
- Enable "Skip updates when busy" for better performance
- Consider running HyperShuffle during off-peak hours
- Monitor client status before initiating playback

### **Performance Tips**
1. **Regular database updates**: Use TrueShuffle1.py to update episode data
2. **Collection organization**: Keep collections focused and well-organized
3. **Network optimization**: Ensure stable connection to Plex servers
4. **Client selection**: Choose the most responsive client for playback
5. **Concurrent usage**: Enable "Skip updates when busy" for better performance
6. **Client monitoring**: Use `check` command to monitor client status
7. **Timing**: Run during low-usage periods for optimal performance

## 🤝 Contributing

### **Development Setup**
1. Fork the repository
2. Install development dependencies
3. Create feature branch
4. Test with various collection configurations
5. Submit pull request

### **Testing**
- Test with different collection sizes
- Verify holiday filtering accuracy
- Check client compatibility
- Validate error handling scenarios

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

### **Getting Help**
1. Check the troubleshooting section
2. Run `status` command for system diagnostics
3. Review error messages and logs
4. Check Plex server status

### **Reporting Issues**
- Include system status output
- Provide error messages
- Describe steps to reproduce
- Include collection and library information

---

**🎉 Enjoy your enhanced Plex shuffling experience with HyperShuffle!**

For more information about the original TrueShuffle project, visit:
https://github.com/pastram-i/plex-trueshuffle 
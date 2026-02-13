# Creating a Windows Release

## Building the Executable

1. Make sure all dependencies are installed:
   ```bash
   pip install pyinstaller
   ```

2. Run the build script:
   ```bash
   build_exe.bat
   ```
   
   This creates:
   - `dist/ChessExplorer.exe` - The standalone executable
   - `dist/ChessExplorer_Release/` - Ready-to-distribute folder

## What's Included

The `ChessExplorer_Release` folder contains:
- `ChessExplorer.exe` - The main application (~35-40 MB)
- `README.txt` - User instructions (from EXECUTABLE_README.txt)
- `games/` - Empty folder where user data will be stored

## Testing Before Release

Test the executable locally:
```bash
cd dist\ChessExplorer_Release
ChessExplorer.exe
```

The browser should auto-open to http://localhost:8000. Try:
1. Importing a small chess.com account
2. Exploring the moves
3. Applying filters
4. Using keyboard shortcuts (F to flip, arrows to navigate)

## Creating a Release Package

1. Right-click `dist\ChessExplorer_Release` → Send to → Compressed (zipped) folder
2. Rename to `ChessExplorer-v1.0-Windows.zip`
3. Upload to GitHub Releases

## GitHub Release Instructions

1. Go to your repository on GitHub
2. Click "Releases" → "Draft a new release"
3. Create a new tag: `v1.0` (or whatever version)
4. Release title: "Chess Explorer v1.0 - Windows Executable"
5. Description example:

```markdown
## 🎉 First Windows Release!

A simple chess opening explorer for your chess.com games - **no Python installation required!**

### Quick Start
1. Download `ChessExplorer-v1.0-Windows.zip`
2. Extract the zip file
3. Double-click `ChessExplorer.exe`
4. Import your chess.com games and start exploring!

### Features
- 🌐 Modern web interface with interactive board
- 📥 Import games directly from chess.com
- 🎯 Multi-player support
- 🔍 Advanced filtering (time control, dates, ratings, etc.)
- ⚡ Fast performance with smart caching
- 🎮 Keyboard shortcuts (arrows to navigate, F to flip board)

### Requirements
- Windows 10/11 (64-bit)
- Internet connection (for importing games)
- ~100 MB disk space

### Known Issues
- Windows Defender may show a warning on first run (this is normal for unsigned executables)
- Click "More info" → "Run anyway" if prompted

### For Developers
See the main README.md for Python installation and development setup.
```

6. Attach `ChessExplorer-v1.0-Windows.zip`
7. Click "Publish release"

## Posting to Reddit

**r/chess** (best audience):
```
Title: I made a free chess opening explorer for your chess.com games [Windows]

Body:
I built a simple tool to explore your chess openings from your chess.com games. 
It's completely local - your data stays on your computer.

Features:
- Import all your chess.com games with one click
- Interactive board to explore your opening repertoire
- See win/draw/loss statistics for each move
- Filter by time control, color, date ranges, etc.
- Support for multiple players

Download: [link to GitHub releases]

It's open source on GitHub: [link]

Feedback welcome!
```

**r/chessbeginners**:
- Similar to above but emphasize "learning your opening mistakes"
- Maybe include a screenshot showing the win rates

**r/programming** (if you want developer feedback):
- Focus on technical aspects (trie data structures, caching, performance)
- Link to the source code primarily

## Tips for Reddit Post

1. **Include screenshots** - Show the UI in action
2. **Be clear it's Windows-only** (for now) in the title
3. **Mention it's free** to get more attention
4. **Respond to comments quickly** in the first hour
5. **Post at peak times** (morning or early afternoon US time)
6. **Don't over-promote** - focus on the value it provides

## Future Improvements

Consider for v2.0:
- Mac/Linux executables
- Installer (instead of just zip file)
- Code signing (removes Windows Defender warnings)
- Auto-updater
- Opening name detection
- Position search
- Web-hosted version (no download needed)

## Size Optimization (Optional)

Current size is ~35-40 MB. To reduce:
1. Exclude unnecessary packages in ChessExplorer.spec
2. Use UPX compression (already enabled)
3. Remove development dependencies

The size is reasonable for a chess tool - don't over-optimize initially.

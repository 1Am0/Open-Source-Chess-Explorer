# Chess Explorer - Windows Executable

A simple chess opening explorer for your chess.com games!

## Quick Start

### First Time Setup

1. **Double-click `ChessExplorer.exe`** - This will start the program and open your browser automatically

2. **Import Your Games:**
   - In the web interface, click the hamburger menu (☰) at the top
   - Enter your chess.com username in the "Import Player" field
   - Click "Import Games" and wait for it to complete
   - Your games will be saved for next time!

3. **Explore Your Openings:**
   - Select your player from the dropdown (or "All players" to see all imported games)
   - Apply any filters you want (color, time control, date ranges, etc.)
   - Click moves on the left to explore your opening tree
   - See win/draw/loss statistics for each move!

### Every Time After

- Just double-click `ChessExplorer.exe`
- Your browser will open automatically at http://localhost:8000
- All your previously imported games are ready to explore!

### Keyboard Shortcuts

- **Arrow Keys** - Navigate through move history (←/→) or jump to start/end (↑/↓)
- **F** - Flip the board to view from Black's perspective

### Importing More Players

You can import multiple chess.com players and combine their games:
1. Click the hamburger menu
2. Enter another username
3. Click "Import Games"
4. Use the player dropdown to select specific players or "All players"

### Troubleshooting

**Nothing happens when I click Import:**
- Make sure you have an internet connection
- Check that the username is spelled correctly
- If it takes a while, that's normal - importing thousands of games can take 10-30 seconds

**The program closes immediately:**
- You may need to allow it through Windows Firewall
- Try right-click → "Run as administrator"

**I want to import from command line:**
- Open Command Prompt in this folder
- Run: `ChessExplorer.exe chess-explore-import your_username --player your_username`

### Where Are My Games Stored?

Games are saved in the `games/` folder next to the executable as `<username>.json` files. You can back these up or share them!

## What Can I Do With This?

- **Learn your repertoire** - See which openings you play most
- **Find weak spots** - Identify moves where you lose more often
- **Track improvement** - Filter by date to see how your openings evolved
- **Prepare for opponents** - Import opponent's games to study their style
- **Multi-player analysis** - Combine games from multiple players to see team/club patterns

## Need Help?

- GitHub: https://github.com/yourusername/Open-Source-Chess-Explorer
- Reddit: Post on r/chess with questions
- Issues: Report bugs on GitHub Issues page

Enjoy exploring your chess games! ♟️

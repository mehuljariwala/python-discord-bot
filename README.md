# Discord TTS Audiobook Bot

A Discord bot that reads books aloud in voice channels using Piper TTS. Built with Python and containerized with Podman/Docker.

## Features

- **File Upload Support**: Upload and read `.txt`, `.pdf`, and `.epub` files
- **Text-to-Speech**: Uses Piper TTS engine for high-quality speech synthesis
- **Voice Channel Playback**: Plays audio directly in Discord voice channels
- **State Management**: Save and resume reading progress with JSON-based storage
- **Web Scraping**: Extract and read text from web pages
- **Sentence-by-Sentence Processing**: Real-time audio generation and playback

## Commands

- `/read <attachment>` - Upload a file (txt/pdf/epub) and start reading it aloud
- `/scrape <url>` - Scrape text from a URL and read it aloud
- `/stop` - Stop playback and save your progress
- `/resume` - Resume from your last saved position

## Setup

### Prerequisites

- Docker or Podman
- Discord Bot Token (get one from [Discord Developer Portal](https://discord.com/developers/applications))

### Environment Variables

Set your Discord bot token:
```bash
export BOT_TOKEN="your_discord_bot_token_here"
```

### Build and Run with Docker

```bash
# Build the container
docker build -f Containerfile -t discord-tts-bot .

# Run the container
docker run -e BOT_TOKEN="${BOT_TOKEN}" discord-tts-bot
```

### Build and Run with Podman

```bash
# Build the container
podman build -f Containerfile -t discord-tts-bot .

# Run the container
podman run -e BOT_TOKEN="${BOT_TOKEN}" discord-tts-bot
```

## Project Structure

```
.
├── main.py              # Main bot application
├── requirements.txt     # Python dependencies
├── Containerfile        # Container build instructions
└── README.md           # This file
```

## Dependencies

- **discord.py** - Discord API wrapper
- **beautifulsoup4** - HTML/XML parsing for web scraping
- **requests** - HTTP library for web requests
- **PyPDF2** - PDF text extraction
- **EbookLib** - EPUB file parsing
- **Piper TTS** - Text-to-speech engine
- **FFmpeg** - Audio processing (installed via apt)

## How It Works

1. **File Processing**: When you upload a file, the bot extracts text based on file type
2. **Text Splitting**: Text is split into sentences for manageable TTS chunks
3. **Audio Generation**: Each sentence is converted to speech using Piper
4. **Playback**: Audio is played in your voice channel while the next sentence is being processed
5. **State Saving**: Your progress (sentence number) is saved to `db.json` when you stop

## Technical Details

- **Multi-stage Build**: Uses Alpine Linux to download Piper, then copies to slim Python image
- **Async Processing**: Leverages asyncio for concurrent audio generation and playback
- **Voice Model**: Uses en_US-lessac-medium voice from Piper
- **State Storage**: JSON-based file storage for user progress tracking

## Known Limitations

- Currently supports single-page web scraping (no automatic chapter navigation)
- One save state per user (not multiple slots)
- Simple sentence splitting (may not handle all edge cases)
- No reading time estimation yet

## Error Encountered During Development

The original implementation failed with:
```
TypeError: BotBase.__init__() missing 1 required keyword-only argument: 'intents'
```

**Fix Applied**: Added proper Discord intents initialization:
```python
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
```

## Future Enhancements

- Automatic chapter navigation for web scraping
- Multiple save slots (3 per user)
- Reading time estimation
- Better text filtering (ignore credits, chapter lists, etc.)
- Line-by-line TTS with real-time processing
- SQLite database for better state management

## License

This project was created as part of a Discord bot development demonstration.


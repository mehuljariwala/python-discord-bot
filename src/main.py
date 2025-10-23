import discord
from discord.ext import commands
import os
import asyncio
import json
from bs4 import BeautifulSoup
import requests
import PyPDF2
from ebooklib import epub
import io

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# --- State Management ---
DB_FILE = "db.json"
# This will hold the current state of the bot, e.g., the text being read
current_state = {}

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

# --- TTS ---
async def text_to_speech_async(text, output_file):
    voice_path = "en_US-lessac-medium.onnx"
    command = f'piper --model {voice_path} --output_file {output_file}'
    
    process = await asyncio.create_subprocess_shell(
        command,
        stdin=asyncio.subprocess.PIPE
    )
    
    await process.communicate(input=text.encode('utf-8'))

# --- Text Processing ---
def split_into_sentences(text):
    # A simple sentence splitter
    return [sentence.strip() for sentence in text.replace('\n', ' ').split('.') if sentence]

# --- Core Player Task ---
async def play_text(ctx):
    global current_state
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    while current_state.get("current_sentence", 0) < len(current_state.get("sentences", [])):
        if not current_state.get("is_playing"): 
            await asyncio.sleep(1)
            continue

        sentence_index = current_state["current_sentence"]
        sentence = current_state["sentences"][sentence_index]
        audio_file = f"output_{ctx.guild.id}.wav"

        await text_to_speech_async(sentence, audio_file)

        if voice_client.is_connected():
            voice_client.play(discord.FFmpegPCMAudio(audio_file), after=lambda e: print('Player error: %s' % e) if e else None)
            while voice_client.is_playing():
                await asyncio.sleep(1)
            current_state["current_sentence"] += 1
        else:
            print("Voice client disconnected, stopping playback.")
            break

    # End of book
    if voice_client.is_connected():
        await voice_client.disconnect()

# --- Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# --- Text Extraction ---
async def extract_text_from_txt(attachment: discord.Attachment):
    content = await attachment.read()
    return content.decode("utf-8")

async def extract_text_from_pdf(attachment: discord.Attachment):
    content = await attachment.read()
    pdf_file = io.BytesIO(content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

async def extract_text_from_epub(attachment: discord.Attachment):
    content = await attachment.read()
    epub_book = epub.read_epub(io.BytesIO(content))
    text = ""
    for item in epub_book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text += soup.get_text()
    return text

# --- Commands ---
@bot.command()
async def read(ctx, attachment: discord.Attachment):
    global current_state
    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return

    channel = ctx.author.voice.channel
    if discord.utils.get(bot.voice_clients, guild=ctx.guild):
        await discord.utils.get(bot.voice_clients, guild=ctx.guild).move_to(channel)
    else:
        await channel.connect()

    file_ext = os.path.splitext(attachment.filename)[1].lower()
    text = ""

    if file_ext == ".txt":
        text = await extract_text_from_txt(attachment)
    elif file_ext == ".pdf":
        text = await extract_text_from_pdf(attachment)
    elif file_ext == ".epub":
        text = await extract_text_from_epub(attachment)
    else:
        await ctx.send("Unsupported file type. Please upload a .txt, .pdf, or .epub file.")
        return

    if text:
        sentences = split_into_sentences(text)
        current_state = {
            "user_id": ctx.author.id,
            "book_title": attachment.filename,
            "sentences": sentences,
            "current_sentence": 0,
            "is_playing": True
        }
        await ctx.send(f"Starting to read {attachment.filename}. Estimated sentences: {len(sentences)}")
        bot.loop.create_task(play_text(ctx))
    else:
        await ctx.send("Could not extract any text from the file.")

@bot.command()
async def scrape(ctx, url: str):
    global current_state
    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return

    channel = ctx.author.voice.channel
    if discord.utils.get(bot.voice_clients, guild=ctx.guild):
        await discord.utils.get(bot.voice_clients, guild=ctx.guild).move_to(channel)
    else:
        await channel.connect()

    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for bad status codes
        soup = BeautifulSoup(response.content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        if text:
            sentences = split_into_sentences(text)
            current_state = {
                "user_id": ctx.author.id,
                "book_title": f"Scraped content from {url}",
                "sentences": sentences,
                "current_sentence": 0,
                "is_playing": True
            }
            await ctx.send(f"Starting to read content from {url}. Estimated sentences: {len(sentences)}")
            bot.loop.create_task(play_text(ctx))
        else:
            await ctx.send("Could not extract any text from the URL.")

    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error fetching the URL: {e}")


@bot.command()
async def stop(ctx):
    global current_state
    if not discord.utils.get(bot.voice_clients, guild=ctx.guild) or not current_state.get("is_playing"):
        await ctx.send("Nothing is currently playing.")
        return

    current_state["is_playing"] = False
    db = load_db()
    db[str(ctx.author.id)] = {
        "book_title": current_state["book_title"],
        "current_sentence": current_state["current_sentence"],
        "sentences": current_state["sentences"]
    }
    save_db(db)
    await ctx.send(f"Paused and saved progress for {current_state['book_title']} at sentence {current_state['current_sentence']}.")
    
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client.is_connected():
        await voice_client.disconnect()

@bot.command()
async def resume(ctx):
    global current_state
    db = load_db()
    user_state = db.get(str(ctx.author.id))

    if not user_state:
        await ctx.send("No saved state found for you.")
        return

    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return

    channel = ctx.author.voice.channel
    if discord.utils.get(bot.voice_clients, guild=ctx.guild):
        await discord.utils.get(bot.voice_clients, guild=ctx.guild).move_to(channel)
    else:
        await channel.connect()

    current_state = {
        "user_id": ctx.author.id,
        "book_title": user_state["book_title"],
        "sentences": user_state["sentences"],
        "current_sentence": user_state["current_sentence"],
        "is_playing": True
    }

    await ctx.send(f"Resuming {user_state['book_title']} from sentence {user_state['current_sentence']}.")
    bot.loop.create_task(play_text(ctx))


# --- Run Bot ---
if __name__ == "__main__":
    # Make sure to set the BOT_TOKEN environment variable
    bot.run(os.getenv("BOT_TOKEN"))


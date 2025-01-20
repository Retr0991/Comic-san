SECRET_KEY=''

from telegram import ForceReply, Update, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler
from script import getCBZ
import asyncio, os, re

def restricted(func):
    """Decorator to restrict access to authenticated users."""
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not authenticated(user_id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

def authenticated(user_id):
    return True

def authorize(user_id):
    pass

def format_asura_url(url: str) -> str:
    """Format URL to match Asura Comics pattern"""
    pattern = r'https?:\/\/(?:www\.)?asuracomic\.net\/series\/([^\/]+)\/chapter\/(\d+)'
    
    # Check if URL already matches pattern
    if re.match(pattern, url):
        return url
        
    # Extract series name if URL is partial
    series_match = re.search(r'series\/([^\/]+)', url)
    if not series_match:
        raise ValueError("Invalid URL format - must contain series name")
        
    series_name = series_match.group(1)
    
    # Format URL to match pattern
    formatted_url = f"https://asuracomic.net/series/{series_name}"
    return formatted_url

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ Set Auth """
    user = update.effective_user
    if not authenticated(user.id):
        await update.message.reply_html(
            f"Hi {user.full_name}!\nEnter secret key",
            reply_markup = ForceReply(selective=True),
        )

        user_secret = update.message.text
        if user_secret == SECRET_KEY:
            authorize(user.id)
            await update.message.reply_text("You have been authenticated")
        else:
            await update.message.reply_text("Wrong secret key")
    else:
        await update.message.reply_text("You are already authenticated")


@restricted
async def alive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /alive is issued."""
    try:
        # Asynchronously run subprocess commands
        cpu = await run_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        memory = await run_command("free | grep Mem | awk '{printf \"%.2f\", $3/$2 * 100.0}'")
        uptime = await run_command("uptime -p")

        await update.message.reply_text(f"System Info\n"
                                        f"- {uptime}\n"
                                        f"- CPU: {cpu}%\n"
                                        f"- Memory: {memory}%")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

async def run_command(cmd: str) -> str:
    """Asynchronously run a shell command and return its output."""
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise Exception(f"Command failed: {stderr.decode().strip()}")
    
    return stdout.decode().strip()

async def sendCBZ(query: CallbackQuery | None, url: str, 
                  chapter: int | str, name: str) -> None:
    """Send the CBZ file to the user"""
    cbz_path = await getCBZ(url, chapter, name)

    # Get the CBZ file size in MB
    cbz_size = os.path.getsize(cbz_path) / (1024 * 1024)

    # Send the CBZ file
    if cbz_size < 50:
        await query.message.reply_document(
            document=open(cbz_path, 'rb'),
            write_timeout=60,
            read_timeout=60
        )
    else:
        # Dropbox drop-in here
        await query.message.reply_text(f"{cbz_path} is too large to send with size of {cbz_size:.1f} MB")

    # Remove the CBZ file
    os.remove(cbz_path)


def get_range(expression: str) -> list[float]:
    """Get the range of chapters from a string expression, including standalone decimal numbers.

    Examples:
        "1-5" -> [1, 2, 3, 4, 5]
        "1,3,5" -> [1, 3, 5]
        "1-3,5,7-9" -> [1, 2, 3, 5, 7, 8, 9]
        "0.1,0.7,3-5" -> [0.1, 0.7, 3, 4, 5]
    """
    # Remove all non-permitted characters (digits, commas, hyphens, and periods)
    expression = re.sub(r'[^\d\-,\.]', '', expression)
    result = []

    # Split by comma and process each part
    for part in expression.split(','):
        if '-' in part:  # Process ranges
            start, end = map(int, part.split('-'))
            result.extend(range(start, end + 1))
        elif part.strip():  # Process standalone numbers (integers or decimals)
            result.append(float(part) if '.' in part else int(part))

    return sorted(set(result))  # Remove duplicates and sort

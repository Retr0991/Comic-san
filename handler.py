SECRET_KEY=''

from telegram import ForceReply, Update, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler
from script import getCBZ
import subprocess, os, re

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

        cpu = subprocess.run(["top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'"], shell=True, capture_output=True, text=True).stdout.strip()
        memory = subprocess.run(["free | grep Mem | awk '{printf \"%.2f\", $3/$2 * 100.0}'"], shell=True, capture_output=True, text=True).stdout.strip()
        uptime = subprocess.run(["uptime -p"], shell=True, capture_output=True, text=True).stdout.strip()
        await update.message.reply_text(f"System Info\n"
                                        f"- {uptime}\n"
                                        f"- CPU: {cpu}%\n"
                                        f"- Memory: {memory}%")
        
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


def get_range(expression: str) -> list[int]:
    """Get the range of chapters from a string expression.
    Examples:
        "1-5" -> [1,2,3,4,5]
        "1,3,5" -> [1,3,5]
        "1-3,5,7-9" -> [1,2,3,5,7,8,9]
    """
    # Remove all non permitted characters
    expression = re.sub(r'[^\d\-\,]', '', expression)
    
    result = []
    # Split by comma and process each part
    for part in expression.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            result.extend(range(start, end + 1))
        else:
            if part.strip():  # Check if part is not empty
                result.append(int(part))
    
    return sorted(list(set(result)))  # Remove duplicates and sort

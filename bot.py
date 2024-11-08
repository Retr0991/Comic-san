CUSTOM_BOT_API_SERVER = 'http://localhost:8081'

import logging
import subprocess

from telegram import ForceReply, Update

from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

authenticatedUsers = []

# Enable logging

logging.basicConfig(

    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO

)

# set higher logging level for httpx to avoid all GET and POST requests being logged

logging.getLogger("httpx").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

def restricted(func):
    """Decorator to restrict access to authenticated users."""
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in authenticatedUsers:
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

# Define a few command handlers. These usually take the two arguments update and

# context.

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /start is issued and prompt for the secret key."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.full_name}!\nEnter secret key",
        reply_markup=ForceReply(selective=True),
    )
    return 1  # Move to the next state to wait for the user's response

async def check_secret_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check if the received message contains the secret key."""
    user_id = update.effective_user.id
    message_text = update.message.text

    if SECRET_KEY in message_text:
        if user_id not in authenticatedUsers:
            authenticatedUsers.append(user_id)
            await update.message.reply_text("You have been authenticated.")
        else:
            await update.message.reply_text("You are already authenticated.")
    else:
        await update.message.reply_text("Invalid secret key. Please try again.")
        return ConversationHandler.END  # Stay in the current state to wait for the correct secret key

    return ConversationHandler.END  # End the conversation
    

@restricted
async def getStats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /alive is issued."""

        cpu = subprocess.run(["top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'"], shell=True, capture_output=True, text=True).stdout.strip()
        memory = subprocess.run(["free | grep Mem | awk '{printf \"%.2f\", $3/$2 * 100.0}'"], shell=True, capture_output=True, text=True).stdout.strip()
        uptime = subprocess.run(["uptime -p"], shell=True, capture_output=True, text=True).stdout.strip()
        await update.message.reply_text(f"System Info\n"
                                        f"- {uptime}\n"
                                        f"- CPU: {cpu}%\n"
                                        f"- Memory: {memory}%")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    """Send a message when the command /help is issued."""

    await update.message.reply_text("Fake Help message")


@restricted
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    """Echo the user message."""

    await update.message.reply_text(update.message.text)

@restricted
async def handlePDF(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
        """Handle PDF files."""
    
        document = update.message.document
    
        if document.mime_type == 'application/pdf':
    
            try:
                # Download the file
                file = await context.bot.get_file(document.file_id,
                                                  read_timeout=60,
                                                  write_timeout=60)
                file_path = f"{document.file_name}"
                await file.download_to_drive(file_path, write_timeout=60)
                logger.info("File downloaded successfully to %s", file_path)

                # run command line comands
                try:
                    subprocess.run(["./conv", file_path, file_path[:-4]])
                except Exception as e:
                    logger.error("Error while converting%s", e)
                    await update.message.reply_text("Error while converting the file")

                cbz_file_path = file_path[:-3]+'cbz'

                # Send the file back to the user
                await update.message.reply_document(cbz_file_path,
                                                    read_timeout=60,
                                                    write_timeout=60)
                logger.info("File sent back to the user successfully: %s", cbz_file_path)

                # delete the file
                subprocess.run(["rm", file_path])
                subprocess.run(["rm", file_path[:-3]+'cbz'])
    
            except Exception as e:
                logger.error("Error: %s", e)
                await update.message.reply_text("Error while downloading the file: %s", e)



def main() -> None:

    """Start the bot."""

    # Create the Application and pass it your bot's token.

    application = Application.builder().token(TOKEN).base_url(CUSTOM_BOT_API_SERVER+'/bot').local_mode(True).build()

    # Create a conversation handler with the states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_secret_key)],
        },
        fallbacks=[],
    )

    # Add handlers
    application.add_handler(conv_handler)

    # on different commands - answer in Telegram

    application.add_handler(CommandHandler("start", start))

    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(CommandHandler("alive", getStats))


    # on non command i.e message - echo the message on Telegram

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    application.add_handler(MessageHandler(filters.ATTACHMENT, handlePDF))


    # Run the bot until the user presses Ctrl-C

    application.run_polling(allowed_updates=Update.ALL_TYPES)



if __name__ == "__main__":
    main()
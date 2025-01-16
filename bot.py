import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, ContextTypes, 
MessageHandler, filters, ConversationHandler, CallbackQueryHandler)
from handler import (alive, format_asura_url,
              sendCBZ, get_range)
import json
import dotenv
import os

dotenv.load_dotenv()
TOKEN = os.getenv("TOKEN")

saved_data = {}
with open("data.json", "r") as file:
    saved_data = json.load(file)


# Stages            
START_ROUTES, GET_URL, SAVE_ROUTE, JOB, CHAPTER_INPUT = range(5)

# Callback data
ONE, TWO, THREE, FOUR = range(4)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def select_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Choose CHANNEL"""
    # Get user that sent /start and log his name
    user = update.message.from_user

    logger.info("User %s started the conversation.", user.first_name)

    # Build InlineKeyboard where each button has a displayed text
    # and a string as callback_data
    # The keyboard is a list of button rows, where each row is in turn
    # a list (hence `[[...]]`).

    keyboard = [
        [
            InlineKeyboardButton("Asura", callback_data=str(ONE)),
            InlineKeyboardButton("Cancel", callback_data=str(TWO)),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send message with text and appended InlineKeyboard
    await update.message.reply_text("Choose the site to fetch", reply_markup=reply_markup)

    # Tell ConversationHandler that we're in state `FIRST` now
    return START_ROUTES


async def asura(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get the series URL"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Selected Asura\nEnter the URL of the Manhwa")
    return GET_URL

async def getManhwaDetails(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle URL and name input"""
    if 'url' not in context.user_data:
        # First message - store URL
        context.user_data['url'] = format_asura_url(update.message.text + '/')
        await update.message.reply_text("Enter the name of the Manhwa")
        return GET_URL
    else:
        # Second message - store name and show confirmation
        name = update.message.text
        while name in [1, 2]:
            await update.message.reply_text("Invalid name. Enter the name of the Manhwa")
            return GET_URL
        context.user_data['name'] = name
        url = context.user_data['url']
        
        await update.message.reply_text(f"URL set to: `{url}`\nName: `{name}`", parse_mode='MarkdownV2')
        
        keyboard = [
            [
                InlineKeyboardButton("Save", callback_data=str(ONE)),
                InlineKeyboardButton("Nah", callback_data=str(TWO)),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Do you want to save the details?", reply_markup=reply_markup)
        return SAVE_ROUTE


async def save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the Manhwa details"""
    query = update.callback_query
    await query.answer()

    url = context.user_data['url']
    name = context.user_data['name']
    saved_data[name] = url
    with open("data.json", "w") as file:
        json.dump(saved_data, file)

    await query.edit_message_text(text=f"Record `{name}` has been saved", parse_mode='MarkdownV2')

    context.user_data.clear()
    return ConversationHandler.END



async def set_chapter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get Chapter(s) to download"""

    query = update.callback_query
    await query.answer()

    if query.data in saved_data:
        context.user_data['url'] = saved_data[query.data]
        context.user_data['name'] = query.data

    keyboard = [
        [
            InlineKeyboardButton("Get Latest Chapter", callback_data=str(ONE)),
            InlineKeyboardButton("Custom", callback_data=str(TWO)),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Select the chapter(s) to download", reply_markup=reply_markup)

    return JOB

async def single_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Performs latest chapter download"""
    query = update.callback_query
    await query.answer()

    url = context.user_data['url']
    name = context.user_data['name']
    await query.edit_message_text(text="Starting Job")

    await sendCBZ(query, url, "latest", name)

    context.user_data.clear()
    return ConversationHandler.END


async def custom_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Performs custom chapter download"""
    query = update.callback_query
    await query.answer()

    # If first time, prompt for input
    if 'chapters' not in context.user_data:
        await query.edit_message_text(text="Set chapter range")
        return CHAPTER_INPUT
    
    expression = context.user_data['chapters']
    li = get_range(expression)
    logger.info(f"List formed: {li}")
    url = context.user_data['url']
    name = context.user_data['name']
    await query.edit_message_text(text="Starting Custom Job")
    for chapter in li:
        await sendCBZ(query, url, chapter, name)

    context.user_data.clear()
    return ConversationHandler.END

async def handle_chapter_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle chapter range input"""
    expression = update.message.text
    context.user_data['chapters'] = expression

    keyboard = [
        [
            InlineKeyboardButton("Continue", callback_data=str(TWO)),
            InlineKeyboardButton("Cancel", callback_data=str(FOUR)),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Selected Range:\n{get_range(expression)}", reply_markup=reply_markup)
    return JOB

async def show_saved_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show saved data"""
    user = update.message.from_user

    keyboard = []
    for key in saved_data:
        keyboard.append([InlineKeyboardButton(key, callback_data=key)])

    keyboard.append([InlineKeyboardButton("Cancel", callback_data=str(FOUR))])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select the record to download", reply_markup=reply_markup)

    return JOB

async def end_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Clear user data and end conversation"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Conversation ended.")
    elif update.message:
        await update.message.reply_text("Conversation ended.")
    
    context.user_data.clear()
    return ConversationHandler.END


def main() -> None:
    """ Start thr Bot """

    app = Application.builder().token(TOKEN).build()

    # app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("alive", alive))

    conv_handler = ConversationHandler(

        entry_points=[CommandHandler("select", select_channel)],

        states={

            START_ROUTES: [

                CallbackQueryHandler(asura, pattern="^" + str(ONE) + "$"),
                CallbackQueryHandler(end_conversation, pattern="^" + str(TWO) + "$"),

            ],

            GET_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, getManhwaDetails),
            ],

            SAVE_ROUTE: [

                CallbackQueryHandler(save, pattern="^" + str(ONE) + "$"),
                CallbackQueryHandler(set_chapter, pattern="^" + str(TWO) + "$"),

            ],

            JOB: [
                CallbackQueryHandler(single_job, pattern="^" + str(ONE) + "$"),
                CallbackQueryHandler(custom_job, pattern="^" + str(TWO) + "$"),
                CallbackQueryHandler(set_chapter, pattern="^" + str(THREE) + "$"),
                CallbackQueryHandler(end_conversation, pattern="^" + str(FOUR) + "$"),
            ],

            CHAPTER_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chapter_input)
            ]

        },

        fallbacks=[
            CommandHandler("cancel", end_conversation),
            CallbackQueryHandler(end_conversation, pattern="^" + str(FOUR) + "$"),
        ],

        per_message=False
    )

    saved_data_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("saved", show_saved_data)],
        states={
            JOB: [
                CallbackQueryHandler(single_job, pattern="^" + str(ONE) + "$"),
                CallbackQueryHandler(custom_job, pattern="^" + str(TWO) + "$"),
                CallbackQueryHandler(set_chapter, pattern="^(?!(" + str(ONE) + "|" + str(TWO) + "|" + str(FOUR) + ")$).*$"),
                CallbackQueryHandler(end_conversation, pattern="^" + str(FOUR) + "$"),
            ],
            CHAPTER_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chapter_input)
            ]
        },
        fallbacks=[CommandHandler("cancel", end_conversation)],
        per_message=False
    )

    app.add_handler(conv_handler)
    app.add_handler(saved_data_conv_handler)


    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

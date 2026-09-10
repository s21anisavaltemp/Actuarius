import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Configuration

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID", "")

RECORDINGS_DIR = Path(
    os.getenv("RECORDINGS_DIR", "app/recordings")
)

MESSAGE_TYPES = {
    "type_idea": "Идея",
    "type_task": "Задача",
    "type_note": "Заметка",
    "type_thought": "Мысль",
    "type_other": "Другое",
}

# Conversation states

WAITING_ACTION = 0
WAITING_VOICE = 1
WAITING_TYPE = 2

# Logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# Functions

def is_allowed_user(update: Update) -> bool:
    """
    If ALLOWED_USER_ID is configured, only that Telegram user
    can use the bot.
    """
    if not ALLOWED_USER_ID:
        return True

    user = update.effective_user

    if user is None:
        return False

    try:
        return user.id == int(ALLOWED_USER_ID)
    except ValueError:
        logger.error("ALLOWED_USER_ID must be an integer")
        return False

def get_current_series_dir(context: ContextTypes.DEFAULT_TYPE) -> Path | None:
    """
    Returns the directory of the currently active series.
    """
    series_dir = context.user_data.get("series_dir")

    if not series_dir:
        return None

    return Path(series_dir)

def create_series(context: ContextTypes.DEFAULT_TYPE) -> Path:
    """
    Creates a new directory for a voice message series.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    series_dir = RECORDINGS_DIR / timestamp

    # Extremely unlikely collision protection.
    counter = 1
    original_dir = series_dir

    while series_dir.exists():
        series_dir = Path(f"{original_dir}_{counter}")
        counter += 1

    series_dir.mkdir(parents=True, exist_ok=False)

    context.user_data["series_dir"] = str(series_dir)
    context.user_data["voice_count"] = 0

    logger.info("Created new series: %s", series_dir)

    return series_dir

def get_or_create_series(context: ContextTypes.DEFAULT_TYPE) -> Path:
    """
    Returns the current series or creates a new one.
    """
    existing = get_current_series_dir(context)

    if existing is not None:
        return existing

    return create_series(context)

def get_next_voice_number(context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Returns the next sequential voice message number.
    """
    current_count = context.user_data.get("voice_count", 0)

    next_number = current_count + 1

    context.user_data["voice_count"] = next_number

    return next_number

def clear_series(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Clears information about the active series.
    Does not delete files.
    """
    context.user_data.pop("series_dir", None)
    context.user_data.pop("voice_count", None)

def action_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard shown after each saved voice message.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Продолжить",
                callback_data="continue_series",
            ),
            InlineKeyboardButton(
                "✅ Закончить серию",
                callback_data="finish_series",
            ),
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

def type_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard for selecting the type of the completed series.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "💡 Идея",
                callback_data="type_idea",
            ),
            InlineKeyboardButton(
                "📋 Задача",
                callback_data="type_task",
            ),
        ],
        [
            InlineKeyboardButton(
                "📝 Заметка",
                callback_data="type_note",
            ),
            InlineKeyboardButton(
                "💭 Мысль",
                callback_data="type_thought",
            ),
        ],
        [
            InlineKeyboardButton(
                "📦 Другое",
                callback_data="type_other",
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# /start

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_allowed_user(update):
        return ConversationHandler.END

    await update.message.reply_text(
        "Привет! 👋\n\n"
        "Отправь мне голосовое сообщение.\n"
        "После каждого голосового я спрошу, продолжать ли серию."
    )

    return WAITING_VOICE

# Voice message handling

async def receive_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Saves a voice message to the current series.
    """
    if not is_allowed_user(update):
        return ConversationHandler.END

    message = update.message

    if message is None or message.voice is None:
        return WAITING_VOICE

    try:
        series_dir = get_or_create_series(context)

        voice_number = get_next_voice_number(context)

        filename = f"{voice_number:03d}.ogg"
        destination = series_dir / filename

        # Get Telegram file object
        telegram_file = await context.bot.get_file(
            message.voice.file_id
        )

        # Download without conversion.
        await telegram_file.download_to_drive(
            custom_path=destination
        )

        logger.info(
            "Saved voice message: %s",
            destination,
        )

        await message.reply_text(
            f"Голосовое сохранено как `{filename}`.\n\n"
            "Это конец серии?",
            reply_markup=action_keyboard(),
            parse_mode="Markdown",
        )

        return WAITING_ACTION

    except Exception:
        logger.exception("Failed to save voice message")

        await message.reply_text(
            "❌ Не удалось сохранить голосовое сообщение. "
            "Попробуй ещё раз."
        )

        return WAITING_VOICE


# Continue series

async def continue_series(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    User wants to add another voice message to the current series.
    """
    if not is_allowed_user(update):
        return ConversationHandler.END

    query = update.callback_query

    if query is None:
        return WAITING_ACTION

    await query.answer()

    await query.edit_message_text(
        "Хорошо 👍\n\n"
        "Отправь следующее голосовое сообщение."
    )

    return WAITING_VOICE


# Finish series

async def finish_series(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Finishes the current series without requiring another voice
    message and asks for its type.
    """
    if not is_allowed_user(update):
        return ConversationHandler.END

    query = update.callback_query

    if query is None:
        return WAITING_ACTION

    await query.answer()

    series_dir = get_current_series_dir(context)

    if series_dir is None:
        await query.edit_message_text(
            "Активной серии нет.\n\n"
            "Отправь голосовое сообщение, чтобы начать новую."
        )

        return WAITING_VOICE

    await query.edit_message_text(
        "Серия закончена. ✅\n\n"
        "К какому типу относится эта серия?",
        reply_markup=type_keyboard(),
    )

    return WAITING_TYPE


# Type selection

async def select_type(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Saves selected type into type.txt and starts waiting
    for the next series.
    """
    if not is_allowed_user(update):
        return ConversationHandler.END

    query = update.callback_query

    if query is None:
        return WAITING_TYPE

    await query.answer()

    callback_data = query.data

    message_type = MESSAGE_TYPES.get(callback_data)

    if message_type is None:
        await query.edit_message_text(
            "❌ Неизвестный тип сообщения."
        )
        return WAITING_TYPE

    series_dir = get_current_series_dir(context)

    if series_dir is None:
        await query.edit_message_text(
            "Активная серия не найдена."
        )
        return WAITING_VOICE

    try:
        type_file = series_dir / "type.txt"

        type_file.write_text(
            message_type,
            encoding="utf-8",
        )

        voice_count = context.user_data.get(
            "voice_count",
            0,
        )

        logger.info(
            "Finished series %s, type=%s, voices=%d",
            series_dir,
            message_type,
            voice_count,
        )

        await query.edit_message_text(
            f"Готово! ✅\n\n"
            f"Тип: {message_type}\n"
            f"Голосовых сообщений: {voice_count}\n\n"
            "Можешь отправить следующее голосовое "
            "для создания новой серии."
        )

        # Important:
        # the previous series is now completely finished.
        clear_series(context)

        return WAITING_VOICE

    except Exception:
        logger.exception("Failed to save message type")

        await query.edit_message_text(
            "❌ Не удалось сохранить тип серии. "
            "Попробуй выбрать его ещё раз."
        )

        return WAITING_TYPE


# Cancel

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Stops the current conversation without deleting already
    saved files.
    """
    if not is_allowed_user(update):
        return ConversationHandler.END

    series_dir = get_current_series_dir(context)

    if series_dir:
        await update.message.reply_text(
            "Текущая серия остановлена.\n\n"
            "Уже сохранённые голосовые файлы не удалены."
        )
    else:
        await update.message.reply_text(
            "Текущей активной серии нет."
        )

    clear_series(context)

    return WAITING_VOICE


# Fallback for ignored messages

async def ignore_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    All non-voice messages are intentionally ignored.
    """
    return WAITING_VOICE


async def ignore_during_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Ignore messages while waiting for Continue/Finish.
    """
    return WAITING_ACTION


async def ignore_during_type(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Ignore messages while waiting for type selection.
    """
    return WAITING_TYPE


# Error handler

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    logger.exception(
        "Unhandled exception while processing update",
        exc_info=context.error,
    )


# Main

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is not configured"
        )

    RECORDINGS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(30)       # Increase network read timeout
        .write_timeout(30)      # Increase network write timeout
        .connect_timeout(30)    # Increase initial connection timeout
        .pool_timeout(30)
        .build()
    )

    conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
        ],

        states={
            # ------------------------------------------------
            # Waiting for a voice message
            # ------------------------------------------------
            WAITING_VOICE: [
                MessageHandler(
                    filters.VOICE,
                    receive_voice,
                ),
                CommandHandler(
                    "cancel",
                    cancel,
                ),
                MessageHandler(
                    ~filters.VOICE,
                    ignore_message,
                ),
            ],

            # ------------------------------------------------
            # Voice has been saved.
            # Waiting for Continue / Finish.
            # ------------------------------------------------
            WAITING_ACTION: [
                CallbackQueryHandler(
                    continue_series,
                    pattern="^continue_series$",
                ),
                CallbackQueryHandler(
                    finish_series,
                    pattern="^finish_series$",
                ),
                CommandHandler(
                    "cancel",
                    cancel,
                ),
                MessageHandler(
                    filters.ALL,
                    ignore_during_action,
                ),
            ],

            # ------------------------------------------------
            # Series is finished.
            # Waiting for type.
            # ------------------------------------------------
            WAITING_TYPE: [
                CallbackQueryHandler(
                    select_type,
                    pattern="^type_",
                ),
                CommandHandler(
                    "cancel",
                    cancel,
                ),
                MessageHandler(
                    filters.ALL,
                    ignore_during_type,
                ),
            ],
        },

        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
        ],

        # Since this bot is intended for one user, this also
        # prevents concurrent updates for the same conversation
        # from causing confusing state transitions.
        per_chat=True,
        per_user=True,
    )

    application.add_handler(
        conversation_handler
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Bot started. python-telegram-bot=%s",
        __import__("telegram").__version__,
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()

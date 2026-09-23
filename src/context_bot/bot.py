import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

import mtranslate
from telebot import TeleBot, types

from context_bot.config import Settings
from context_bot.pdf import extract_text
from context_bot.storage import UserRepository
from context_bot.summarizer import summarize

logger = logging.getLogger(__name__)


def _menu() -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("PDF Summarizer", callback_data="pdf_summarizer"),
        types.InlineKeyboardButton("Software Development Contact", callback_data="contact"),
    )
    return keyboard


def create_bot(settings: Settings) -> TeleBot:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    users = UserRepository(settings.users_file)
    bot = TeleBot(token=settings.bot_token)
    upload_prompts: dict[int, int] = {}

    @bot.message_handler(commands=["start"])
    def send_welcome(message: types.Message) -> None:
        users.add(message.from_user.id, message.from_user.username)
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "Welcome to PDF Contexter Bot!", reply_markup=_menu())

    @bot.callback_query_handler(func=lambda call: True)
    def handle_menu(call: types.CallbackQuery) -> None:
        action = call.data.split(" ", maxsplit=1)[0]
        chat_id = call.message.chat.id
        bot.delete_message(chat_id, call.message.message_id)

        if action == "pdf_summarizer":
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("<- BACK", callback_data="menu"))
            prompt = bot.send_message(chat_id, "Send me a PDF file:", reply_markup=keyboard)
            upload_prompts[chat_id] = prompt.message_id
        elif action == "contact":
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton("<- BACK", callback_data="menu"),
                types.InlineKeyboardButton("Open Chat", url="https://t.me/ssllvvtt"),
            )
            bot.send_message(chat_id, "Software Development Contact", reply_markup=keyboard)
        elif action == "menu":
            bot.send_message(chat_id, "Choose your option:", reply_markup=_menu())
        elif action == "MessageSender":
            if call.from_user.username != settings.admin_username:
                logger.warning("Unauthorized mass-message request from user %s", call.from_user.id)
                return
            prompt = bot.send_message(chat_id, "Send me a message:")
            bot.register_next_step_handler(prompt, send_mass_message)
        elif action == "translate":
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton("Russian", callback_data="ru"),
                types.InlineKeyboardButton("Arabic", callback_data="ar"),
                types.InlineKeyboardButton("English", callback_data="en"),
                types.InlineKeyboardButton("<- BACK", callback_data="translate_back"),
            )
            bot.send_message(chat_id, call.message.text, reply_markup=keyboard)
        elif action in {"ru", "ar", "en"}:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton("<- BACK", callback_data="translate"),
                types.InlineKeyboardButton("Menu", callback_data="menu"),
            )
            translated = mtranslate.translate(call.message.text, action)
            bot.send_message(chat_id, translated, reply_markup=keyboard)
        elif action == "translate_back":
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton("<- MENU", callback_data="menu"),
                types.InlineKeyboardButton("Translate", callback_data="translate"),
            )
            bot.send_message(chat_id, call.message.text, reply_markup=keyboard)

    def send_mass_message(message: types.Message) -> None:
        active_users = []
        for user in users.all():
            try:
                bot.send_chat_action(user["id"], "typing")
                bot.send_message(user["id"], message.text)
                active_users.append(user)
            except Exception:
                logger.exception("Failed to send message to user %s", user["id"])
        users.replace(active_users)
        bot.send_message(message.chat.id, "Message sent to all users.")

    @bot.message_handler(content_types=["document"])
    def handle_document(message: types.Message) -> None:
        prompt_id = upload_prompts.pop(message.chat.id, None)
        if prompt_id is not None:
            bot.delete_message(message.chat.id, prompt_id)

        if message.document.mime_type != "application/pdf":
            bot.send_message(message.chat.id, "File type not supported.")
            return

        file_path: Path | None = None
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            with NamedTemporaryFile(
                dir=settings.upload_dir,
                suffix=".pdf",
                delete=False,
            ) as temporary_file:
                temporary_file.write(downloaded_file)
                file_path = Path(temporary_file.name)

            received = bot.send_message(message.chat.id, "PDF received and saved successfully.")
            wait = bot.send_message(
                message.chat.id,
                "Please wait while I summarize your PDF... It can take 1-3 minutes.",
            )
            summary = summarize(extract_text(file_path))

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton("<- MENU", callback_data="menu"),
                types.InlineKeyboardButton("Translate", callback_data="translate"),
            )
            bot.delete_message(message.chat.id, message.message_id)
            bot.delete_message(message.chat.id, wait.message_id)
            bot.delete_message(message.chat.id, received.message_id)
            bot.send_message(
                message.chat.id,
                f"Here is your summarized text: {summary}",
                reply_markup=keyboard,
            )
        except Exception:
            logger.exception("Error processing PDF file")
            bot.send_message(message.chat.id, "An error occurred while processing the PDF file.")
        finally:
            if file_path is not None:
                file_path.unlink(missing_ok=True)

    @bot.message_handler(commands=["aezakmi"])
    def admin_panel(message: types.Message) -> None:
        if message.from_user.username != settings.admin_username:
            logger.warning("Unauthorized admin panel request from user %s", message.from_user.id)
            return

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Message sender", callback_data="MessageSender"))
        bot.send_message(message.chat.id, "Admin Panel", reply_markup=keyboard)

    return bot

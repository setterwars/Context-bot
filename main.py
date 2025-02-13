import os
import logging
import pdfplumber
import json
from tokens import BOT_TOKEN
from telebot import TeleBot, types
from transformers import BartForConditionalGeneration, BartTokenizer, pipeline, MarianMTModel, MarianTokenizer
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0

send_message = []

SAVE_DIR = 'saved_pdfs'
USERS_FILE = 'users.json'

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

bot = TeleBot(token=BOT_TOKEN)

def PDF2TEXT(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            extracted_text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if extracted_text:
                text += extracted_text + "\n"
    return text

def text_summarize(text):
    try:
        lang = detect(text)
        logger.info(f"Detected language: {lang}")

        if lang == 'en':
            model_name = "facebook/bart-large-cnn"
            model = BartForConditionalGeneration.from_pretrained(model_name)
            tokenizer = BartTokenizer.from_pretrained(model_name)
        else:
            translation_model_name = "Helsinki-NLP/opus-mt-mul-en"
            translation_model = MarianMTModel.from_pretrained(translation_model_name)
            translation_tokenizer = MarianTokenizer.from_pretrained(translation_model_name)

            translated = translation_model.generate(**translation_tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512))
            text = translation_tokenizer.decode(translated[0], skip_special_tokens=True)
            logger.info(f"Translated text: {text}")

            model_name = "facebook/bart-large-cnn"
            model = BartForConditionalGeneration.from_pretrained(model_name)
            tokenizer = BartTokenizer.from_pretrained(model_name)

        summarizer = pipeline("summarization", model=model, tokenizer=tokenizer)

        inputs = tokenizer.encode("summarize: " + text, return_tensors="pt", max_length=1024, truncation=True)
        outputs = model.generate(
            inputs,
            max_length=700,
            min_length=200,
            length_penalty=2.0,
            num_beams=4,
            early_stopping=True
        )
        summary = tokenizer.decode(outputs[0], skip_special_tokens=True, clean_up_tokenization_spaces=True)
        return summary
    except Exception as e:
        logger.error(f"Error in text summarization: {e}")
        return "An error occurred during the summarization process."

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)
    logger.info(f"Created directory: {SAVE_DIR}")

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump([], f)
    logger.info(f"Created file: {USERS_FILE}")

def save_user(user_id, username):
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    if user_id not in [user['id'] for user in users]:
        users.append({'id': user_id, 'username': username})
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f)
        logger.info(f"Saved user: id {user_id}, username: {username}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    save_user(message.from_user.id, message.from_user.username)
    bot.delete_message(message.chat.id, message.message_id)
    logger.info(f"Received /start command from user: id {message.from_user.id}, name: {message.from_user.username}")
    keyboard = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton(text="PDF Summarizer", callback_data='pdf_summarizer')
    button2 = types.InlineKeyboardButton(text="Software Development Contact", callback_data='contact')
    keyboard.add(button1, button2)
    bot.send_message(message.chat.id, "Welcome to PDF Contexter Bot!", reply_markup=keyboard)
    logger.info("Sent welcome message")

@bot.callback_query_handler(func=lambda call: True)
def menu_button_handler(call):
    req = call.data.split(' ')
    logger.info(
        f"Received callback query: {req} from user: id {call.from_user.id}, username: {call.from_user.username}")

    if req[0] == 'pdf_summarizer':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        logger.info(
            f"Deleted menu button message from user: id {call.from_user.id}, username: {call.from_user.username}")
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton(text="<- BACK", callback_data='menu')
        keyboard.add(button1)
        send_message.append(bot.send_message(call.message.chat.id, "Send me a PDF file:", reply_markup=keyboard))
        logger.info("Prompted user to send PDF file")
    elif req[0] == 'contact':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        logger.info(f"Deleted contact message from user: id {call.from_user.id}, username: {call.from_user.username}")
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton(text="<- back", callback_data='menu')
        button2 = types.InlineKeyboardButton(text="Open Chat", url="https://t.me/ssllvvtt")
        keyboard.add(button1, button2)
        bot.send_message(call.message.chat.id, "Software Development Contact", reply_markup=keyboard)
        logger.info("Sent software development contact info")
    elif req[0] == 'menu':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        logger.info(f"Deleted menu message from user: id {call.from_user.id}, username: {call.from_user.username}")
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton(text="PDF Summarizer", callback_data='pdf_summarizer')
        button2 = types.InlineKeyboardButton(text="Software Developer Contact", callback_data='contact')
        keyboard.add(button1, button2)
        bot.send_message(call.message.chat.id, "Choose your option:", reply_markup=keyboard)
        logger.info("Prompted user to choose an option")
    elif req[0] == 'MessageSender':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        logger.info(
            f"Deleted message sender message from user: id {call.from_user.id}, username: {call.from_user.username}")
        msg = bot.send_message(call.message.chat.id, "Send me a message:")
        bot.register_next_step_handler(msg, mass_message_handler)
        logger.info("Prompted user to send message")
    elif req[0] == 'translate':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton(text="Russia", callback_data='ru')
        button2 = types.InlineKeyboardButton(text="Arabic", callback_data='ar')
        button4 = types.InlineKeyboardButton(text="English", callback_data='en')
        button3 = types.InlineKeyboardButton(text="<-BACK", callback_data="translate_back")
        keyboard.add(button1, button2, button4 ,button3)
        bot.send_message(call.message.chat.id, call.message.text, reply_markup=keyboard)
    elif req[0] == 'ru':
        import mtranslate
        bot.delete_message(call.message.chat.id, call.message.message_id)
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton(text="<-BACK", callback_data='translate')
        button2 = types.InlineKeyboardButton(text="Menu", callback_data='menu')
        keyboard.add(button1, button2)
        bot.send_message(call.message.chat.id, mtranslate.translate(call.message.text, 'ru'), reply_markup=keyboard)
    elif req[0] == 'ar':
        import mtranslate
        bot.delete_message(call.message.chat.id, call.message.message_id)
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton(text="<-BACK", callback_data='translate')
        button2 = types.InlineKeyboardButton(text="Menu", callback_data='menu')
        keyboard.add(button1, button2)
        bot.send_message(call.message.chat.id, mtranslate.translate(call.message.text, 'ar'), reply_markup=keyboard)
    elif req[0] == 'en':
        import mtranslate
        bot.delete_message(call.message.chat.id, call.message.message_id)
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton(text="<-BACK", callback_data='translate')
        button2 = types.InlineKeyboardButton(text="Menu", callback_data='menu')
        keyboard.add(button1, button2)
        bot.send_message(call.message.chat.id, mtranslate.translate(call.message.text, 'en'), reply_markup=keyboard)
    elif req[0] == 'translate_back':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton(text="<- MENU", callback_data='menu')
        button2 = types.InlineKeyboardButton(text="Translate", callback_data='translate')
        keyboard.add(button1, button2)
        bot.send_message(call.message.chat.id, call.message.text, reply_markup=keyboard)

def mass_message_handler(message):
    logger.info(f"Received mass message from admin: {message.text}")
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    updated_users = users.copy()
    for user in users:
        try:
            flag = bot.send_chat_action(user['id'], 'typing')
            if flag:
                bot.send_message(user['id'], message.text)
        except Exception as e:
            logger.error(f"Failed to send message to user {user['id']}: {e}")
            updated_users.remove(user)
    with open(USERS_FILE, 'w') as f:
        json.dump(updated_users, f, indent=4)

    logger.info("Mass message sent to all users")
    bot.send_message(message.chat.id, "Message sent to all users.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if len(send_message) > 0:
        bot.delete_message(message.chat.id, send_message[-1].message_id)
    logger.info(
        f"Received document from user: id {message.from_user.id}, name: {message.from_user.username} with mime type: {message.document.mime_type}")

    if message.document.mime_type == 'application/pdf':
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            file_path = os.path.join(SAVE_DIR, message.document.file_name)
            with open(file_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            logger.info(f"Saved PDF file: {file_path}")
            pdfreceived = bot.send_message(message.chat.id, "PDF received and saved successfully.")
            pdf_text = PDF2TEXT(file_path)
            logger.info("Converted PDF to text")
            wait_message = bot.send_message(message.chat.id, "Please wait while I summarize your PDF... It can take 1-3 minutes.")
            summary = text_summarize(pdf_text)
            os.remove(file_path)
            logger.info(f"Removed PDF file: {file_path}")
            keyboard = types.InlineKeyboardMarkup()
            button1 = types.InlineKeyboardButton(text="<- MENU", callback_data='menu')
            button2 = types.InlineKeyboardButton(text="Translate", callback_data='translate')
            keyboard.add(button1, button2)
            bot.delete_message(message.chat.id, message.message_id)
            bot.delete_message(message.chat.id, wait_message.message_id)
            bot.delete_message(message.chat.id, pdfreceived.message_id)
            bot.send_message(message.chat.id, f"Here is your summarized text:{summary}", reply_markup=keyboard)
            logger.info("Prompted user with summarized text and menu option")
        except Exception as e:
            logger.error(f"Error processing PDF file: {e}")
            bot.send_message(message.chat.id, "An error occurred while processing the PDF file.")
    else:
        logger.warning(f"Unsupported file type received: {message.document.mime_type}")
        bot.send_message(message.chat.id, "File type not supported.")

@bot.message_handler(commands=['aezakmi'])
def admin_panel(message):
    if message.from_user.username == 'ssllvvtt':
        logger.info(
            f"Received /AdminPanel command from user: id {message.from_user.id}, name: {message.from_user.username}")
        button1 = types.InlineKeyboardButton(text="Message sender", callback_data='MessageSender')
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(button1)
        bot.send_message(message.chat.id, "Admin Panel", reply_markup=keyboard)
    else:
        logger.info(
            f"Unauthorized user try to call admin panel: id {message.from_user.id}, name: {message.from_user.username}")

logger.info("Bot started polling")
bot.infinity_polling()
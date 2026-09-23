import logging

from context_bot.bot import create_bot
from context_bot.config import Settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    bot = create_bot(Settings.from_env())
    logging.getLogger(__name__).info("Bot started polling")
    bot.infinity_polling()

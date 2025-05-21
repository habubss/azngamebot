from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import MessageEntityType
import sqlite3
import json
import logging
import re

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "7973682932:AAEDjrvUDeyn4olfnk3iJUYK__-4HbL6lFA"


def init_db():
    conn = sqlite3.connect('scores.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            score INTEGER,
            group_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


init_db()


async def send_start_message(chat_id, context):
    """Отправляет стартовое сообщение с кнопкой"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            text="уйнарга",
            web_app={"url": "https://soft-belekoy-0e2f3a.netlify.app/"}
        )]
    ])

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Уйнарга өчен түбәндәге төймәгә басыгыз!",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        raise


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await send_start_message(update.message.chat_id, context)


async def handle_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик добавления бота в чат"""
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await send_start_message(update.message.chat.id, context)
            break


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальный обработчик сообщений"""
    if not update.message or not update.message.text:
        return

    bot_username = context.bot.username.lower()
    message_text = update.message.text.lower()

    # Проверка на упоминание
    if f"@{bot_username}" in message_text:
        try:
            await send_start_message(update.message.chat.id, context)
        except Exception as e:
            logger.error(f"Ошибка при обработке упоминания: {e}")
            await update.message.reply_text("Произошла ошибка, попробуйте позже")
        return

    # Дополнительная проверка через entities
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == MessageEntityType.MENTION:
                mentioned = update.message.text[entity.offset:entity.offset + entity.length].lower()
                if mentioned[1:] == bot_username:
                    try:
                        await send_start_message(update.message.chat.id, context)
                    except Exception as e:
                        logger.error(f"Ошибка при обработке упоминания: {e}")
                    return


async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.message.web_app_data.data)
        logger.info(f"Алынган мәгълүмат: {data}")

        conn = sqlite3.connect('scores.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scores (user_id, username, first_name, score, group_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['user_id'], data['username'], data['first_name'], data['score'], data['group_id']))
        conn.commit()
        conn.close()

        if 'group_id' in data and data['group_id']:
            await send_top_message(data['group_id'], context)

        await update.message.reply_text(f"Вы набрали {data['score']} очков в Lumberjack")
    except Exception as e:
        logger.error(f"Мәгълүмат эшкәртүдә хата: {e}")
        await update.message.reply_text("Произошла ошибка при сохранении результата")


async def send_top_message(chat_id, context):
    """Отправляет топ игроков"""
    try:
        conn = sqlite3.connect('scores.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, MAX(score) as max_score
            FROM scores
            WHERE group_id = ?
            GROUP BY user_id
            ORDER BY max_score DESC
            LIMIT 10
        ''', (chat_id,))
        top_players = cursor.fetchall()
        conn.close()

        message = "# фасат через @gamebot\n\n## Lumberjack\n**Top Players**\n"
        for i, (username, score) in enumerate(top_players, 1):
            message += f"{i}. {username} - {score}\n"
        message += "\n---\n### Play Lumberjack!"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("уйнарга", web_app={"url": "https://soft-belekoy-0e2f3a.netlify.app/"})]
        ])

        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=keyboard,
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке топа: {e}")


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /top"""
    await send_top_message(update.message.chat.id, context)


def main():
    app = Application.builder().token(TOKEN).build()

    # Порядок обработчиков важен!
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_members))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("top", top_command))

    logger.info("Бот запущен и готов к работе!")
    app.run_polling()


if __name__ == '__main__':
    main()
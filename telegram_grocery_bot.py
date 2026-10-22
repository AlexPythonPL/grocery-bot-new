import os
import telebot
from flask import Flask, request

# Читаем токен и выводим его длину для отладки в логах Render
# .strip() автоматически удалит случайно попавшие пробелы или переносы строк
BOT_TOKEN = os.environ.get('BOT_TOKEN', '').strip()
print(f"DEBUG_CHECK -> BOT_TOKEN length: {len(BOT_TOKEN) if BOT_TOKEN else 'NOT FOUND'}")

if not BOT_TOKEN:
    raise ValueError("❌ ОШИБКА: Переменная окружения BOT_TOKEN не найдена на Render!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

user_data = {}

# Автоматическая настройка вебхука для Render
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')
if RENDER_URL:
    webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    print(f"✅ WEBHOOK SUCCESSFULLY SET TO: {webhook_url}")
else:
    print("⚠️ RENDER_EXTERNAL_URL не найдена, вебхук не установлен автоматически.")


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Привіт! Я твій Розумний Помічник у магазині. 🛒\n\n"
        "Я допоможу дізнатися реальну ціну за 1 кг/л та обрати вигідніший товар!\n\n"
        "Натисни /calc або напиши будь-яке повідомлення, щоб почати розрахунок."
    )
    bot.reply_to(message, welcome_text)


@bot.message_handler(commands=['calc'])
@bot.message_handler(func=lambda message: True)
def start_calc(message):
    chat_id = message.chat.id
    user_data[chat_id] = {}

    msg = bot.send_message(
        chat_id, "Введіть назву **першого** товару :", parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_name1)


def process_name1(message):
    chat_id = message.chat.id
    user_data[chat_id]['name1'] = message.text

    msg = bot.send_message(
        chat_id, f"Введіть вагу/об'єм **{message.text}** у грамах/мл:"
    )
    bot.register_next_step_handler(msg, process_weight1)


def process_weight1(message):
    chat_id = message.chat.id
    try:
        user_data[chat_id]['netto1'] = float(message.text.replace(',', '.'))
        msg = bot.send_message(
            chat_id, f"Введіть ціну **{user_data[chat_id]['name1']}** у гривнях:"
        )
        bot.register_next_step_handler(msg, process_price1)
    except ValueError:
        msg = bot.send_message(
            chat_id, "Будь ласка, введіть число (вагу в грамах)! Спробуйте ще раз:"
        )
        bot.register_next_step_handler(msg, process_weight1)


def process_price1(message):
    chat_id = message.chat.id
    try:
        user_data[chat_id]['price1'] = float(message.text.replace(',', '.'))
        msg = bot.send_message(chat_id, "Тепер введіть назву **другого** товару :")
        bot.register_next_step_handler(msg, process_name2)
    except ValueError:
        msg = bot.send_message(
            chat_id, "Будь ласка, введіть число (ціну)! Спробуйте ще раз:"
        )
        bot.register_next_step_handler(msg, process_price1)


def process_name2(message):
    chat_id = message.chat.id
    user_data[chat_id]['name2'] = message.text

    msg = bot.send_message(
        chat_id, f"Введіть вагу/об'єм **{message.text}** у грамах/мл:"
    )
    bot.register_next_step_handler(msg, process_weight2)


def process_weight2(message):
    chat_id = message.chat.id
    try:
        user_data[chat_id]['netto2'] = float(message.text.replace(',', '.'))
        msg = bot.send_message(
            chat_id, f"Введіть ціну **{user_data[chat_id]['name2']}** у гривнях:"
        )
        bot.register_next_step_handler(msg, process_price2)
    except ValueError:
        msg = bot.send_message(
            chat_id, "Будь ласка, введіть число (вагу)! Спробуйте ще раз:"
        )
        bot.register_next_step_handler(msg, process_weight2)


def process_price2(message):
    chat_id = message.chat.id
    try:
        user_data[chat_id]['price2'] = float(message.text.replace(',', '.'))

        d = user_data[chat_id]
        res1 = (d['price1'] / d['netto1']) * 1000
        res2 = (d['price2'] / d['netto2']) * 1000

        result_text = (
            f"📊 **Результати розрахунку:**\n\n"
            f"• **{d['name1']}**: {res1:.2f} грн за 1 кг/л\n"
            f"• **{d['name2']}**: {res2:.2f} грн за 1 кг/л\n\n"
        )

        if res1 > res2:
            diff = res1 - res2
            result_text += f"💡 **{d['name2']}** вигідніше на **{diff:.2f} грн/кг**!"
        elif res2 > res1:
            diff = res2 - res1
            result_text += f"💡 **{d['name1']}** вигідніше на **{diff:.2f} грн/кг**!"
        else:
            result_text += "⚖️ Ціни за 1 кг/л однакові!"

        result_text += (
            "\n\nЩоб зробити новий розрахунок, просто напишіть будь-що у чат."
        )

        bot.send_message(chat_id, result_text, parse_mode="Markdown")

    except ValueError:
        msg = bot.send_message(
            chat_id, "Будь ласка, введіть число (ціну)! Спробуйте ще раз:"
        )
        bot.register_next_step_handler(msg, process_price2)


# Вебхук-маршрут для приема запросов от Telegram (использует безопасный токен в URL)
@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    return "Forbidden", 403


@app.route('/')
def index():
    return "Grocery Bot is running!", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

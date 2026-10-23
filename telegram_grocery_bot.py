import os
import telebot
from flask import Flask, request

# Читаем токен и выводим его длину для отладки в логах Render
BOT_TOKEN = os.environ.get('BOT_TOKEN', '').strip()
print(f"DEBUG_CHECK -> BOT_TOKEN length: {len(BOT_TOKEN) if BOT_TOKEN else 'NOT FOUND'}")

if not BOT_TOKEN:
    raise ValueError("❌ ОШИБКА: Переменная окружения BOT_TOKEN не найдена на Render!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

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
        "Напиши /calc, щоб розпочати розрахунок ціни."
    )
    bot.reply_to(message, welcome_text)


@bot.message_handler(commands=['calc'])
def start_calc(message):
    bot.reply_to(message, "Введіть дані у такому форматі:\n\n`Назва1 вага1 ціна1 / Назва2 вага2 ціна2`\n\nПриклад:\n`Сир 200 85 / Сир 300 120`", parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    # Упрощенный парсер в одну строчку для надежной работы на вебхуках
    try:
        text = message.text.strip()
        if '/' not in text:
            bot.reply_to(message, "Будь ласка, введіть дані у форматі: `Товар1 вага ціна / Товар2 вага ціна` (через слеш). Напишіть /calc для прикладу.", parse_mode="Markdown")
            return

        part1, part2 = text.split('/', 1)
        
        # Разбираем первый товар
        p1_words = part1.strip().split()
        price1 = float(p1_words[-1].replace(',', '.'))
        netto1 = float(p1_words[-2].replace(',', '.'))
        name1 = " ".join(p1_words[:-2])

        # Разбираем второй товар
        p2_words = part2.strip().split()
        price2 = float(p2_words[-1].replace(',', '.'))
        netto2 = float(p2_words[-2].replace(',', '.'))
        name2 = " ".join(p2_words[:-2])

        res1 = (price1 / netto1) * 1000
        res2 = (price2 / netto2) * 1000

        result_text = (
            f"📊 **Результати розрахунку:**\n\n"
            f"• **{name1}**: {res1:.2f} грн за 1 кг/л\n"
            f"• **{name2}**: {res2:.2f} грн за 1 кг/л\n\n"
        )

        if res1 > res2:
            diff = res1 - res2
            result_text += f"💡 **{name2}** вигідніше на **{diff:.2f} грн/кг**!"
        elif res2 > res1:
            diff = res2 - res1
            result_text += f"💡 **{name1}** вигідніше на **{diff:.2f} грн/кг**!"
        else:
            result_text += "⚖️ Ціни за 1 кг/л однакові!"

        bot.reply_to(message, result_text, parse_mode="Markdown")

    except Exception:
        bot.reply_to(message, "⚠️ Не вдалось розпізнати формат. Використовуйте приклад:\n`Молоко 900 38 / Молоко 1500 60`", parse_mode="Markdown")


# Надежный вебхук-маршрут (без жесткой привязки к точным параметрам content-type)
@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    if request.headers.get('content-type', '').startswith('application/json'):
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403


@app.route('/')
def index():
    return "Grocery Bot is running!", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

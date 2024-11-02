import telebot
from telebot import types
import requests

bot = telebot.TeleBot('7494619124:AAGNH0Sr3hZpuVS1iwraNf-RVhsbxXUde1g')

# Масив для збереження скарг
complaints = []

# Словник для відстеження активних скарг
active_complaints = {}

# Структура скарги
class Complaint:
    def __init__(self, name=None, city=None, number=None, text=None, media=None, is_anonymous=False):
        self.name = name
        self.city = city
        self.number = number
        self.text = text
        self.media = media if media else []
        self.is_anonymous = is_anonymous

# Обробник для стартової команди
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton('Створити скаргу', callback_data='create_complaint')
    markup.add(btn1)

    btn2 = types.InlineKeyboardButton('Переглянути Ваші заявки', callback_data='view_complaints')
    markup.add(btn2)

    bot.send_message(message.chat.id, 'Вас вітає система агрегації корупційних скарг', reply_markup=markup)

# Обробник для callback-даних
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == 'create_complaint':
        markup = types.InlineKeyboardMarkup()
        anon_btn = types.InlineKeyboardButton('Створити анонімну скаргу', callback_data='anonymous_complaint')
        data_btn = types.InlineKeyboardButton('Створити скаргу з даними', callback_data='data_complaint')
        markup.add(anon_btn, data_btn)
        bot.send_message(call.message.chat.id, 'Оберіть тип заявки:', reply_markup=markup)

    elif call.data == 'view_complaints':
        if complaints:
            for c in complaints:
                media_info = f"Медіа файли: {len(c.media)} файл(ів)" if c.media else "Немає медіа файлів"
                if c.is_anonymous:
                    bot.send_message(call.message.chat.id, f"Скарга (анонімна): {c.text}\n{media_info}")
                else:
                    bot.send_message(call.message.chat.id,
                                     f"Скарга від {c.name} ({c.city}, {c.number}): {c.text}\n{media_info}")
        else:
            bot.send_message(call.message.chat.id, 'Немає заявок.')

    elif call.data == 'anonymous_complaint':
        bot.send_message(call.message.chat.id, 'Будь ласка, напишіть текст Вашої скарги.')
        bot.register_next_step_handler(call.message, handle_anonymous_complaint)

    elif call.data == 'data_complaint':
        bot.send_message(call.message.chat.id, 'Будь ласка, вкажіть своє ім\'я.')
        bot.register_next_step_handler(call.message, handle_complaint_name)

# Обробник анонімної скарги
def handle_anonymous_complaint(message):
    complaint_text = message.text
    complaint = Complaint(text=complaint_text, is_anonymous=True)
    complaints.append(complaint)
    active_complaints[message.chat.id] = complaint
    bot.send_message(message.chat.id,
                     'Ваша анонімна скарга була успішно відправлена.\nТепер можете прикріпити медіа (фото, відео, аудіо) або натисніть /done для завершення.')
    bot.register_next_step_handler(message, handle_media_attachment)

# Обробники для скарги з даними
def handle_complaint_name(message):
    name = message.text
    bot.send_message(message.chat.id, 'Будь ласка, вкажіть місто.')
    bot.register_next_step_handler(message, handle_complaint_city, name)

def handle_complaint_city(message, name):
    city = message.text
    bot.send_message(message.chat.id, 'Будь ласка, вкажіть номер телефону.')
    bot.register_next_step_handler(message, handle_complaint_number, name, city)

def handle_complaint_number(message, name, city):
    number = message.text
    bot.send_message(message.chat.id, 'Будь ласка, напишіть текст Вашої скарги.')
    bot.register_next_step_handler(message, handle_complaint_text, name, city, number)

def handle_complaint_text(message, name, city, number):
    complaint_text = message.text
    complaint = Complaint(name=name, city=city, number=number, text=complaint_text)
    complaints.append(complaint)
    active_complaints[message.chat.id] = complaint
    bot.send_message(message.chat.id,
                     'Текст для скарги додано.\nТепер можете прикріпити медіа (фото, відео, аудіо) або натисніть /done для завершення.')
    bot.register_next_step_handler(message, handle_media_attachment)

# Обробник медіа файлів
@bot.message_handler(content_types=['photo', 'video', 'audio'])
def handle_media_attachment(message):
    complaint = active_complaints.get(message.chat.id)
    if not complaint:
        bot.send_message(message.chat.id, 'Немає активної скарги для додавання медіа.')
        return

    if message.text and message.text == '/done':
        done(message)
        return

    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        complaint.media.append(file_id)
        bot.send_message(message.chat.id, 'Фото успішно додано до скарги.')
    elif message.content_type == 'video':
        file_id = message.video.file_id
        complaint.media.append(file_id)
        bot.send_message(message.chat.id, 'Відео успішно додано до скарги.')
    elif message.content_type == 'audio':
        file_id = message.audio.file_id
        complaint.media.append(file_id)
        bot.send_message(message.chat.id, 'Аудіо успішно додано до скарги.')

    bot.send_message(message.chat.id, 'Якщо бажаєте, можете додати ще медіа або натисніть /done для завершення.')

# Об'єднаний обробник для завершення додавання медіа
@bot.message_handler(commands=['done'])
def done(message):
    complaint = active_complaints.get(message.chat.id)
    if complaint:
        send_complaint_to_backend(complaint)
        del active_complaints[message.chat.id]
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.send_message(message.chat.id, 'Скарга успішно збережена та відправлена на сервер.')
    else:
        bot.send_message(message.chat.id, 'Немає активної скарги для завершення.')

@bot.message_handler(commands=['menu'])
def show_menu(message):
    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton('Створити скаргу', callback_data='create_complaint')
    markup.add(btn1)

    btn2 = types.InlineKeyboardButton('Переглянути Ваші заявки', callback_data='view_complaints')
    markup.add(btn2)

    bot.send_message(message.chat.id, 'Оберіть дію:', reply_markup=markup)

def send_complaint_to_backend(complaint):
    url = 'http://localhost:8080/api/reports/create'
    data = {
        "name": complaint.name,
        "city": complaint.city,
        "number": complaint.number,
        "text": complaint.text,
        "filesUrls": complaint.media
    }
    print(data)

    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print("Скаргу успішно надіслано на бекенд!")
        else:
            print(f"Не вдалося надіслати скаргу. Статус-код: {response.status_code}")
    except Exception as e:
        print(f"Сталася помилка під час надсилання скарги: {e}")

bot.polling(none_stop=True)
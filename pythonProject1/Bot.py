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
    def __init__(self, name=None, last_name=None, city=None, phone=None, text=None, is_anonymous=False, media=None):
        self.name = name
        self.last_name = last_name
        self.city = city
        self.phone = phone
        self.text = text
        self.is_anonymous = is_anonymous
        self.media = media if media else []

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
                                     f"Скарга від {c.name} {c.last_name} ({c.city}, {c.phone}): {c.text}\n{media_info}")
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
    # Ініціалізуємо порожній список медіа, якщо ще не зроблено
    if not complaint.media:
        complaint.media = []
    bot.register_next_step_handler(message, handle_media_attachment)

# Обробники для скарги з даними
def handle_complaint_name(message):
    name = message.text
    bot.send_message(message.chat.id, 'Будь ласка, вкажіть своє прізвище.')
    bot.register_next_step_handler(message, handle_complaint_last_name, name)

def handle_complaint_last_name(message, name):
    last_name = message.text
    bot.send_message(message.chat.id, 'Будь ласка, вкажіть місто.')
    bot.register_next_step_handler(message, handle_complaint_city, name, last_name)

def handle_complaint_city(message, name, last_name):
    city = message.text
    bot.send_message(message.chat.id, 'Будь ласка, вкажіть номер телефону.')
    bot.register_next_step_handler(message, handle_complaint_phone, name, last_name, city)

def handle_complaint_phone(message, name, last_name, city):
    phone = message.text
    bot.send_message(message.chat.id, 'Будь ласка, напишіть текст Вашої скарги.')
    bot.register_next_step_handler(message, handle_complaint_text, name, last_name, city, phone)

def handle_complaint_text(message, name, last_name, city, phone):
    complaint_text = message.text
    complaint = Complaint(name=name, last_name=last_name, city=city, phone=phone, text=complaint_text)
    complaints.append(complaint)
    active_complaints[message.chat.id] = complaint
    bot.send_message(message.chat.id,
                     'Текст для скарги додано.\nТепер можете прикріпити медіа (фото, відео, аудіо) або натисніть /done для завершення.')
    # Ініціалізуємо порожній список медіа, якщо ще не зроблено
    if not complaint.media:
        complaint.media = []
    bot.register_next_step_handler(message, handle_media_attachment)

# Обробник медіа файлів
@bot.message_handler(content_types=['photo', 'video', 'audio'])
def handle_media_attachment(message):
    complaint = active_complaints.get(message.chat.id)
    if not complaint:
        bot.send_message(message.chat.id, 'Немає активної скарги для додавання медіа.')
        return

    # Перевіряємо, чи користувач не завершив додавання скарги
    if message.text and message.text == '/done':
        done(message)
        return

    # Обробляємо медіа, якщо ще не завершено
    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id  # Отримуємо ID найбільшого фото
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
        send_complaint_to_backend(complaint)  # Відправляємо скаргу на бекенд
        del active_complaints[message.chat.id]  # Видаляємо активну скаргу
        bot.clear_step_handler_by_chat_id(message.chat.id)  # Очищаємо обробники для цього чату
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
    url = 'http://localhost:8080/api/complaints/submit'  # Замість localhost, додайте ваш сервер
    data = {
        "name": complaint.name,
        "lastName": complaint.last_name,
        "city": complaint.city,
        "phoneNumber": complaint.phone,
        "complaintText": complaint.text,
        "media": complaint.media  # список медіа файлів як список рядків
    }

    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print("Complaint sent successfully to the backend!")
        else:
            print(f"Failed to send complaint. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error occurred while sending complaint: {e}")

bot.polling(none_stop=True)

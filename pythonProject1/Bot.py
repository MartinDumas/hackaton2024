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
    def __init__(self, user_id, name=None, surname= None, fathersname = None, region=None,  number=None, category=None, text=None, media=None, is_anonymous=False, information_about_user=None, status="На розгляді"):
        self.user_id = user_id
        self.name = name
        self.surname = surname
        self.fathersname = fathersname
        self.region = region
        self.number = number
        self.category = category
        self.text = text
        self.media = media if media else []
        self.is_anonymous = is_anonymous
        self.information_about_user = information_about_user
        self.status = status

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
        category_buttons = [
            types.InlineKeyboardButton('Корупція', callback_data='category_Корупція'),
            types.InlineKeyboardButton('Шахрайство', callback_data='category_Шахрайство'),
            types.InlineKeyboardButton('Зловживання владою', callback_data='category_Зловживання владою'),
            types.InlineKeyboardButton('Інше', callback_data='category_Інше')
        ]
        markup.add(*category_buttons)
        bot.send_message(call.message.chat.id, 'Оберіть категорію для скарги:', reply_markup=markup)

    elif call.data.startswith('category_'):
        category = call.data.split('_')[1]
        active_complaints[call.message.chat.id] = {"category": category}
        markup = types.InlineKeyboardMarkup()
        anon_btn = types.InlineKeyboardButton('Створити анонімну скаргу', callback_data='anonymous_complaint')
        data_btn = types.InlineKeyboardButton('Створити скаргу з даними', callback_data='data_complaint')
        markup.add(anon_btn, data_btn)
        bot.send_message(call.message.chat.id, 'Оберіть тип заявки:', reply_markup=markup)

    elif call.data == 'view_complaints':
        user_complaints = [c for c in complaints if c.user_id == call.message.chat.id]
        if user_complaints:
            for c in user_complaints:
                media_info = f"Медіа файли: {len(c.media)} файл(ів)" if c.media else "Немає медіа файлів"
                user_info = f"Додаткова інформація про користувача: {c.information_about_user}" if c.information_about_user else "Додаткова інформація не вказана"
                if c.is_anonymous:
                    bot.send_message(call.message.chat.id, f"Скарга (анонімна): {c.text}\n{media_info}\n{user_info}\nСтатус: {c.status}")
                else:
                    bot.send_message(call.message.chat.id, f"Скарга від {c.name} ({c.region},{c.city},{c.number}, \n{user_info}): {c.text}\n{media_info}\nСтатус: {c.status}")
        else:
            bot.send_message(call.message.chat.id, 'Немає заявок.')

    elif call.data == 'anonymous_complaint':
        bot.send_message(call.message.chat.id, 'Будь ласка, напишіть текст Вашої скарги.')
        bot.register_next_step_handler(call.message, handle_anonymous_complaint)

    elif call.data == 'data_complaint':
        bot.send_message(call.message.chat.id, 'Будь ласка, вкажіть своє ім\'я.')
        bot.register_next_step_handler(call.message, handle_complaint_name)
    elif call.data.startswith('region_'):
        region = call.data.split('_')[1]
        chat_data = active_complaints.get(call.message.chat.id)
        chat_data['region'] = region
        bot.send_message(call.message.chat.id, 'Будь ласка, вкажіть номер телефону')
        bot.register_next_step_handler(call.message, handle_complaint_number, chat_data['name'], chat_data['surname'],
                                       chat_data['fathersname'], region)


# Обробник анонімної скарги
def handle_anonymous_complaint(message):
    complaint_text = message.text
    chat_data = active_complaints.get(message.chat.id, {})
    category = chat_data.get("category")
    complaint = Complaint(user_id=message.chat.id, text=complaint_text, is_anonymous=True, category=category)
    complaints.append(complaint)
    active_complaints[message.chat.id] = complaint
    bot.send_message(message.chat.id, 'Бажаєте залишити персональні дані для зворотного зв\'язку? Або ж натисніть кнопку /skip для пропуску')
    bot.register_next_step_handler(message, handle_user_information)

# Обробник для введення персональних даних
def handle_user_information(message):
    complaint = active_complaints.get(message.chat.id)
    if complaint:
        if message.text.lower() == '/skip':
            complaint.information_about_user = None
            bot.send_message(message.chat.id, 'Персональні дані пропущено. Тепер можете прикріпити медіа.')
        else:
            complaint.information_about_user = message.text
            bot.send_message(message.chat.id, 'Ваші персональні дані успішно збережено.')
        bot.send_message(message.chat.id, 'Тепер можете прикріпити медіа (фото, відео, аудіо) або натисніть /done для завершення.')
        bot.register_next_step_handler(message, handle_media_attachment)

# Обробники для скарги з даними
def handle_complaint_name(message):
    name = message.text
    bot.send_message(message.chat.id, 'Будь ласка, вкажіть прізвище')
    bot.register_next_step_handler(message, handle_complaint_surname, name)

def handle_complaint_surname(message, name):
    surname = message.text
    bot.send_message(message.chat.id, 'Будь ласка, вкажіть по батькові')
    bot.register_next_step_handler(message, handle_complaint_fathersname, name,surname)

def handle_complaint_fathersname(message, name, surname):
    fathersname = message.text
    active_complaints[message.chat.id] = {"name": name, "surname": surname, "fathersname": fathersname}
    show_region_selection(message)

def show_region_selection(message):
    markup = types.InlineKeyboardMarkup()
    regions = [
        'Київ', 'Львів', 'Одеса', 'Дніпро', 'Харків', 'Запоріжжя', 'Вінниця', 'Полтава',
        'Чернігів', 'Івано-Франківськ', 'Луганськ', 'Донецьк', 'Рівне', 'Херсон',
        'Хмельницький', 'Чернівці', 'Суми', 'Житомир', 'Черкаси', 'Миколаїв', 'Тернопіль',
        'Волинь', 'Закарпаття'
    ]
    buttons = [types.InlineKeyboardButton(region, callback_data=f'region_{region}') for region in regions]
    markup.add(*buttons)
    bot.send_message(message.chat.id, 'Оберіть область', reply_markup=markup)

def handle_complaint_number(message, name,surname, fathersname, region, ):
    number = message.text
    bot.send_message(message.chat.id, 'Будь ласка, напишіть текст Вашої скарги.')
    bot.register_next_step_handler(message, handle_complaint_text, name, surname, fathersname, region,  number)

def handle_complaint_text(message, name, surname, fathersname, region,  number):
    complaint_text = message.text
    chat_data = active_complaints.get(message.chat.id, {})
    category = chat_data.get("category")
    complaint = Complaint(user_id=message.chat.id, name=name, surname= surname, fathersname= fathersname, region=region,  number=number, text=complaint_text, category=category)
    complaints.append(complaint)
    active_complaints[message.chat.id] = complaint
    bot.send_message(message.chat.id, 'Текст для скарги додано.\nБажаєте залишити персональні дані для зворотного зв\'язку? Або ж натисніть кнопку /skip для пропуску')
    bot.register_next_step_handler(message, handle_user_information)

# Обробник медіа файлів
@bot.message_handler(content_types=['photo', 'video', 'audio'])
def handle_media_attachment(message):
    complaint = active_complaints.get(message.chat.id)
    if not complaint:
        bot.send_message(message.chat.id, 'Немає активної скарги для додавання медіа.')
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

    bot.send_message(message.chat.id, 'Можете прикріпити ще медіа або натисніть /done для завершення.')

# Обробник для команди /done
@bot.message_handler(commands=['done'])
def handle_done(message):
    complaint = active_complaints.pop(message.chat.id, None)
    send_complaint_to_backend(complaint)
    if complaint:
        bot.send_message(message.chat.id, 'Скаргу успішно надіслано. Дякуємо за вашу участь.')
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
        "category" : complaint.category,
        "name": complaint.name,
        "surname": complaint.surname,
        "fathersname": complaint.fathersname,
        "region": complaint.region,
        "number": complaint.number,
        "text": complaint.text,
        "information": complaint.information_about_user,
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
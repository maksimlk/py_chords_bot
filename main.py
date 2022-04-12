import telebot
from telebot import types
import sqlite3
import requests
from bs4 import BeautifulSoup
import pandas as pd
from matplotlib.ticker import MaxNLocator
import datetime

TG_BOT_ID = "TG ID"

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
})

start_message = "Вас преветствует chords bot, этот бот был создан для поиска аккордов для разных инструментов и песен." \
                " Просим вас выбрать ваш инструмент:"
active_message = "Выберите действие"
help_message = "Этот бот преднозначен для поиска аккордов песен, а также для поиска схем аккордов для выбранного " \
               "инструмента. \n"

instruments = ["гитара", "укулеле"]
chords = ['Am', 'Dm', 'Em', 'E', 'F', 'G', 'A', 'C']

bot = telebot.TeleBot(TG_BOT_ID)

conn = sqlite3.connect('chords.db')

cursor = conn.cursor()

try:
    query = "CREATE TABLE \"chords\" (\"ID\" INTEGER UNIQUE, \"user_id\" TEXT, \"instrument\" TEXT, \"registered\" TEXT, PRIMARY KEY (\"ID\"))"
    cursor.execute(query)
except:
    pass


def load_guitar_chord_class_page(chord):
    if chord == 'B':
        chord = 'H'
    url = 'https://tuneronline.ru/chords/' + chord.lower()
    request = requests.get(url, headers=s.headers)
    return request.text


def get_ukulele_chord_img(chord):
    url = 'https://gitaraclub.ru/blog/akkordy-ukulele/'
    request = requests.get(url, headers=s.headers)
    page = request.text
    soup = BeautifulSoup(str(page), features="html.parser")
    chords_soup = soup.find_all('td')
    for chord_soup in chords_soup:
        soup1 = BeautifulSoup(str(chord_soup), features="html.parser")
        if len(str(soup1.find('img').get('alt')).split()) > 1:
            if str(soup1.find('img').get('alt')).split()[1] == chord:
                return soup1.find('img').get('src')
        if len(str(soup1.find('img').get('alt')).split('-')) > 1:
            if str(soup1.find('img').get('alt')).split('-')[1] == chord:
                return soup1.find('img').get('src')
    return None


def get_guitar_chord_img(chord):
    page = load_guitar_chord_class_page(chord[0])
    if chord[0] == 'B':
        chord = 'H' + chord.lower()
    soup = BeautifulSoup(str(page), features="html.parser")
    chords_soup = soup.find_all('div', {'class': 'chords1'})
    for chord_soup in chords_soup:
        soup1 = BeautifulSoup(str(chord_soup), features="html.parser")
        if soup1.find('h3', {'class': 'chordsh3'}).text == chord:
            return soup1.find('img', {'class': 'crd'}).get('src')


def set_instrument(msg):
    if msg.text not in instruments:
        send_keyboard(msg, "Выберите правильный инструмент")
        return
    with sqlite3.connect('chords.db') as con:
        cursor = con.cursor()
        cursor.execute('SELECT EXISTS(SELECT * from chords WHERE user_id=(?))', (msg.from_user.id,))
        temp = cursor.fetchone()
        if temp[0] == 1:
            cursor.execute('UPDATE chords SET instrument = ? WHERE user_id = ?',
                           (msg.text, msg.from_user.id))
        else:
            temp = datetime.datetime.now().date()
            cursor.execute('INSERT INTO chords (user_id, instrument, registered) VALUES (?, ?, ?)',
                           (msg.from_user.id, msg.text, temp))
        con.commit()
    main_keyboard(msg, "Ваш инструмент: " + msg.text)


@bot.message_handler(commands=['start'])
def send_keyboard(message, text=start_message, function=set_instrument):
    keyboard = types.ReplyKeyboardMarkup(row_width=1)  # наша клавиатура
    for instrument in instruments:
        keyboard.add(instrument)
    msg = bot.send_message(message.from_user.id,
                           text=text, reply_markup=keyboard)
    bot.register_next_step_handler(msg, function)


def active_keyboard(message, text=active_message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2)  # наша клавиатура
    itembtn1 = types.KeyboardButton('Найти песню')  # создадим кнопку
    itembtn2 = types.KeyboardButton('Найти аккорд')
    itembtn3 = types.KeyboardButton('выйти')
    keyboard.add(itembtn1, itembtn2, itembtn3)
    msg = bot.send_message(message.from_user.id,
                           text=text, reply_markup=keyboard)
    bot.register_next_step_handler(msg, choose_active)


def main_keyboard(message, text=active_message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2)  # наша клавиатура
    itembtn1 = types.KeyboardButton('К поиску')  # создадим кнопку
    itembtn2 = types.KeyboardButton('Выбрать инструмент')
    itembtn3 = types.KeyboardButton('Мой инструмент')
    itembtn4 = types.KeyboardButton('Помощь')
    itembtn5 = types.KeyboardButton('Статистика')
    keyboard.add(itembtn1, itembtn2, itembtn3, itembtn4, itembtn5)
    msg = bot.send_message(message.from_user.id,
                           text=text, reply_markup=keyboard)
    bot.register_next_step_handler(msg, choose_main)


def choose_active(msg):
    if msg.text == "Найти песню":
        find_song(msg)
        return
    elif msg.text == "Найти аккорд":
        find_chord(msg)
        return
    elif msg.text == "выйти":
        main_keyboard(msg)
        return
    active_keyboard(msg, "Выберите правильную комманду")


def find_song(msg):
    msg = bot.send_message(msg.from_user.id,
                           text="Напишите название песни или имя автора", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, get_songs_list)


def get_songs_list(msg):
    url = 'https://amdm.ru/search/?q=' + str(msg.text).replace(' ', '+')
    request = requests.get(url, headers=s.headers)
    page = request.text
    soup = BeautifulSoup(str(page), features="html.parser")
    songs = soup.find_all('tr', {'class': None})
    songs_list = list()
    urls_list = list()
    if len(songs) == 0:
        active_keyboard(msg, 'Простите, мы не можем найти песню с таким названием')
        return
    if len(songs) > 5:
        songs = songs[:5]
    for song in songs:
        soup1 = BeautifulSoup(str(song), features="html.parser").find('td', {'class', 'artist_name'})
        songs_list.append(soup1.text)
        song_a = soup1.find_all('a')
        url = BeautifulSoup(str(song_a[1]), features="html.parser").find('a').get('href')
        urls_list.append(url)
    keyboard = types.InlineKeyboardMarkup()
    i = 0
    while i < len(songs_list):
        keyboard.add(types.InlineKeyboardButton(str(songs_list[i])[:64], callback_data=str(urls_list[i])))
        i += 1
    keyboard.add(types.InlineKeyboardButton('выйти', callback_data='exit'))
    bot.send_message(msg.from_user.id,
                     text="Выберите вариант из предложенного", reply_markup=keyboard)


def get_song_text(url):
    request = requests.get('https:' + str(url), headers=s.headers)
    page = request.text
    soup = BeautifulSoup(str(page), features="html.parser")
    return soup.find('pre').text


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == 'exit':
        active_keyboard(call)
    else:
        text = get_song_text(call.data)
        bot.send_message(call.from_user.id,
                         text=text)
        active_keyboard(call)


def choose_main(msg):
    if msg.text == "К поиску":
        active_keyboard(msg)
        return
    elif msg.text == "Выбрать инструмент":
        send_keyboard(msg, "Выберите инструмент", update_instrument)
        return
    elif msg.text == "Мой инструмент":
        get_instrument(msg, True)
        return
    elif msg.text == "Помощь":
        main_keyboard(msg, help_message)
        return
    elif msg.text == "Статистика":
        send_stats(msg)
        return
    main_keyboard(msg, "Выберите правильную комманду")


def update_instrument(msg):
    if msg.text not in instruments:
        send_keyboard(msg, "Выберите правильный инструмент", update_instrument)
        return
    with sqlite3.connect('chords.db') as con:
        cursor = con.cursor()
        cursor.execute('UPDATE chords SET instrument=? WHERE user_id=?',
                       (msg.text, msg.from_user.id))
        con.commit()
    main_keyboard(msg, "Ваш инструмент: " + msg.text + ". Для просмотра своего инструмента введите")


def find_chord(msg):
    keyboard = types.ReplyKeyboardMarkup(row_width=4)  # наша клавиатура
    itembtn1 = types.KeyboardButton('Am')  # создадим кнопку
    itembtn2 = types.KeyboardButton('Dm')
    itembtn3 = types.KeyboardButton('Em')
    itembtn4 = types.KeyboardButton('E')
    itembtn5 = types.KeyboardButton('F')
    itembtn6 = types.KeyboardButton('G')
    itembtn7 = types.KeyboardButton('A')
    itembtn8 = types.KeyboardButton('C')
    itembtn9 = types.KeyboardButton('D')
    itembtn10 = types.KeyboardButton('Bm')
    itembtn11 = types.KeyboardButton('H7')
    itembtn12 = types.KeyboardButton('D7')

    keyboard.add(itembtn1, itembtn2, itembtn3, itembtn4, itembtn5, itembtn6, itembtn7, itembtn8, itembtn9, itembtn10,
                 itembtn11, itembtn12)

    msg = bot.send_message(msg.from_user.id,
                           text="Выберите аккорд или напишите свой", reply_markup=keyboard)

    bot.register_next_step_handler(msg, get_chord)


def get_instrument(msg, a=False):
    with sqlite3.connect('chords.db') as con:
        cursor = con.cursor()
        instrument = cursor.execute(
            'SELECT instrument FROM chords WHERE user_id=={}'.format(msg.from_user.id)).fetchone()
        if a:
            bot.send_message(msg.chat.id, instrument)
            main_keyboard(msg)
        return instrument[0]


def get_chord(msg):
    instrument = get_instrument(msg)
    if instrument == "гитара":
        get_guitar_chord(msg)
        return
    elif instrument == "укулеле":
        get_ukulele_chord(msg)
        return
    bot.send_message(msg.from_user.id,
                     text="Извините, мы не смогли найти данный аккорд")


def get_guitar_chord(msg):
    url_part = get_guitar_chord_img(msg.text)
    if url_part is None or url_part == '':
        active_keyboard(msg, 'Извините, мы не можем найти такой аккорд, что вы хотите сделать теперь?')
        return
    url = 'https:' + str(url_part)
    bot.send_photo(msg.from_user.id, url)
    active_keyboard(msg)


def get_ukulele_chord(msg):
    url_part = get_ukulele_chord_img(msg.text)
    if url_part is None or url_part == '':
        active_keyboard(msg, 'Извините, мы не можем найти такой аккорд, что вы хотите сделать теперь?')
        return
    url = 'https:' + str(url_part)
    bot.send_photo(msg.from_user.id, url)
    active_keyboard(msg)


def send_stats(msg):
    with sqlite3.connect('chords.db') as con:
        # Инстурменты, которые используют пользователи
        temp = pd.read_sql(con=con, sql="SELECT * FROM chords")
        fig1 = temp['instrument'].value_counts().plot(kind='bar', figsize=(20, 16), fontsize=26)
        fig1.set_title('Музыкальные инструменты у использующих данного бота', fontsize=22)
        fig1.set_ylabel('Количество людей', fontsize=20)
        fig1.yaxis.set_major_locator(MaxNLocator(integer=True))
        fig1.get_figure().savefig('temp1.png')
        bot.send_photo(msg.from_user.id, photo=open('temp1.png', 'rb'))
        bot.send_message(msg.from_user.id,
                         text="Лови информацию о количестве людей использующих определённый инструмент")
        # Кол-во новых пользователей
        temp['registered'] = pd.to_datetime(temp['registered']).dt.date
        fig2 = temp.loc[temp.registered > (pd.to_datetime(datetime.datetime.now().date()) - pd.to_timedelta("7day"))][
            'registered'].value_counts().plot(kind='bar', figsize=(20, 16), fontsize=26)
        fig2.set_title('Кол-во зарегистрированных пользователей за последние 7 дней', fontsize=22)
        fig2.yaxis.set_major_locator(MaxNLocator(integer=True))
        fig2.get_figure().savefig('temp2.png')
        bot.send_photo(msg.from_user.id, photo=open('temp2.png', 'rb'))
        bot.send_message(msg.from_user.id,
                         text="И ещё количество новых пользователей ежедневно")

    main_keyboard(msg, 'Что вы хотите сделать теперь?')


bot.polling(none_stop=True)

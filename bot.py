import telebot
import config
from natasha import Doc, Segmenter, MorphVocab, NewsEmbedding, NewsMorphTagger
from deeppavlov import configs, build_model

from parse.horoscope_parser import HoroscopeParser
from parse.user import User


bot = telebot.TeleBot(config.BOT_TOKEN)
ner_model = build_model(configs.ner.ner_ontonotes_bert_mult, download=True)
horoscope_parser = HoroscopeParser()

user_dict = {}

segmenter = Segmenter()
emb = NewsEmbedding()
morph_tagger = NewsMorphTagger(emb)
morph_vocab = MorphVocab()


@bot.message_handler(commands=['start'])  # Функция отвечает на команду 'start'
def start_message(message):
    bot.send_message(message.chat.id,
                    f"Привет! \n"
                    f"Я расскажу всё, что знают звезды. Могу прислать твой персональный <b>гороскоп</b> 🔮\n"
                    f"Чтобы узнать полный список команд, напиши /help \n"
                    f"Чтобы закончить диалог, напиши /exit\n",
                    parse_mode='HTML')


@bot.message_handler(commands=['help'])  # Функция отвечает на команду 'help'
def help_message(message):
    bot.send_message(message.chat.id,
                 f"<b>Я знаю следующие команды</b>:\n\n"
                 f"/help - <i>Повторить это сообщение</i>\n\n"
                 f"/exit - <i>Выход</i>\n\n"
                 f"Если хочешь узнать гороскоп -- напиши мне об этом, я тебя пойму!",
                 parse_mode='HTML')


@bot.message_handler(commands=['exit'])  # Функция отвечает на команду 'exit'
def end_message(message):
    user_dict[message.chat.id].needs_greet = True
    bot.send_message(message.chat.id,
                     f"Рада была помочь! До встречи!\n")


def is_bye(message):
    message = Doc(message.text)
    message.segment(segmenter)
    message.tag_morph(morph_tagger)
    cnt = 0
    for token in message.tokens:
        token.lemmatize(morph_vocab)
        if token.lemma.lower() in ['пока', 'свидание']:
            cnt += 1
    return cnt


@bot.message_handler(content_types=['text'])  # Функция обрабатывает текстовые сообщения
def get_text(message):
    chat_id = message.chat.id
    
    if chat_id not in user_dict:
        user_dict[chat_id] = User()
    
    if is_bye(message):
        user_dict[chat_id].needs_greet = True
        bot.send_message(chat_id, "Рада была помочь! До встречи!")
        return
    
    if user_dict[chat_id].needs_greet:
        user_dict[chat_id].needs_greet = False
        bot.send_message(chat_id, "Привет!")

    # query classification
    horoscope_cnt = 0
    doc = Doc(message.text)
    doc.segment(segmenter)
    doc.tag_morph(morph_tagger)
    for token in doc.tokens:
        token.lemmatize(morph_vocab)
        if token.lemma in horoscope_parser.keywords:
            horoscope_cnt += 1
        
    if horoscope_cnt == 0:
        bot.reply_to(message, 'Я не поняла, чего вы от меня хотите((((\n'
                                'Спросите, пожалуйста, еще раз как-нибудь по-другому')
        return
    
    else:
        process_horoscope_step(message)
        return
        

def process_horoscope_step(message):
    horo_date = horoscope_parser.process_date(message.text, ner_model)
    user_dict[message.chat.id].horo_date = horo_date

    # try to find horo sign
    horo_sign = horoscope_parser.process_sign(message.text)
    if horo_sign is None:
        msg = bot.reply_to(message, 'Назови знак зодиака 🔮')
        bot.register_next_step_handler(msg, process_sign_step)
    else:
        user_dict[message.chat.id].horo_sign = horo_sign
        generate_horo(message)


def process_sign_step(message):
    chat_id = message.chat.id
    horo_sign = horoscope_parser.process_sign(message.text)
    if horo_sign is None:
        msg = bot.reply_to(message, 'Попробуй еще! Назови знак зодиака 🔮')
        bot.register_next_step_handler(msg, process_sign_step)
        return
    user_dict[chat_id].horo_sign = horo_sign
    generate_horo(message)


def generate_horo(message):
    chat_id = message.chat.id
    # get horoscope
    horo_date, horo_sign = user_dict[chat_id].horo_date, user_dict[chat_id].horo_sign
    bot.send_message(chat_id,
                     text='Предсказание почти готово... 🧙‍♀️\n')
    final_horo = horoscope_parser.get_horo(horo_date, horo_sign)
    # send horoscope to user
    bot.send_message(chat_id,
                     text=final_horo)

    # clear for opportunity to get new horo
    user_dict[chat_id].horo_date, user_dict[chat_id].horo_sign = None, None
    bot.send_message(chat_id,
                     text='Я могу еще чем-то помочь?\nЕсли нет, то попрощайся со мной или напиши /exit')

bot.polling(none_stop=True, interval=0)

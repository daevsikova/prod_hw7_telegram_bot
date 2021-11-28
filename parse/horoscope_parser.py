import urllib.request
import json

import pymorphy2
import nltk
from rutimeparser import parse
import datetime
from dateutil import parser


class HoroscopeParser:
    url = 'https://zeapi.yandex.net/lab/api/yalm/text3'
    headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_4) AppleWebKit/605.1.15 '
                  '(KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Origin': 'https://yandex.ru',
    'Referer': 'https://yandex.ru/',
    }
    
    morph = pymorphy2.MorphAnalyzer()
    tokenizer = nltk.tokenize.TreebankWordTokenizer()

    horo_signs = {'овен': 'овен', 'телец': 'телец',
                  'близнец': 'близнецы', 'рак': 'рак',
                  'лев': 'лев', 'дева': 'дева',
                  'вес': 'весы', 'весы': 'весы',
                  'скорпион': 'скорпион', 'стрелец': 'стрелец',
                  'козерог': 'козерог', 'водолей': 'водолей',
                  'рыбы': 'рыбы', 'рыба': 'рыбы'}
    keywords = ["гороскоп", "предсказание", "судьба", "астрологический"]
    
    tags = ['B-TIME', 'I-TIME', 'B-DATE', 'I-DATE']

    def process_date(self, message, ner_model):
        date = parse(message)

        if date is None:
            date = ''
            result = ner_model([message])
            for idx in [i for i, el in enumerate(result[1][0]) if el in self.tags]:
                date += result[0][0][idx]
            date = '' if not date else parser.parse(date).date()

        if not date or date < datetime.datetime.now().date():
            date = datetime.datetime.now().date()
        return date

    def process_sign(self, message):
        result = self._tokenize_text(message)
        sign = [word for word in result if word in self.horo_signs]
        if not sign:
            return None
        return self.horo_signs[sign[0]]

    def get_horo(self, date, horo_sign):
        data = {"query": f"Гороскоп {horo_sign} на {date}:", "intro": 0, "filter": 1}
        params = json.dumps(data).encode('utf8')
        req = urllib.request.Request(self.url, data=params, headers=self.headers)
        response = urllib.request.urlopen(req)

        text = response.read().decode('unicode-escape')
        d = dict(el.split('":') for el in text.strip('{}').split(',"'))
        horo = d['text'].strip('"')
        
        cnt = 0
        idx = 0
        for sym in horo:
            idx += 1
            if sym == '.':
                cnt += 1
            if cnt == 2:
                break

        return horo[:idx]

    def _tokenize_text(self, text):
        words = self.tokenizer.tokenize(text)
        result = []

        for word in words:
            p = self.morph.parse(word)[0]
            result.append(p.normal_form)
        return result

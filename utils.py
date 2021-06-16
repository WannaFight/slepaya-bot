import json
import os
import random
from typing import List

import gensim
from fuzzywuzzy import process, fuzz
import keras
import numpy as np
import requests



def searcher(q: str, full_text: List[str], cutoff=85) -> List[str]:
    def custom_ratio(s1, s2):
        fratio = fuzz.UWRatio(s1, s2)
        if s1[0].lower() != s2[0].lower():
            fratio -= 25
        else:
            fratio += 10
        return fratio

    quotes_indices = []

    for i, sent in enumerate(full_text):
        try:
            if process.extractBests(q, filter(lambda x: abs(len(q)-len(x)) < 2 and len(x) > 2, sent.split()),
                                    score_cutoff=cutoff, scorer=custom_ratio):
                quotes_indices.append(i)
        except IndexError:
            continue

    return quotes_indices


def ending_decider(l: int, word_no_ending: str) -> str:
    ten_reminder = l % 10
    if ten_reminder == 1 and l != 11:
        return word_no_ending + 'у'
    elif ten_reminder in {2, 3, 4} and l not in {12, 13, 14}:
        return word_no_ending + 'ы'
    else:
        return word_no_ending


class QuotesModel:
    def __init__(self):
        self.model = keras.models.load_model('good_model.h5')
        self.word_model = gensim.models.Word2Vec.load('w2v.model')
        self.vars = json.loads(open('variables.json', 'r').read())

    def word2idx(self, word):
        return self.word_model.wv.key_to_index[word]

    def idx2word(self, idx):
        return self.word_model.wv.index_to_key[idx]

    def sample(self, predictions, temperature=0.75):
        if temperature <= 0:
            return np.argmax(predictions)
        predictions = np.asarray(predictions).astype('float64')
        predictions = np.log(predictions) / temperature
        exp_predictions = np.exp(predictions)
        predictions = exp_predictions / np.sum(exp_predictions)
        probas = np.random.multinomial(1, predictions, 1)

        return np.argmax(probas)

    def generate_next(self, num_generated=10, temp=0.75) -> str:
        text = random.choice(self.vars['beginings'])
        word_idxs = [self.word2idx(word) for word in text.lower().split()]

        for _ in range(num_generated):
            prediction = self.model.predict(x=np.array(word_idxs))
            idx = self.sample(prediction[-1], temperature=temp)
            word_idxs.append(idx)

        return ' '.join(self.idx2word(idx) for idx in word_idxs)

    def translate_generated(self, t: float, words: int, folder_id: str = os.getenv('FOLDER_ID', "b1geh42nvb0dfevai47f"),
                            texts: list = [], targetLanguageCode: str = "ru") -> str:
        body = {
            "folder_id": folder_id,
            "texts": texts if texts
                     else [self.generate_next(temp=t, num_generated=words) for _ in range(5)],
            "targetLanguageCode": targetLanguageCode
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"API-Key {os.getenv('YA_TOKEN')}"
        }

        resp = requests.post("https://translate.api.cloud.yandex.net/translate/v2/translate",
                             data=str(body), headers=headers)

        if resp.ok:
            for i in resp.json()['translations']:
                if ',' in i['text']:
                    return (200, i['text'])
            return (200, i['text'])
        else:
            return (400, resp.json()['message'])

from importlib import import_module
import pymysql
import json
from itertools import islice
import pandas as pd
import numpy as np
import math
import os
import jieba
import urllib.request
import jieba.posseg as pseg
import pickle as pkl
import torch
from IPython import embed

current_path = os.getcwd()

MAX_VOCAB_SIZE = 10000
UNK, PAD = '<UNK>', '<PAD>'

models = {'FastText_Y':{'path':current_path+'/models/FastText_Y.ckpt'},
          'FastText_V':{'path':current_path+'/models/FastText_V.ckpt'},
          'FastText_A':{'path':current_path+'/models/FastText_A.ckpt'},
          'FastText_S':{'path':current_path+'/models/FastText_S.ckpt'},
          'FastText_I':{'path':current_path+'/models/FastText_I.ckpt'}}

for key in models:
    print('Loading model [{}]'.format(key))
    tmp = import_module('models.' + key)
    config = tmp.Config("./", 'random')
    model = tmp.Model(config).to(config.device)

    # load ckpt
    model.load_state_dict(torch.load(models[key]['path'], map_location=torch.device('cpu')))
    

    models[key]['config'] = config
    models[key]['model'] = model  

class DatasetIterater(object):
    def __init__(self, batches, batch_size, device):
        self.batch_size = batch_size                 #一次进多少个句子
        self.batches = batches                       # 数据集
        self.n_batches = len(batches) // batch_size  # 数据集大小整除batch容量
        self.residue = False                         # 记录batch数量是否为整数
        # if len(batches) % self.n_batches != 0:
        self.residue = True
        self.index = 0
        self.device = device

    def _to_tensor(self, datas):
        # xx = [xxx[2] for xxx in datas]
        # indexx = np.argsort(xx)[::-1]
        # datas = np.array(datas)[indexx]
        x = torch.LongTensor([_[0] for _ in datas]).to(self.device)  # 句子words_line
        y = torch.LongTensor([_[1] for _ in datas]).to(self.device)  # 标签
        bigram = torch.LongTensor([_[3] for _ in datas]).to(self.device)
        trigram = torch.LongTensor([_[4] for _ in datas]).to(self.device)

        # pad前的长度(超过pad_size的设为pad_size，未超过的为原seq_size不变)
        seq_len = torch.LongTensor([_[2] for _ in datas]).to(self.device)
        return (x, seq_len, bigram, trigram), y

    def __next__(self):
        if self.residue and self.index == self.n_batches:    # 如果batch外还剩下一点句子，并且迭代到了最后一个batch
            batches = self.batches[self.index * self.batch_size: len(self.batches)]  #直接拿出剩下的所有数据
            self.index += 1
            batches = self._to_tensor(batches)
            return batches

        elif self.index >= self.n_batches:
            self.index = 0
            raise StopIteration
        else:    # 迭代器的入口，刚开始self.index是0，肯定小于self.n_batches
            batches = self.batches[self.index * self.batch_size: (self.index + 1) * self.batch_size]  # 正常取一个batch的数据
            self.index += 1
            batches = self._to_tensor(batches)
            return batches

    def __iter__(self):
        return self

    def __len__(self):
        if self.residue:
            return self.n_batches + 1
        else:
            return self.n_batches


def build_iterator(dataset, config):
    iter = DatasetIterater(dataset, config.batch_size, config.device)
    return iter

def build_dataset(config, test_data, ues_word=False):

    vocab_path = 'models/vocab.pkl'

    if ues_word:
        tokenizer = lambda x: x.split(' ')  # 以空格隔开，word-level
    else:
        tokenizer = lambda x: [y for y in x]  # char-level
    if os.path.exists(vocab_path):
        vocab = pkl.load(open(vocab_path, 'rb'))
    else:
        vocab = build_vocab(config.train_path, tokenizer=tokenizer, max_size=MAX_VOCAB_SIZE, min_freq=1)
        pkl.dump(vocab, open(config.vocab_path, 'wb'))
    print(f"Vocab size: {len(vocab)}")

    def biGramHash(sequence, t, buckets):
        t1 = sequence[t - 1] if t - 1 >= 0 else 0
        return (t1 * 14918087) % buckets

    def triGramHash(sequence, t, buckets):
        t1 = sequence[t - 1] if t - 1 >= 0 else 0
        t2 = sequence[t - 2] if t - 2 >= 0 else 0
        return (t2 * 14918087 * 18408749 + t1 * 14918087) % buckets

    def load_dataset(path, pad_size=52):
        contents = []
        for i, row in test_data.iterrows():
            words_line = []
            token = tokenizer(row['content_jieba_segment'])
            seq_len = len(token)
            if pad_size:
                if len(token) < pad_size:
                    token.extend([PAD] * (pad_size - len(token)))
                else:
                    token = token[:pad_size]
                    seq_len = pad_size
            # word to id
            for word in token:
                words_line.append(vocab.get(word, vocab.get(UNK)))

            # fasttext ngram
            buckets = config.n_gram_vocab
            bigram = []
            trigram = []
            # ------ngram------
            for i in range(pad_size):
                bigram.append(biGramHash(words_line, i, buckets))
                trigram.append(triGramHash(words_line, i, buckets))
            # -----------------
            contents.append((words_line, 0, seq_len, bigram, trigram))  #words_line，数字标签，元素数量，bigram，trigram
        return contents  # [([...], 0), ([...], 1), ...]
    test = load_dataset(test_data, config.pad_size)
    return vocab, test

def predict(test_data):
    vocab, test_data = build_dataset(models['FastText_I']['config'], test_data)


    # models['FastText_Y'].n_vocab = len(vocab)
    x = import_module('models.' + "FastText_I")
    config = x.Config("./", 'random')
    config.n_vocab = len(vocab)

    test_iter = build_iterator(test_data, config)


    predictions = {key:[] for key in models}
    for texts, labels in test_iter:
        for key in models:
            output = models[key]['model'](texts)
            output = torch.max(output.data, 1)[1].cpu().numpy()
            predictions[key].extend(output)
            



    return predictions

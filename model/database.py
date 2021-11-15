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
from predict import predict


URL = "http://github.com/fxsjy/jieba/raw/master/extra_dict/dict.txt.big"
if not os.path.exists(os.path.join(os.getcwd(),"dict.txt.big")):
    urllib.request.urlretrieve(URL,"dict.txt.big")
jieba.set_dictionary("dict.txt.big")

###特別注意！我現在使用的資料庫為暫時資料庫！所以可以隨意玩耍！
def db_operate():
    db = pymysql.connect(host='demo.jlwu.info',  # 主機名稱
                         port=1107,
                         database="BD109A_temp",
                         user="BD109A",
                         password="@vy4G9jcGAfaT6tAJ")
    return db



def get_lost_review(v_id,c_list):
    db = db_operate()
    cursor = db.cursor()


    combine_clist = ','.join(["'%s'" % item for item in c_list])

    sql = """Select review_id,text from total_review WHERE review_id IN (%s) """ %(combine_clist)
    cursor.execute(sql)
    test_data = cursor.fetchall()
    db.close()

    review = {}
    r_id = []
    text = []

    for row in test_data:
        review[row[0]] = row[1]
        r_id.append(row[0])
        text.append(row[1])
    data = pd.DataFrame(list(review.items()), columns=['r_id', 'text'])
    return data
##這裡我回傳方式有一種是字典{'r_id':'text'}，或是直接回傳兩個list，看你們要怎麼用
def get_review(v_id):
    db = db_operate()
    cursor = db.cursor()

    sql = """Select review_id,text from total_review WHERE video_id = '%s' """ % v_id
    cursor.execute(sql)
    test_data = cursor.fetchall()
    db.close()

    review = {}
    r_id = []
    text = []

    for row in test_data:
        review[row[0]] = row[1]
        r_id.append(row[0])
        text.append(row[1])
    data = pd.DataFrame(list(review.items()), columns=['r_id', 'text'])
    return data

def out_txt(data):
    new_col = []
    split_data = np.array(data.loc[:,:])

    for i in range(len(split_data)):

        if "\n" in split_data[i][1]:
            new = split_data[i][1].replace("\n"," ")

            if "\r" in new:
                new1 = new.replace("\r"," ")
                new_col.append(new1)
            else:
                new_col.append(new)

        elif "\r" in split_data[i][1]:
            new = split_data[i][1].replace("\r"," ")
            new_col.append(new)

        else:
            new_col.append(split_data[i][1])

    df = pd.DataFrame(new_col, columns =['content_combine'])
    df_com = pd.concat([df,data], axis=1)
    df_com = df_com[['r_id', 'content_combine']]
    df['content_jieba_segment']=''

    for a in range(len(df_com.index)):
        zh_annotated_ws = ' '.join(jieba.cut(df_com.iloc[a,1], cut_all=False))
        df_com.loc[a,"content_jieba_segment"] = zh_annotated_ws
    result = df_com.reindex(columns=['r_id','content_jieba_segment'])
    data = result
    return data



##這裡輸入（a,b,c,d,e,f）都是文字喔！
def insert_result_to_db(result,r_id,vid):
    try:
        db = db_operate()
        cursor = db.cursor()
        for i in range(len(result['FastText_Y'])):
            sql = """INSERT INTO result(r_id, yter_grade, v_grade, ex_grade, ir_grade, se_grade, v_id) \
                    VALUES ('%s','%s','%s','%s','%s','%s','%s')"""%(r_id[i], result['FastText_Y'][i]+1, result['FastText_V'][i]+1,result['FastText_A'][i]+1, result['FastText_S'][i]+1, result['FastText_I'][i]+1,vid)
            cursor.execute(sql)
            db.commit()
        db.close()
        message = 'success'
    except:
        message = 'fail'
    return message


def main(v_id="WyXWx9FLEp0"):
    data = get_review(v_id)
    data = out_txt(data)
    result = predict(data)
    message = insert_result_to_db(result,v_id)

if __name__ == "__main__":
    main()


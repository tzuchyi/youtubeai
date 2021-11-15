from __future__ import print_function
import pymysql
import matplotlib.pyplot as plt
from math import pi
import os

def db_operate():
    db = pymysql.connect(host='192.168.0.100',  # 主機名稱
                         port=3307,
                         database="BD109A_temp",
                         user="BD109A",
                         password="@vy4G9jcGAfaT6tAJ")
    return db

# def db_operate():
#     db = pymysql.connect(host='demo.jlwu.info',  # 主機名稱
#                          port=1107,
#                          database="BD109A_temp",
#                          user="BD109A",
#                          password="@vy4G9jcGAfaT6tAJ")
#     return db


def is_url(url):
    if url[:32] == 'https://www.youtube.com/watch?v=':
        v_id = url[32:43]
        return v_id
    elif url[:17] == 'https://youtu.be/':
        v_id = url[17:28]
        return v_id
    elif url[:30] == 'https://m.youtube.com/watch?v=':
        v_id = url[30:41]
        return v_id
    else:
        return False


def exist_video(http):
    v_id = is_url(http)

    db = db_operate()
    cursor = db.cursor()
    sql = "SELECT * FROM video where video_id = '%s'"%v_id
    cursor.execute(sql)
    result = cursor.fetchall()
    db.close()
    list_of_video = [i[0] for i in result]
    if len(result) >0:
        return True
    else:
        return False


def exist_comment(http):
    v_id = is_url(http)

    db = db_operate()
    cursor = db.cursor()
    sql = "SELECT * FROM total_review WHERE video_id = '%s'" % (v_id)
    cursor.execute(sql)
    result = cursor.fetchall()
    db.close()
    if len(result) == 0:
        return False
    else:
        return True


def exist_result(http):
    v_id = is_url(http)

    db = db_operate()
    cursor = db.cursor()
    sql = "SELECT * FROM result WHERE v_id = '%s'" % (v_id)
    cursor.execute(sql)
    result = cursor.fetchall()
    db.close()
    if len(result) == 0:
        return False
    else:
        return True

def ranking():
    db = db_operate()
    cursor = db.cursor()

    sql = """select * from video where click_count is not null ORDER BY click_count desc limit 20"""
    cursor.execute(sql)
    result = cursor.fetchall()
    db.close()

    rank = []
    ranking = [i+1 for i in range(20)]
    for i,j in zip(result,ranking):
        temp = {}
        temp['v_id'] = i[0]
        if len(i[1])>15:
            temp['v_name'] = i[1][:15]+'...'
        else:
            temp['v_name'] = i[1]

        if len(i[4])>15:
            temp['channel'] = i[4][:20]+'...'
        else:
            temp['channel'] = i[4]
        temp['click'] = i[11]
        temp['rank'] = j
        rank.append(temp)
    return rank


def list_of_dict_sort(list, column):
    list.sort(key=lambda k: (k.get(column, 0)), reverse=True)


def average(list, column):
    df_sum = sum(item[column] for item in list)
    avg = df_sum / len(list)
    return avg


def count_scores(s_list, column, target):
    result = len(list(filter(lambda s_list: s_list[column] == target, s_list)))
    return result


def each_count(s_list, column, cate):
    temp = {}
    for i in range(20, cate * 20 + 1, 20):
        name = 'v' + str(i)
        temp[name] = count_scores(s_list, column, i)
    return temp


def get_result(v_id, target):
    # 抓分數
    db = db_operate()
    cursor = db.cursor()
    sql = "SELECT * FROM result WHERE v_id = '%s'" % (v_id)
    cursor.execute(sql)
    result = cursor.fetchall()
    db.close()
    # 抓留言文字
    db = db_operate()
    cursor = db.cursor()
    sql = "SELECT * FROM total_review WHERE video_id = '%s'" % (v_id)
    cursor.execute(sql)
    review = cursor.fetchall()
    db.close()
    # 留言id文字字典
    id_review = {}
    for i in review:
        id_review[i[0]] = i[1]
    # 抓影片資訊
    db = db_operate()
    cursor = db.cursor()
    sql = "SELECT * FROM video WHERE video_id = '%s'" % (v_id)
    cursor.execute(sql)
    video_info = cursor.fetchall()
    db.close()

    info = {'v_id': video_info[0][0],
            'v_name': video_info[0][1],
            'channel': video_info[0][4],
            'hashtag': video_info[0][5],
            'description': video_info[0][6],
            'click': video_info[0][11]}

    if target == 6:
        yter_scores = []
        v_scores = []
        ex_scores = []
        ir_scores = []
        se_scores = []

        for i in result:
            temp = {'text': id_review[i[0]], 'yter_grade': i[1] * 20}
            yter_scores.append(temp)
            temp = {'text': id_review[i[0]], 'v_grade': i[2] * 20}
            v_scores.append(temp)
            temp = {'text': id_review[i[0]], 'ex_grade': i[3] * 20}
            ex_scores.append(temp)
            temp = {'text': id_review[i[0]], 'ir_grade': i[4] * 20}
            ir_scores.append(temp)
            temp = {'text': id_review[i[0]], 'se_grade': i[5] * 20}
            se_scores.append(temp)

        list_of_dict_sort(yter_scores, 'yter_grade')
        list_of_dict_sort(v_scores, 'v_grade')
        list_of_dict_sort(ex_scores, 'ex_grade')
        list_of_dict_sort(ir_scores, 'ir_grade')
        list_of_dict_sort(se_scores, 'se_grade')

        yter_com_num = each_count(yter_scores, 'yter_grade', 3)
        v_com_num = each_count(v_scores, 'v_grade', 3)
        ex_com_num = each_count(ex_scores, 'ex_grade', 5)
        ir_com_num = each_count(ir_scores, 'ir_grade', 2)
        se_com_num = each_count(se_scores, 'se_grade', 2)

        yter_scores_avg = average(yter_scores, 'yter_grade')
        yter_scores_avg = yter_scores_avg / 20
        yter_scores_avg = yter_scores_avg / 3 * 5
        v_scores_avg = average(v_scores, 'v_grade')
        v_scores_avg = v_scores_avg / 20
        v_scores_avg = v_scores_avg / 3 * 5
        ex_scores_avg = average(ex_scores, 'ex_grade')
        ex_scores_avg = ex_scores_avg / 20

        # 這邊為諷刺及腥羶色占比
        ir_scores_avg = ir_com_num['v40'] / (ir_com_num['v20'] + ir_com_num['v40'])
        ir_scores_avg = round(ir_scores_avg * 100, 2)
        se_scores_avg = se_com_num['v40'] / (se_com_num['v20'] + se_com_num['v40'])
        se_scores_avg = round(se_scores_avg * 100, 2)

        # print(yter_com_num)
        # print(yter_scores_avg)
        # print(count_scores(yter_scores,'yter_grade','1'))

        avg = {'yter': yter_scores_avg, 'v': v_scores_avg, 'ex': ex_scores_avg, 'ir': ir_scores_avg,
               'se': se_scores_avg}
        com_num = {'yter': yter_com_num, 'v': v_com_num, 'ex': ex_com_num, 'ir': ir_com_num, 'se': se_com_num}
        scores = {'yter_scores': yter_scores, 'v_scores': v_scores, 'ex_scores': ex_scores,
                  'ir_scores': ir_scores, 'se_scores': se_scores, 'avg': avg, 'com_num': com_num}

    else:
        scores = []
        for i in result:
            temp = {'r_id': i[0],
                    'text': id_review[i[0]],
                    'grade': i[target],
                    'grade_percentage': i[target] * 20}
            scores.append(temp)

    return scores, info


# def radar_chart(url):
#     v_id = is_url(url)
#     scores, info = get_result(v_id, 6)
#     plt.rcParams['font.sans-serif'] = ['Microsoft Sans Serif']
#     categories = ['YouTuber喜愛程度',
#             '影片喜愛程度',
#             '激動程度',
#             '諷刺程度',
#             '腥羶色程度']
#     N = len(categories)
#     angles = [n / float(N) * 2 * pi for n in range(N)]
#     angles += angles[:1]
#
#     values = [scores['avg']['yter'],scores['avg']['v'],scores['avg']['ex'],scores['avg']['ir'],scores['avg']['se']]
#     values += values[:1]
#
#     ax = plt.subplot(111, polar=True)
#
#     # Draw one axe per variable + add labels labels yet
#     plt.xticks(angles[:-1], categories, color='grey', size=15)
#
#     # Draw ylabels
#     ax.set_rlabel_position(0)
#     plt.yticks([1,2, 3,4, 5], ["1","2", "3","4", "5"], color="grey", size=15)
#     plt.ylim(1, 5)
#
#     # Plot data
#     ax.plot(angles, values, linewidth=1, linestyle='solid')
#
#     my_path = os.path.dirname(os.path.abspath(__file__))
#     plt.savefig(my_path + '/img/'+v_id+'.png')
#     plt.show()
#     img_url = '/img/'+v_id+'.png'
#     return img_url

def radar_chart(url):
    v_id = is_url(url)
    scores, info = get_result(v_id, 6)
    v_name = str(info['v_name'])
    len_of_comment = str(len(scores['yter_scores']))
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
    categories = ['degree of YouTuber like',
                  'degree of video like',
                  'degree of excited']
    len_cate = len(categories)
    angles = [n / float(len_cate) * 2 * pi for n in range(len_cate)]
    angles += angles[:1]

    values = [scores['avg']['yter'], scores['avg']['v'], scores['avg']['ex']]
    values += values[:1]

    ax = plt.subplot(111, polar=True)

    # Draw one axe per variable + add labels labels yet
    plt.xticks(angles[:-1], categories, color='grey', size=15)

    # Draw ylabels
    ax.set_rlabel_position(0)
    plt.yticks([1, 2, 3, 4, 5], ["1", "2", "3", "4", "5"], color="grey", size=15)
    plt.ylim(1, 5)

    # Plot data
    ax.plot(angles, values, linewidth=1, linestyle='solid')

    my_path = os.path.dirname(os.path.abspath(__file__))
    plt.savefig(my_path + "/result_img/" + v_id + '.png')

    img_url = "/result_img/" + v_id + '.png'
    plt.show()
    plt.close()
    ir = str(scores['avg']['ir'])
    se = str(scores['avg']['se'])

    return [img_url, ir, se, v_name, len_of_comment]

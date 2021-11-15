from __future__ import print_function
import json
import time
import re
import lxml.html
import requests
from lxml.cssselect import CSSSelector
import pymysql
import random
import select_db

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

def insert_fake(vid):
    db = db_operate()
    cursor = db.cursor()

    sql = "SELECT * FROM total_review WHERE video_id = '%s'" %(vid)

    cursor.execute(sql)
    result = cursor.fetchall()
    db.close()
    list_of_rid = [i[0] for i in result]
    print(list_of_rid)
    db = db_operate()
    cursor = db.cursor()
    for i in list_of_rid:
        score = [random.randint(1,5) for j in range(5)]
        sql = """INSERT INTO result(r_id,yter_grade,v_grade,ex_grade,ir_grade,se_grade,v_id) VALUES  ('%s','%s','%s','%s','%s','%s','%s')""" %(i, score[0], score[1],score[2],score[3],score[4],vid)
        print(sql)
        cursor.execute(sql)
        db.commit()
    db.close()


# modified from https://github.com/egbertbouman/youtube-comment-downloader
YOUTUBE_VIDEO_URL = 'https://www.youtube.com/watch?v={youtube_id}'
YOUTUBE_COMMENTS_AJAX_URL_OLD = 'https://www.youtube.com/comment_ajax'
YOUTUBE_COMMENTS_AJAX_URL_NEW = 'https://www.youtube.com/comment_service_ajax'

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'


def find_value(html, key, num_chars=2, separator='"'):
    pos_begin = html.find(key) + len(key) + num_chars
    pos_end = html.find(separator, pos_begin)
    return html[pos_begin: pos_end]


def ajax_request(session, url, params=None, data=None, headers=None, retries=5, sleep=20):
    for _ in range(retries):
        response = session.post(url, params=params, data=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        if response.status_code in [403, 413]:
            return {}
        else:
            time.sleep(sleep)


def download_comments(youtube_id, sleep=.1):
    if r'"isLiveContent":true' in requests.get(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id)).text:
        print('Live stream detected! Not all comments may be downloaded.')
        return download_comments_new_api(youtube_id, sleep)
    return download_comments_old_api(youtube_id, sleep)


def download_comments_new_api(youtube_id, sleep=1):
    # Use the new youtube API to download some comments
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT

    response = session.get(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id))
    html = response.text
    session_token = find_value(html, 'XSRF_TOKEN', 3)
    session_token = bytes(session_token, 'ascii').decode('unicode-escape')

    data = json.loads(find_value(html, 'var ytInitialData = ', 0, '};') + '}')
    for renderer in search_dict(data, 'itemSectionRenderer'):
        ncd = next(search_dict(renderer, 'nextContinuationData'), None)
        if ncd:
            break
    continuations = [(ncd['continuation'], ncd['clickTrackingParams'])]

    while continuations:
        continuation, itct = continuations.pop()
        response = ajax_request(session, YOUTUBE_COMMENTS_AJAX_URL_NEW,
                                params={'action_get_comments': 1,
                                        'pbj': 1,
                                        'ctoken': continuation,
                                        'continuation': continuation,
                                        'itct': itct},
                                data={'session_token': session_token},
                                headers={'X-YouTube-Client-Name': '1',
                                         'X-YouTube-Client-Version': '2.20201202.06.01'})

        if not response:
            break
        if list(search_dict(response, 'externalErrorMessage')):
            raise RuntimeError('Error returned from server: ' + next(search_dict(response, 'externalErrorMessage')))

        # Ordering matters. The newest continuations should go first.
        continuations = [(ncd['continuation'], ncd['clickTrackingParams'])
                         for ncd in search_dict(response, 'nextContinuationData')] + continuations

        for comment in search_dict(response, 'commentRenderer'):
            yield {'cid': comment['commentId'],
                   'text': ''.join([c['text'] for c in comment['contentText']['runs']]),
                   'time': comment['publishedTimeText']['runs'][0]['text'],
                   'author': comment.get('authorText', {}).get('simpleText', ''),
                   'channel': comment['authorEndpoint']['browseEndpoint']['browseId'],
                   'votes': comment.get('voteCount', {}).get('simpleText', '0'),
                   'photo': comment['authorThumbnail']['thumbnails'][-1]['url'],
                   'heart': next(search_dict(comment, 'isHearted'), False)}

        time.sleep(sleep)


def search_dict(partial, key):
    if isinstance(partial, dict):
        for k, v in partial.items():
            if k == key:
                yield v
            else:
                for o in search_dict(v, key):
                    yield o
    elif isinstance(partial, list):
        for i in partial:
            for o in search_dict(i, key):
                yield o


def download_comments_old_api(youtube_id, comment_limit, sleep=1):
    # Use the old youtube API to download all comments (does not work for live streams)
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT

    # Get Youtube page with initial comments
    response = session.get(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id))
    html = response.text

    reply_cids = extract_reply_cids(html)

    ret_cids = []
    for comment in extract_comments(html):
        ret_cids.append(comment['cid'])
        yield comment

    page_token = find_value(html, 'data-token')
    session_token = find_value(html, 'XSRF_TOKEN', 3)
    session_token = bytes(session_token, 'ascii').decode('unicode-escape')

    first_iteration = True

    # Get remaining comments (the same as pressing the 'Show more' button)
    while page_token:
        print(len(ret_cids), comment_limit)
        if len(ret_cids) > comment_limit and comment_limit != -1:
            break
        data = {'video_id': youtube_id,
                'session_token': session_token}

        params = {'action_load_comments': 1,
                  'order_by_time': True,
                  'filter': youtube_id}

        if first_iteration:
            params['order_menu'] = True
        else:
            data['page_token'] = page_token

        response = ajax_request(session, YOUTUBE_COMMENTS_AJAX_URL_OLD, params, data)
        if not response:
            break

        page_token, html = response.get('page_token', None), response['html_content']

        reply_cids += extract_reply_cids(html)
        for comment in extract_comments(html):
            if comment['cid'] not in ret_cids:
                ret_cids.append(comment['cid'])

                yield comment

        first_iteration = False
        time.sleep(sleep)

    # Get replies (the same as pressing the 'View all X replies' link)
    for cid in reply_cids:
        data = {'comment_id': cid,
                'video_id': youtube_id,
                'can_reply': 1,
                'session_token': session_token}

        params = {'action_load_replies': 1,
                  'order_by_time': True,
                  'filter': youtube_id,
                  'tab': 'inbox'}

        response = ajax_request(session, YOUTUBE_COMMENTS_AJAX_URL_OLD, params, data)
        if not response:
            break

        html = response['html_content']

        for comment in extract_comments(html):
            if comment['cid'] not in ret_cids:
                ret_cids.append(comment['cid'])
                yield comment
        time.sleep(sleep)


def extract_comments(html):
    try:
        tree = lxml.html.fromstring(html)
        item_sel = CSSSelector('.comment-item')
        text_sel = CSSSelector('.comment-text-content')
        time_sel = CSSSelector('.time')
        author_sel = CSSSelector('.user-name')
        vote_sel = CSSSelector('.like-count.off')
        photo_sel = CSSSelector('.user-photo')
        heart_sel = CSSSelector('.creator-heart-background-hearted')

        for item in item_sel(tree):
            yield {'cid': item.get('data-cid'),
               'text': text_sel(item)[0].text_content(),
               'time': time_sel(item)[0].text_content().strip(),
               'author': author_sel(item)[0].text_content(),
               'channel': item[0].get('href').replace('/channel/','').strip(),
               'votes': vote_sel(item)[0].text_content() if len(vote_sel(item)) > 0 else 0,
               'photo': photo_sel(item)[0].get('src'),
               'heart': bool(heart_sel(item))}
    except:
        return {}


    for item in item_sel(tree):
        yield {'cid': item.get('data-cid'),
               'text': text_sel(item)[0].text_content(),
               'time': time_sel(item)[0].text_content().strip(),
               'author': author_sel(item)[0].text_content(),
               'channel': item[0].get('href').replace('/channel/','').strip(),
               'votes': vote_sel(item)[0].text_content() if len(vote_sel(item)) > 0 else 0,
               'photo': photo_sel(item)[0].get('src'),
               'heart': bool(heart_sel(item))}


def extract_reply_cids(html):
    tree = lxml.html.fromstring(html)
    sel = CSSSelector('.comment-replies-header > .load-comments')
    return [i.get('data-cid') for i in sel(tree)]



def download_info(youtube_id, sleep=1):
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT
    youtube_url = YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id)
    response = session.get(youtube_url)
    html = response.text
    data = json.loads(find_value(html, 'var ytInitialData = ', 0, '};') + '}')
    return extract_info(data)


def extract_info(data):
    title = ''.join([item['text'] for item in list(search_dict(list(search_dict(data, 'videoPrimaryInfoRenderer'))[0], 'title'))[0]['runs']])
    view_count = list(search_dict(list(search_dict(data, 'shortViewCount'))[0], 'simpleText'))[0]
    published_time = list(search_dict(list(search_dict(data, 'publishedTimeText'))[0], 'simpleText'))[0]
    channel = list(search_dict(list(search_dict(data, 'videoSecondaryInfoRenderer'))[0], 'title'))[0]['runs'][0]['text']
    description = list(search_dict(list(search_dict(data, 'videoSecondaryInfoRenderer'))[0], 'description'))
    description = '' if len(description) == 0 else re.sub(r'\r\n+', '\n', '\n'.join([run['text'] \
                                                for run in list(
              search_dict(list(search_dict(data, 'videoSecondaryInfoRenderer'))[0], 'description'))[0]['runs']]))
    like = list(search_dict(list(search_dict(data, 'topLevelButtons'))[0][0], 'label'))[0]
    unlike = list(search_dict(list(search_dict(data, 'topLevelButtons'))[0][1], 'label'))[0]
    try:
        hashtag = [t['text'] for t in list(search_dict(data, 'superTitleLink'))[0]['runs'] if t['text'].strip() != '']
    except:
        hashtag = []

    return {'title': title,
            'view_count': view_count,
            'published_time': published_time,
            'channel': channel,
            'hashtag': hashtag,
            'description': description,
            'num_like': like,
            'num_unlike': unlike
            }



def main_info(youtube_id, sleep=0.1):
    try:
        """
        if os.sep in output:
            outdir = os.path.dirname(output)
            if not os.path.exists(outdir):
                os.makedirs(outdir)

        if r'\"isLiveContent\":true' in requests.get(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id)).text:
            print('Live stream detected! Do not download anything!')
            return
        """
        youtube_info = download_info(youtube_id)
        information = json.dumps(youtube_info, ensure_ascii=False)
        return True, [youtube_id, information]



    except Exception as e:
        print('Error:', str(e))
        #sys.exit(1)
        return False, None


def main_comment(youtube_id, output, comment_limit, sleep=0.1):

    try:
        """
        if os.sep in output:
            outdir = os.path.dirname(output)
            if not os.path.exists(outdir):
                os.makedirs(outdir)
        """
        if r'\"isLiveContent\":true' in requests.get(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id)).text:
            print('Live stream detected! Do not download anything!')
            return
        com = []
        for comment in download_comments_old_api(youtube_id, comment_limit=comment_limit, sleep=sleep):
            comment_json = json.dumps(comment, ensure_ascii=False)
            com.append(comment_json)
        return True, [youtube_id, com]


    except Exception as e:
        print('Error:', str(e))
        #sys.exit(1)
        return False, None


def insert_comment(comment):
    db = db_operate()

    cursor = db.cursor()

    sql = """INSERT INTO total_review(review_id, text,time,author,channel,votes,video_id) VALUES """
    comments = comment[1]
    for i in comments:
        try:
            vals = json.loads(i)
            val = str(
                (vals['cid'], vals['text'].replace('"','').replace("'",''), vals['time'], vals['author'].replace('"','').replace("'",''), vals['channel'].replace('"','').replace("'",''), vals['votes'], comment[0]))
            insert = sql + val
            cursor.execute(insert)
            db.commit()

        except Exception as e:
            db.rollback()

    db.close()


def insert_ytid(info):
    db = db_operate()
    cursor = db.cursor()
    yter = json.loads(info[1])['channel'].replace('"','').replace("'",'')
    sql = "SELECT * FROM YOUTUBER"
    cursor.execute(sql)
    result = cursor.fetchall()
    db.close()
    list_of_yter = [i[1] for i in result]
    db = db_operate()
    cursor = db.cursor()
    if yter not in list_of_yter:
        id_ = str(len(result) + 1)
        cate = ''
        sql = """INSERT INTO YOUTUBER(YOUTUBER_ID, CHANNEL,CATEGORY) VALUES  ('%s','%s','%s')""" % (id_, yter, cate)
        print('**insert_ytid**', sql)
        cursor.execute(sql)
        db.commit()
        db.close()
        return id_
    else:
        for i in result:
            if i[1] == yter:
                id_ = i[0]
        db.close()
        return id_


def insert_video(info):
    yter_id = insert_ytid(info)
    db = db_operate()

    cursor = db.cursor()

    # SQL 插入语句
    information = info[1]
    sql = """INSERT INTO video(video_id, video_name,view_count,published_time,channel,hashtag,description,num_like, num_unlike, ytr_id) VALUES """
    vals = json.loads(information)
    if len(vals['hashtag']) != 0:
        temp = str()
        for i in vals['hashtag']:
            temp = temp + str(i)
    else:
        temp = str()
    val = str((info[0], vals['title'].replace('"','').replace("'",''), vals['view_count'], vals['published_time'], vals['channel'].replace('"','').replace("'",''), temp.replace('"','').replace("'",''),
               vals['description'].replace('"','').replace("'",''), vals['num_like'], vals['num_unlike'], yter_id))
    insert = sql + val

    cursor.execute(insert)
    db.commit()
    db.close()


def auto_info_insert(http):
    #YOUTUBE_VIDEO_URL = 'https://www.youtube.com/watch?v={youtube_id}'
    #YOUTUBE_COMMENTS_AJAX_URL_OLD = 'https://www.youtube.com/comment_ajax'
    #USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'
    http_id = select_db.is_url(http)
    info_state, info_ = main_info(youtube_id=http_id, sleep=0.1)

    if info_state == False:
        return '失敗'
    insert_video(info_)
    return '成功'

def auto_comment_insert(http):
    http_id = select_db.is_url(http)
    comment_state, comment_ = main_comment(youtube_id=http_id, output=http_id, comment_limit=5000, sleep=0.1)
    if comment_state == False:
        return '失敗'
    insert_comment(comment_)
    return '成功'

def main(url):
    if select_db.exist_video(url) == True:
        if select_db.exist_comment(url) == False:
            message = auto_comment_insert(url)
            return message
        else:
            if select_db.exist_result(url) == True:
                return 'exist'
            else:
                return '成功'
    else:
        message = auto_info_insert(url)
        if message == '失敗':
            return message
        message = auto_comment_insert(url)
    return message

def click_plus(id):
    db = db_operate()
    cursor = db.cursor()
    sql = """select * from video WHERE video_id = '%s' """ %id
    cursor.execute(sql)
    result = cursor.fetchall()
    db.close()

    for i in result:
        if i[11]==None:
            count = 1
        else :
            count = int(i[11]) + 1

    db = db_operate()
    cursor = db.cursor()
    sql = """update video set click_count ='%s' where video_id ='%s' """ % (count, id)
    cursor.execute(sql)
    db.commit()
    db.close()




if __name__ == '__main__':
    print(download_info("Mpf2wbIXfYI", ""))


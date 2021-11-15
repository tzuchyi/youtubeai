from flask import Flask, render_template, request, session, redirect, url_for, abort, send_from_directory
import auto
import select_db
import requests
from datetime import timedelta
import os

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)

# LINE 聊天機器人的基本資料
# config = configparser.ConfigParser()
# config.read('config.ini')
line_bot_api = LineBotApi(
    "q8SBdyHTFX7T5BwiHnGo8Gxnpo8H8NprffySV/eYh5RxVdMKt1Big9Uykk859YAvZNJep/fZZcf5+yv1LCqBKLoKzYO9QvF6aC6MB3hO0QRqBf3WL66xDIK9WYIgu52fwa8atrJvBIWbsxI1WdFcoAdB04t89/1O/w1cDnyilFU=")
handler = WebhookHandler("6c90bebf21c272cee59b9f5461658eda")

# 串接url(別人的)
api_url = "http://192.168.0.101:1374"
# 自己的ngrok
ngrok_url = "https://demo.jlwu.info:1108/youtubeai"


# 接收 LINE 的資訊
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    print('*' * 10, body, '*' * 10)
    # handle webhook body（負責）
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'


# 學你說話
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text
    if select_db.is_url(user_msg) != False:
        # print('='*100,user_msg)
        message = auto.main(user_msg)

        if message == '成功':
            return_message = requests.post(api_url, json={'video_id': select_db.is_url(user_msg)})
            print('=' * 100, return_message)
            if return_message.text == '成功':
                img_url, ir, se, v_name, len_of_comment = select_db.radar_chart(user_msg)
                vid = select_db.is_url(user_msg)
                auto.click_plus(vid)

                img_urls = ngrok_url + img_url
                reply = [TextSendMessage(
                    text='【' + v_name + '】的結果出爐囉！\n總共有' + len_of_comment + '留言進行分析。\n欲查詢詳細資料請點此網址:' + ngrok_url + "/result/" + vid),
                         ImageSendMessage(original_content_url=img_urls, preview_image_url=img_urls),
                         TextSendMessage(text='諷刺留言佔比:' + ir + "% \n腥羶色留言佔比" + se + '%')]
                # line_bot_api.reply_message(event.reply_token, reply)
                userId = event.source.user_id
                line_bot_api.push_message(userId, reply)
            else:
                reply = TextSendMessage(text='Youtube忙線中，請再試一次！')
                line_bot_api.reply_message(event.reply_token, reply)
        elif message == 'exist':
            img_url, ir, se, v_name, len_of_comment = select_db.radar_chart(user_msg)
            vid = select_db.is_url(user_msg)
            img_urls = ngrok_url + img_url
            auto.click_plus(vid)

            reply = [TextSendMessage(
                text='【' + v_name + '】的結果出爐囉！\n總共有' + len_of_comment + '留言進行分析。\n欲查詢詳細資料請點此網址:' + ngrok_url + "/result/" + vid),
                     ImageSendMessage(original_content_url=img_urls, preview_image_url=img_urls),
                     TextSendMessage(text='諷刺留言佔比:' + ir + "% \n腥羶色留言佔比" + se + '%')]
            line_bot_api.reply_message(event.reply_token, reply)
        else:
            reply = TextSendMessage(text='Youtube忙線中，請再試一次！!')
            line_bot_api.reply_message(event.reply_token, reply)
    else:
        reply = TextSendMessage(text='請輸入YouTube網址！')
        line_bot_api.reply_message(event.reply_token, reply)


@app.route('/', methods=['GET', 'POST'])
def hello_world():
    session['url'] = False
    template = 'index.html'
    if request.method == 'POST':
        template = 'return.html'
        url = request.values['url']
        print(url)
        session['url'] = select_db.is_url(url)

        if select_db.is_url(url) != False:
            session.permanent = True
            # ans = website
            message = auto.main(url)
            print(message)
            if message == '成功':
                return_message = requests.post(api_url, json={'video_id': session['url']})
                if return_message.text == '成功':
                    return redirect(url_for('result', vid=select_db.is_url(url)))
            elif message == 'exist':
                # auto.click_plus(session['url'])
                return redirect(url_for('result', vid=select_db.is_url(url)))

            else:
                session['url'] = False
                template = 'index.html'
                message = '請輸入YouTube網址'
                ranking = select_db.ranking()
                return render_template(template, message=message, ranking=ranking)

        return redirect(url_for('result', vid=select_db.is_url(url)))
        # return render_template(template)
        # return render_template(template, website=url, data={'message':message, 'info':info_, 'comment':comment_},ans=ans)
    else:
        message = '???'
        ranking = select_db.ranking()
        return render_template(template, message=message, ranking=ranking)


@app.route('/contact')
def contact():
    template = 'contact.html'
    return render_template(template)


@app.route('/line')
def line():
    template = 'line.html'
    return render_template(template)


@app.route('/standard')
def standard():
    template = 'standard.html'
    return render_template(template)


@app.route("/result_img/<filename>")
def download(filename):
    dirpath = os.path.join(app.root_path, 'result_img')
    # 透過flask內建的send_from_directory
    return send_from_directory(dirpath, filename)  # as_attachment=True 一定要寫，不然會變開啟，不是下載


@app.route('/result/<vid>')
def result(vid):
    url = 'https://www.youtube.com/watch?v=' + str(vid)
    message = select_db.exist_result(url)
    if message == False:
        return render_template('index.html')
    auto.click_plus(vid)
    scores, info = select_db.get_result(vid, 6)
    return render_template('result.html', scores=scores, info=info)


@app.route('/rank')
def rank():
    ranking = select_db.ranking()
    ##ranking
    # {{ranking.v_id}} {{ranking.v_name}} {{ranking.click}} {{ranking.rank}}
    # v_id 影片名稱 點擊次數 點擊排名
    return render_template('rank.html', ranking=ranking)


@app.route('/return')
def return_():
    template = 'return.html'
    v_id = session.get('url')
    scores, info = select_db.get_result(v_id, 6)
    return render_template(template, scores=scores, info=info)


# @app.route('/insert')
# def insert_fakedata(vid="WyXWx9FLEp0"):
#     if vid is not None:
#         auto.insert_fake(vid)
#         return '成功'
#     return '失敗'


import pymysql


def test(id):
    db = pymysql.connect(host='demo.jlwu.info',  # 主機名稱
                         port=1107,
                         database="BD109A",
                         user="BD109A",
                         password="@vy4G9jcGAfaT6tAJ")

    cursor = db.cursor()

    sql = "SELECT * FROM video "
    cursor.execute(sql)
    result = cursor.fetchall()
    videos = [i[0] for i in result]
    db.close()
    if id in videos:
        db = pymysql.connect(host='demo.jlwu.info',  # 主機名稱
                             port=1107,
                             database="BD109A",
                             user="BD109A",
                             password="@vy4G9jcGAfaT6tAJ")

        cursor = db.cursor()

        sql = "SELECT * FROM video \
               WHERE video_id = '%s' " % id
        cursor.execute(sql)
        result = cursor.fetchall()
        db.close()
        for j in result:
            temp = {'v_id': j[0],
                    'v_name': j[1],
                    'channel': j[4],
                    'hashtag': j[5],
                    'description': j[6]}
    else:
        temp = {}

    return temp


if __name__ == '__main__':
    app.debug = True
    app.run()

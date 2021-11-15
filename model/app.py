from flask import Flask, request, redirect, url_for
import database
import predict
import json
import requests

app = Flask(__name__)

# api_url = 'https://bf362fd29d56.ngrok.io'

#web的ngrok
# web_url = "https://c545b14b4ebd.ngrok.io"

# v_id = 'WyXWx9FLEp0'
@app.route('/', methods=["POST"])
def main():
	if request.method =='POST':
		data = request.get_json()
		print(data)
		if 'lost_cid' in data.keys():

			v_id = data['video_id']
			lost_cid = data['lost_cid']
			data = database.get_lost_review(v_id,lost_cid)

		else:
			print(data['video_id'])
			v_id = data['video_id']
			data = database.get_review(v_id)

		data = database.out_txt(data)
		r_id = data["r_id"]
		result = predict.predict(data)
		# print(result)
		message = database.insert_result_to_db(result,r_id,v_id)
		# print(message)
		return message


		

if __name__ == '__main__':
    app.run(port = 1374,host= '0.0.0.0')

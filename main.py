import json
import os
import logging
import threading
import urllib.request
from threading import Timer

import datetime
import time
from flask_cors import *
from flask import Flask, render_template, jsonify, request


env_dist = os.environ
db = {}

# ACCESS_KEY、ACCESS_SECRET请替换成您的阿里云accesskey id和secret
NAME = env_dist.get('NAME', 'faucet')
CHAIN_ID = env_dist.get('CHAIN_ID', 'rainbow-dev')
PASSWORD = env_dist.get('PASSWORD', '1234567890')
ACCOUNT = env_dist.get('ACCOUNT', 'faa1ljemm0yznz58qxxs8xyak7fashcfxf5lssn6jm')
MAX_COUNT = env_dist.get('MAX_COUNT', 10)

REST_URL = 'http://192.168.150.7:30317'
SEQUENCE = 0
ACCOUNT_NUMBER = 0


logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter(
    '[%(asctime)s][%(thread)d][%(filename)s][line: %(lineno)d][%(levelname)s] ## %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

app = Flask(__name__)
CORS(app)


def clear_db(h=0, m=0):
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    logger.info("current hour: %d", hour)
    logger.info("current minute: %d", minute)
    if h == hour and m == minute:
        db.clear()
    t = Timer(10, clear_db)
    t.start()


@app.route('/')
@cross_origin()
def index():
    return render_template('index.html')


@app.route('/account', methods=['GET'])
@cross_origin()
def account():
    try:
        res = urllib.request.urlopen(REST_URL + "/auth/accounts/" + ACCOUNT)
        ret = res.read()
        return ret
    except Exception as e:
        logger.error(e)


@app.route('/apply', methods=['POST'])
@cross_origin()
def apply():
    ip = request.remote_addr

    data = request.get_data()
    try:
        json_dict = json.loads(data)
    except Exception as e:
        logger.error(e)
        return jsonify({"err_code": "400", "err_msg": "bad request"})
    address = json_dict.get("address", "")

    logger.info("apply address: %s", address)
    if address.strip() == "":
        return jsonify({"err_code": "401", "err_msg": "address is empty"})

    if verify(ip):
        t = threading.Thread(target=send,args=(address,))
        t.setDaemon(True)  # 设置线程为后台线程
        t.start()
        return jsonify({})
    logger.error("Exceed the upper limit")
    return jsonify({"err_code": "402", "err_msg": "verify error"})


def verify(req_ip):
    count = db.get(req_ip, 0)
    if count >= MAX_COUNT:
        return False
    db[req_ip] = count + 1
    return True


def send(address):
    global SEQUENCE
    data = {
        "amount": "10000000000000000000iris-atto",
        "sender": ACCOUNT,
        "base_tx": {
            "name": NAME,
            "password": PASSWORD,
            "chain_id": CHAIN_ID,
            "sequence": str(SEQUENCE),
            "account_number": str(ACCOUNT_NUMBER),
            "gas": "10000",
            "fee": "4000000000000000iris-atto"
        }
    }
    data = json.dumps(data)
    data = bytes(data, 'utf8')
    SEQUENCE += 1
    req = urllib.request.Request(REST_URL + "/bank/accounts/" + address + "/transfers",
                                 headers={'Content-Type': 'application/json'}, data=data)
    try:
        res = urllib.request.urlopen(req)
        ret = res.read()
        data = json.loads(ret)
        logger.info(data)
        tx = data.get('hash', '')
        return tx
    except urllib.request.HTTPError as e:
        SEQUENCE -= 1
        ret = e.file.read()
        s = ret.decode('utf-8')
        logger.error(s)
        if s.find('decoding bech32 failed:') > -1:
            return '-1'
        else:
            return '-2'


def get_sequence():
    try:
        res = urllib.request.urlopen(REST_URL + "/auth/accounts/" + ACCOUNT)
        ret = res.read()
        data = json.loads(ret)
        global SEQUENCE
        global ACCOUNT_NUMBER
        SEQUENCE = int(data.get('sequence', '0'))
        ACCOUNT_NUMBER = int(data.get('account_number', '0'))
        logger.info("update account successfully sequence=%d, account_number=%d", SEQUENCE, ACCOUNT_NUMBER)
    except Exception as e:
        logger.error(e)
        logger.info("fail to update sequence and now sequence=%d, account_number=%d", SEQUENCE, ACCOUNT_NUMBER)
    t = Timer(60 * 2, get_sequence)
    t.start()


if __name__ == '__main__':
    get_sequence()
    clear_db()
    app.run(host='0.0.0.0', port=4000)

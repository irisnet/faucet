import json
import os
import logging
import threading
import urllib.request
from threading import Timer

from flask_cors import *
from flask import Flask, render_template, jsonify, request


env_dist = os.environ

# ACCESS_KEY、ACCESS_SECRET请替换成您的阿里云accesskey id和secret
NAME = env_dist.get('NAME', 'faucet')
CHAIN_ID = env_dist.get('CHAIN_ID', 'rainbow-dev')
PASSWORD = env_dist.get('PASSWORD', '1234567890')
ACCOUNT = env_dist.get('ACCOUNT', 'faa1ljemm0yznz58qxxs8xyak7fashcfxf5lssn6jm')
FEE = env_dist.get('FEE', '5000000000000000000iris-atto')
AMOUNT = env_dist.get('AMOUNT', '10000000000000000000iris-atto')

REST_URL = 'http://localhost:1317'
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

    t = threading.Thread(target=send,args=(address,))
    t.setDaemon(True)  # 设置线程为后台线程
    t.start()
    return jsonify({})


def send(address):
    global SEQUENCE
    data = {
        "amount": AMOUNT,
        "sender": ACCOUNT,
        "base_tx": {
            "name": NAME,
            "password": PASSWORD,
            "chain_id": CHAIN_ID,
            "sequence": str(SEQUENCE),
            "account_number": str(ACCOUNT_NUMBER),
            "gas": "10000",
            "fee": FEE
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
    app.run(host='0.0.0.0', port=4000)

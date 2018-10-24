import json
import os
import logging
import threading
import urllib.request
from threading import Timer

from flask_cors import *

from aliyunsdkcore import client
from aliyunsdkafs.request.v20180112 import AuthenticateSigRequest
from aliyunsdkcore.profile import region_provider
from flask import Flask, render_template, jsonify, request

region_provider.modify_point('afs', 'cn-hangzhou', 'afs.aliyuncs.com')

env_dist = os.environ

# ACCESS_KEY、ACCESS_SECRET请替换成您的阿里云accesskey id和secret
ACCESS_KEY = env_dist.get('ACCESS_KEY', '')
ACCESS_SECRET = env_dist.get('ACCESS_SECRET', '')
APP_KEY = env_dist.get('APP_KEY', 'FFFF0N000000000063E3')
NAME = env_dist.get('NAME', 'faucet')
CHAIN_ID = env_dist.get('CHAIN_ID', 'test-chain-Bf61kJ')
PASSWORD = env_dist.get('PASSWORD', '1234567890')
ACCOUNT = env_dist.get('ACCOUNT', 'faa1x8xj4jdwa3sptwuu6daseeney3jluu39qn8rdm')

REST_URL = 'http://localhost:1317'
SEQUENCE = 0
ACCOUNT_NUMBER = 0

# clt = client.AcsClient('YOUR ACCESSKEY', 'YOUR ACCESS_SECRET', 'cn-hangzhou')
clt = client.AcsClient(ACCESS_KEY, ACCESS_SECRET, 'cn-hangzhou')
ali_request = AuthenticateSigRequest.AuthenticateSigRequest()

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
        res = urllib.request.urlopen(REST_URL + "/accounts/" + ACCOUNT)
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
    token = json_dict.get("token", "")
    session_id = json_dict.get("session_id", "")
    sig = json_dict.get("sig", "")
    address = json_dict.get("address", "")
    scene = json_dict.get("scene", "")

    logger.info("apply address: %s", address)
    if address.strip() == "":
        return jsonify({"err_code": "401", "err_msg": "address is empty"})

    if verify(token, session_id, sig, ip, scene):
        t = threading.Thread(target=send,args=(address,))
        t.setDaemon(True)  # 设置线程为后台线程
        t.start()
        return jsonify({})
    return jsonify({"err_code": "402", "err_msg": "verify error"})


def verify(token, session_id, sig, ip, scene):
    # 必填参数：从前端获取，不可更改
    ali_request.set_SessionId(session_id)
    # 必填参数：从前端获取，不可更改，android和ios只变更这个参数即可，下面参数不变保留xxx
    ali_request.set_Sig(sig)
    # 必填参数：从前端获取，不可更改
    ali_request.set_Token(token)
    # 必填参数：从前端获取，不可更改
    ali_request.set_Scene(scene)
    # 必填参数：后端填写
    ali_request.set_AppKey(APP_KEY)
    # 必填参数：后端填写
    ali_request.set_RemoteIp(ip)

    try:
        result = clt.do_action_with_exception(ali_request)  # 返回code 100表示验签通过，900表示验签失败
    except Exception as e:
        logger.error(e)
        return False
    s = bytes.decode(result)
    j = json.loads(s)
    if j.get('Code', -100) == 100:
        return True

    return False


def send(address):
    global SEQUENCE
    data = {
        "amount": "10000000000000000000iris-atto",
        "sender": NAME,
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
    req = urllib.request.Request(REST_URL + "/bank/" + address + "/send",
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
        res = urllib.request.urlopen(REST_URL + "/bank/accounts/" + ACCOUNT)
        ret = res.read()
        data = json.loads(ret)
        value = data.get('value', '0')
        global SEQUENCE
        global ACCOUNT_NUMBER
        if value == '1':
            SEQUENCE = 1
        SEQUENCE = int(value.get('sequence', '0'))
        ACCOUNT_NUMBER = int(value.get('account_number', '0'))
        logger.info("update account successfully sequence=%d, account_number=%d", SEQUENCE, ACCOUNT_NUMBER)
    except Exception as e:
        logger.error(e)
        logger.info("fail to update sequence and now sequence=%d, account_number=%d", SEQUENCE, ACCOUNT_NUMBER)
    t = Timer(60 * 10, get_sequence)
    t.start()


if __name__ == '__main__':
    get_sequence()
    app.run(host='0.0.0.0', port=4000)

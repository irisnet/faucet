import json
import os
import logging
from subprocess import PIPE, run
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
SCENE = env_dist.get('SCENE', 'ic_activity_h5')
NAME = env_dist.get('NAME', 'faucet')
CHAIN_ID = env_dist.get('CHAIN_ID', 'fuxi-develop')
AMOUNT = env_dist.get('AMOUNT', '10iris')
PASSWORD = env_dist.get('PASSWORD', '1234567890')
NODE = env_dist.get('NODE', 'tcp://192.168.150.7:46657')

# clt = client.AcsClient('YOUR ACCESSKEY', 'YOUR ACCESS_SECRET', 'cn-hangzhou')
clt = client.AcsClient(ACCESS_KEY, ACCESS_SECRET, 'cn-hangzhou')
ali_request = AuthenticateSigRequest.AuthenticateSigRequest()

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s][%(thread)d][%(filename)s][line: %(lineno)d][%(levelname)s] ## %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

app = Flask(__name__)
CORS(app)


@app.route('/')
@cross_origin()
def index():
    return render_template('index.html')


@app.route('/apply', methods=['POST'])
@cross_origin()
def apply():
    ip = request.remote_addr
    # token = request.values.get("token", "")
    # session_id = request.values.get("session_id", "")
    # sig = request.values.get("sig", "")
    # address = request.values.get("address", "")

    data = request.get_data()
    try:
        json_dict = json.loads(data)
    except Exception:
        return jsonify({"err_code": "400", "err_msg": "bad request"})
    token = json_dict.get("token", "")
    session_id = json_dict.get("session_id", "")
    sig = json_dict.get("sig", "")
    address = json_dict.get("address", "")

    logger.info("apply address: %s", address)
    if address.strip() == "":
        return jsonify({"err_code": "401", "err_msg": "address is empty"})

    if verify(token, session_id, sig, ip):
        send(address)
        return jsonify({"data": address})
    return jsonify({"err_code": "402", "err_msg": "verify error"})


def verify(token, session_id, sig, ip):
    # 必填参数：从前端获取，不可更改
    ali_request.set_SessionId(session_id)
    # 必填参数：从前端获取，不可更改，android和ios只变更这个参数即可，下面参数不变保留xxx
    ali_request.set_Sig(sig)
    # 必填参数：从前端获取，不可更改
    ali_request.set_Token(token)
    # 必填参数：从前端获取，不可更改
    ali_request.set_Scene(SCENE)
    # 必填参数：后端填写
    ali_request.set_AppKey(APP_KEY)
    # 必填参数：后端填写
    ali_request.set_RemoteIp(ip)

    try:
        result = clt.do_action_with_exception(ali_request)  # 返回code 100表示验签通过，900表示验签失败
    except Exception:
        return False
    s = bytes.decode(result)
    j = json.loads(s)
    if j.get('Code', -100) == 100:
        return True

    return False


def send(address):
    send_faucet = "iriscli send --to={0} --name={1} --chain-id={2} --amount={3} --node={4}".format(
        address, NAME, CHAIN_ID, AMOUNT, NODE)
    logger.info(send_faucet)

    p = run([send_faucet], shell=True, stdout=PIPE, input=(PASSWORD + "\n").encode())
    logger.info(p.stdout)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000)

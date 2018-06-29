# Faucet
Faucet service for Irishub Testnet


# Captcha
使用阿里云云盾·数据风控，详细信息参考https://help.aliyun.com/product/28308.html?spm=a2c4g.11186623.3.1.RaHrKG

生成appkey替换templates/index.html第20行appkey的值

# ENV Variables

环境变量如下，ACCESS_KEY、ACCESS_SECRET、APP_KEY、SCENE为Captcha配置。其余参数如下：
1. NAME，faucet账户名
2. CHAIN_ID，测试网络chain id
3. AMOUNT，转账金额
4. PASSWORD，faucet账户密码
5. NODE，测试网络节点

```
ACCESS_KEY = env_dist.get('ACCESS_KEY', '')
ACCESS_SECRET = env_dist.get('ACCESS_SECRET', '')
APP_KEY = env_dist.get('APP_KEY', '')
SCENE = env_dist.get('SCENE', 'ic_activity')
NAME = env_dist.get('NAME', 'faucet')
CHAIN_ID = env_dist.get('CHAIN_ID', 'fuxi-develop')
AMOUNT = env_dist.get('AMOUNT', '10iris')
PASSWORD = env_dist.get('PASSWORD', '1234567890')
NODE = env_dist.get('NODE', 'tcp://192.168.150.7:46657')
```

# RUN
```
python3 main.py
```

# Docker
```
docker build -t faucet ./
docker run -p 4000:4000 -e ${ENV Variables} faucet
```
进入docker container或通过docker exec -it执行如下命令新建或恢复faucet账户，
```
iriscli keys add faucet (--recover)
```
并给faucet账号转入一定数量的token。




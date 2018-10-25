FROM irisnet/irishub:v0.5.0-rc1 as builder

FROM python:3.6-alpine

ENV REPO_PATH   /faucet

COPY . $REPO_PATH
WORKDIR $REPO_PATH

COPY --from=builder /usr/local/bin/irislcd /usr/local/bin/irislcd

RUN apk add --no-cache make libc-dev bash gcc && pip3 install -r requirements.txt

EXPOSE 4000

CMD sh start.sh

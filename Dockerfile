FROM node:current-alpine

RUN mkdir -p /data

COPY . /data
WORKDIR /data

RUN cd ./validator && yarn install --frozen-lockfile
ENTRYPOINT node ./validate.js --ci

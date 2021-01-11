FROM nginx:1.19.6-alpine

RUN mkdir -p /opt/service

WORKDIR /opt/service

COPY nginx/default.conf /etc/nginx/conf.d/
COPY www www

FROM alpine:3.22
RUN apk add --no-cache nginx
COPY modules/web/nginx.conf /etc/nginx/nginx.conf
COPY modules/web/index.html /srv/index.html
ENTRYPOINT ["nginx", "-e", "/dev/stderr", "-g", "daemon off;"]

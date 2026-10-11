FROM alpine:3.22
RUN apk add --no-cache upmpdcli=1.9.6-r0 openssl
ENTRYPOINT ["upmpdcli", "-c", "/etc/upmpdcli.conf"]

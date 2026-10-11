#!/bin/sh
# Run as the rootless service user to check Podman 4.3-compatible cache options.
set -eu
podman run --rm --network=none --userns=keep-id --user "$(id -u):$(id -g)" \
  --tmpfs /cache:rw,size=128m,mode=1777 docker.io/library/alpine:3.22 \
  sh -c 'touch /cache/write-test; test -f /cache/write-test; set -- $(df -k /cache | tail -1); test "$2" = 131072'

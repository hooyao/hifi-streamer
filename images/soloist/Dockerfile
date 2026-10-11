FROM ubuntu:24.04 AS download
ARG TARGETARCH
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /download
RUN case "$TARGETARCH" in arm64) arch=arm64;; amd64) arch=x86_64;; *) exit 1;; esac; \
    curl --retry 3 --connect-timeout 15 --max-time 180 -fsSL "https://soloist-builds.spotifycdn.com/soloist_release_${arch}.tar.gz" -o soloist.tar.gz && \
    tar -xzf soloist.tar.gz && test -x soloist && sha256sum soloist > soloist.sha256
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends libasound2t64 libpulse0 libatomic1 ca-certificates && rm -rf /var/lib/apt/lists/* /usr/share/doc/* /usr/share/man/*
COPY --from=download /download/soloist /usr/local/bin/soloist
COPY --from=download /download/soloist.sha256 /usr/share/soloist.sha256
COPY images/soloist/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

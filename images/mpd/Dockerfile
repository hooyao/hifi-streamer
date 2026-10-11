FROM alpine:3.22 AS build
RUN apk add --no-cache build-base meson ninja boost-dev fmt-dev alsa-lib-dev curl-dev flac-dev libsndfile-dev mpg123-dev libogg-dev libvorbis-dev faad2-dev opus-dev icu-dev sqlite-dev curl xz
WORKDIR /build
RUN curl --retry 3 --connect-timeout 15 --max-time 180 -fsSL https://www.musicpd.org/download/mpd/0.24/mpd-0.24.5.tar.xz -o source.tar.xz && tar -xf source.tar.xz
COPY images/mpd/bounded-input.patch /build/bounded-input.patch
RUN cd mpd-0.24.5 && patch -p1 < /build/bounded-input.patch
ARG BUILD_JOBS=4
RUN meson setup out mpd-0.24.5 --buildtype=minsize --auto-features=disabled -Dalsa=enabled -Dcurl=enabled -Dflac=enabled -Dsndfile=enabled -Dmpg123=enabled -Dfaad=enabled -Dvorbis=enabled -Dopus=enabled -Ddsd=true -Ddatabase=true -Dsqlite=enabled -Dicu=enabled -Ddocumentation=disabled -Dtest=false -Dhttpd=false -Dfifo=false && ninja -C out -j${BUILD_JOBS} && strip out/mpd
FROM alpine:3.22
RUN apk add --no-cache libstdc++ fmt alsa-lib libcurl libflac libsndfile mpg123-libs faad2-libs libvorbis opus icu-libs sqlite-libs ca-certificates
COPY --from=build /build/out/mpd /usr/bin/mpd
COPY --from=build /build/mpd-0.24.5/COPYING /usr/share/licenses/mpd/COPYING
ENTRYPOINT ["mpd", "--no-daemon", "/etc/mpd.conf"]

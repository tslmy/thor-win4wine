FROM debian:trixie
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential flex bison pkg-config git ca-certificates gettext curl patch \
    libx11-dev libxext-dev libxrender-dev libxrandr-dev libxi-dev libxcursor-dev \
    libxinerama-dev libfreetype-dev libfontconfig-dev libgnutls28-dev libgl-dev \
    libasound2-dev libdbus-1-dev libudev-dev gcc-mingw-w64-i686 gcc-mingw-w64-x86-64 \
    python3 python3-xlib locales xz-utils && \
    sed -i 's/^# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
COPY containers/build-wine.sh /usr/local/bin/thor-build-wine
ENTRYPOINT ["bash", "/usr/local/bin/thor-build-wine"]

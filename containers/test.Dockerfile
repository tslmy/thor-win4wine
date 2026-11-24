FROM thor-win4wine-native:local
RUN dnf --setopt=install_weak_deps=False install -y python3-gobject dbus-daemon \
    xorg-x11-server-Xwayland xsetroot setxkbmap xterm && \
    useradd --uid 2001 --create-home player
ENTRYPOINT ["bash", "/checks/test-runtime.sh"]

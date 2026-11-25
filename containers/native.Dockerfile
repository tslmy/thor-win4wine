FROM fedora:44
RUN dnf --setopt=install_weak_deps=False install -y gcc gcc-c++ meson ninja-build patch \
    curl pkgconf-pkg-config python3 python3-xlib wayland-devel wayland-protocols-devel \
    libxkbcommon-devel libxml2-devel cairo-devel pango-devel glib2-devel libinput-devel \
    pixman-devel libpng-devel librsvg2-devel libdrm-devel mesa-libgbm-devel mesa-libEGL-devel \
    mesa-libGLES-devel libseat-devel libdisplay-info-devel libliftoff-devel lcms2-devel \
    hwdata hwdata-devel libxcb-devel xcb-util-errors-devel xcb-util-wm-devel \
    xcb-util-renderutil-devel xorg-x11-server-Xwayland-devel xorg-x11-server-Xvfb \
    grim wlrctl wlr-randr kanshi 7zip cabextract tar gzip
ENTRYPOINT ["bash"]

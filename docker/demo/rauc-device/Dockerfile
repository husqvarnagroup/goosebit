FROM alpine:edge AS build

WORKDIR /src

RUN apk add --no-cache \
    alpine-sdk \
    curl-dev \
    dbus-dev \
    git \
    glib-dev \
    json-glib-dev \
    libnl3-dev \
    meson

RUN git clone https://github.com/rauc/rauc.git && \
    cd rauc && \
    meson setup build && \
    meson compile -C build

RUN git clone https://github.com/rauc/rauc-hawkbit-updater.git && \
    cd rauc-hawkbit-updater && \
    meson setup build && \
    meson compile -C build

FROM alpine:edge AS image

RUN apk add --no-cache \
        dbus \
        e2fsprogs \
        glib \
        json-glib \
        libcurl \
        libnl3 \
        supervisor \
        util-linux \
        && \
    echo app0 > /tmp/bootslot

COPY --from=build /src/rauc/build/data/de.pengutronix.rauc.conf /usr/share/dbus-1/system.d/de.pengutronix.rauc.conf
COPY --from=build /src/rauc/build/data/de.pengutronix.rauc.service /usr/share/dbus-1/system-services/de.pengutronix.rauc.service
COPY --from=build /src/rauc/src/de.pengutronix.rauc.Installer.xml /usr/share/dbus-1/interfaces/de.pengutronix.rauc.Installer.xml
COPY --from=build /src/rauc/build/rauc /usr/local/bin/rauc
COPY --from=build /src/rauc-hawkbit-updater/build/rauc-hawkbit-updater /usr/local/bin/rauc-hawkbit-updater
RUN mkdir -p /var/log/myscript /var/log/supervisor /run/dbus /etc/rauc
COPY supervisord.conf /etc/supervisord.conf
COPY bootloader.sh /usr/local/bin/bootloader
COPY system.conf /etc/rauc/system.conf
COPY cert.pem /etc/rauc/keyring.pem
COPY rauc-hawkbit-updater.conf /etc/rauc-hawkbit-updater.conf
COPY create-loop-devices.sh /usr/local/bin/create-loop-devices
COPY restart-app.sh /usr/local/bin/restart-app
COPY app0.img /tmp/app0.img
COPY app1.img /tmp/app1.img
COPY entrypoint.sh /entrypoint.sh

CMD ["/entrypoint.sh"]

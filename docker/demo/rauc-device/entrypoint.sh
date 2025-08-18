#!/bin/sh

dbus-uuidgen --ensure

dev=$(losetup -f | cut -d' ' -f1)
mknod $dev b 7 0
mkdir -p /app
mount -o loop "/tmp/$(cat /tmp/bootslot).img" /app

exec /usr/bin/supervisord

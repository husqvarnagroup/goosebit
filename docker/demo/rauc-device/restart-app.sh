#!/bin/sh

supervisorctl stop app

umount /app
mount -o loop /tmp/$(cat /tmp/bootslot).img /app

version=$(sed -n -E 's/VERSION = "(.+)"/\1/p' /app/app.py)
sed -i -E "s/sw_version = .+/sw_version = $version/" /etc/rauc-hawkbit-updater.conf

supervisorctl start app

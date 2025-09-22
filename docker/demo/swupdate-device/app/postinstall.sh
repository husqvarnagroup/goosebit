#!/bin/sh

# SWUpdate calls shellscripts with first arg: preinst, postinst or postfailure
case "$1" in
postinst)
  chmod +x /usr/local/bin/myscript.py && supervisorctl restart myscript && echo "default 1.0.0" >/etc/sw-versions && supervisorctl restart swupdate || true
  ;;
*) ;;
esac

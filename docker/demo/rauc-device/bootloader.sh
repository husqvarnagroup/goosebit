#!/bin/sh

if [ "$1" = "get-state" ]; then
    echo good
elif [ "$1" = "get-primary" ] || [ "$1" = "get-current" ]; then
    cat /tmp/bootslot
elif [ "$1" = "set-primary" ]; then
    echo $2 > /tmp/bootslot
fi

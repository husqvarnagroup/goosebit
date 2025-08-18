#!/bin/sh

next=$(losetup -f | cut -d' ' -f1)
mknod $next b 7 0
mknod /dev/loop$(( ${next#/dev/loop} + 1 )) b 7 0

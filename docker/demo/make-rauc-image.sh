#!/bin/sh
TMP_DIR=$(dirname "$0")/tmp
BASE_DIR=$(dirname "$0")/rauc-device
APP_DIR=$BASE_DIR/app

VERSION=${1:-0.2.0}

mkdir -p $TMP_DIR

sed -E "s/VERSION = .+/VERSION = \"$VERSION\"/" $APP_DIR/app.py > $TMP_DIR/app.py
chmod +x $TMP_DIR/app.py
mkdir -p $TMP_DIR/bundle
sed -E "s/version=.+/version=$VERSION/" $APP_DIR/manifest.raucm > $TMP_DIR/bundle/manifest.raucm
tar -C $TMP_DIR -cf $TMP_DIR/bundle/app.tar app.py

rauc bundle --cert $BASE_DIR/cert.pem --key $BASE_DIR/key.pem $TMP_DIR/bundle app-$VERSION.raucb

rm -rf $TMP_DIR

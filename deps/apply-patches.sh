#!/usr/bin/env bash

BASEDIR=$(dirname "$0")

# libx11
pushd $BASEDIR/libx11 &>/dev/null
echo "Resetting and applying patches for libx11"
git reset --hard
git apply --ignore-space-change --ignore-whitespace ../patches/libx11*.patch
popd &>/dev/null

# wayland
pushd $BASEDIR/wayland &>/dev/null
echo "Resetting and applying patches for wayland"
git reset --hard
git apply --ignore-space-change --ignore-whitespace ../patches/wayland*.patch
popd &>/dev/null
#!/usr/bin/env bash

if [ $1 == "--version" ]; then
    echo "F++ Compiler/Translater version 1.0"
    exit 0
fi

env python3 /usr/bin/translate.py $1 $2
if [ "$3" == "--debug-result" ]; then
    exit 0
fi

if [ -e "./.output.asm" ]; then
    rm ./.output.asm
fi
if [ -e "./.output.o" ]; then
    rm ./.output.o
fi
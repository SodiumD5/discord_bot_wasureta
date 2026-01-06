#!/bin/bash

if [ ! -f ./Error.txt ]; then
    touch ./Error.txt
fi

python wasu.py
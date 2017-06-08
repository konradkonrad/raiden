#!/usr/bin/env bash

set -e

# temporary fix for bug in `geth makedag` in geth versions 1.6.0-1.6.5

wget -O geth-1.5.9.tar.gz https://gethstore.blob.core.windows.net/builds/geth-linux-amd64-1.5.9-a07539fb.tar.gz
tar xzvf geth-1.5.9.tar.gz
GETH=geth-linux-amd64-1.5.9-a07539fb/geth

mkdir -p $HOME/.ethash

# this will generate the DAG once, travis is configured to cache it and
# subsequent calls will not regenerate
ls -alhR $HOME/.ethash
$GETH makedag 0 $HOME/.ethash

#!/bin/sh
set -eu

docker network inspect nginx-network >/dev/null 2>&1 || docker network create nginx-network

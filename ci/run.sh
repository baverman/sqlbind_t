#!/bin/sh
set -e

thisdir="$(dirname "$0")"
ctx="$1"
shift

docker build --iidfile "$thisdir/image.hsh" "$ctx"
image=$(cat "$thisdir/image.hsh")
docker run -it --rm -v $PWD:/work:ro -w /work $image py.test -p no:cacheprovider "$@"

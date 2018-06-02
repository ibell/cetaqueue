#!/bin/bash
set -e
#ls -al /
#ls -al /mount
mkdir /mount/job
chown -Rv baleen /mount/job
ls -ld /mount/job
ln -s /mount/job /output
ls -al /mount
ls -al /
ls -al /output
# mount
exec gosu baleen "$@"

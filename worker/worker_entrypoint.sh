#!/bin/bash
set -e
mkdir /mount/job && chown -Rv baleen /mount/job && ln -s /mount/job /output
# mount
exec gosu baleen "$@"

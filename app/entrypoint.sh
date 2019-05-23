#!/bin/bash

export prometheus_multiproc_dir="$(mktemp -d)"

exec python -m kad

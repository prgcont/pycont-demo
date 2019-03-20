#!/bin/bash

export prometheus_multiproc_dir="$(mktemp -d)"

python -m kad

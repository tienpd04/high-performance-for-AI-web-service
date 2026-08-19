#!/bin/bash

mkdir -p /tmp/storage
rm -rf /tmp/storage/*
rm -rf logs/gunicorn-error.log
export PYTHONPATH=.
python src/main.py

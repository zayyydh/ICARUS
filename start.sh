#!/bin/sh
echo "Starting ICARUS on port $PORT"
exec uvicorn main:app --host 0.0.0.0 --port $PORT

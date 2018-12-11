#!/bin/bash

# Start the first process
irislcd start --trust-node=true --node $NODE &
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start iris rest: $status"
  exit $status
fi

#init faucet account
curl -X POST "http://localhost:1317/keys" -H "accept: application/json" -H "Content-Type: application/json" -d "{ \"name\": \"$NAME\", \"password\": \"$PASSWORD\", \"seed\": \"$SEED\"}"

# Start the second process
sleep 5s && python3 main.py
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start faucet: $status"
  exit $status
fi

# Naive check runs checks once a minute to see if either of the processes exited.
# This illustrates part of the heavy lifting you need to do if you want to run
# more than one service in a container. The container exits with an error
# if it detects that either of the processes has exited.
# Otherwise it loops forever, waking up every 60 seconds

while sleep 60; do
  ps aux |grep iriscli |grep -q -v grep
  iris_rest_status=$?
  ps aux |grep python3 |grep -q -v grep
  faucet_status=$?
  # If the greps above find anything, they exit with 0 status
  # If they are not both 0, then something is wrong
  if [ iris_rest_status -ne 0 -o faucet_status -ne 0 ]; then
    echo "One of the processes has already exited."
    exit 1
  fi
done
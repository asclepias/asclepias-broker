#!/bin/bash
if [ -z "$1" ]
  then
    echo "First argument must be a JSON file with the payload."
    exit 1
else
    curl -vkX POST "https://localhost:5000/api/event?noindex=1" -d @$1 --header "Content-Type: application/json" --header "Authorization: Bearer $TOKEN"
fi

#!/bin/bash

if [ -z "$API_TOKEN" ]
  then
    echo "You have to export the \"API_TOKEN\" environment variable with a valid access token for the REST API."
    exit 1
fi

if [ -z "$1" ]
  then
    echo "First argument must be a JSON file with the payload."
    exit 1
fi
curl -vkX POST "https://localhost:5000/api/events?noindex=1" \
    --header "Content-Type: application/json" \
    --header "Authorization: Bearer $API_TOKEN" \
    -d @"$1"

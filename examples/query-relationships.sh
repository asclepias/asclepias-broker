#!/bin/bash

# 10.21105/joss.00024 is the corner.py software paper
if [ -z "$1" ]; then
    query_id="10.21105/joss.00024"
    >&2 echo "No identifier was passed, '${query_id}' will be used."
else
    query_id="$1"
fi

curl -vkX GET "https://localhost:5000/api/relationships?id=${query_id}&scheme=doi&relation=isCitedBy&groupBy=version&prettyprint=1" --header "Accept: application/json"

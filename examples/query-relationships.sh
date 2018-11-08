#!/bin/bash

# 10.21105/joss.00024 is the corner.py software paper
if [ -z "$1" ]; then
    query_id="10.21105/joss.00024"
    >&2 echo "No identifier was passed, '${query_id}' will be used."
else
    query_id="$1"
fi

curl -vkG "https://localhost:5000/api/relationships" \
    --header "Accept: application/json" \
    -d id="${query_id}" \
    -d scheme=doi \
    -d relation=isCitedBy \
    -d group_by=version \
    -d prettyprint=1

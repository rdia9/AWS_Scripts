#!/bin/bash

OUTPUT="selected_regions_resources.csv"
QUERY="*"

echo "ARN,Service,Region,LastReportedAt" > $OUTPUT

# Liste fixe des régions à traiter
REGIONS="eu-west-1 eu-west-3"

for REGION in $REGIONS; do
  echo "Traitement de la région : $REGION"
  NEXT_TOKEN=""

  while :; do
    if [ -z "$NEXT_TOKEN" ]; then
      RESPONSE=$(aws resource-explorer-2 search --query-string "$QUERY" --region "$REGION" --output json)
    else
      RESPONSE=$(aws resource-explorer-2 search --query-string "$QUERY" --region "$REGION" --next-token "$NEXT_TOKEN" --output json)
    fi

    echo "$RESPONSE" | jq -r '.Resources[] | [.Arn, .Service, .Region, (.LastReportedAt // "")] | @csv' >> $OUTPUT

    NEXT_TOKEN=$(echo "$RESPONSE" | jq -r '.NextToken // empty')
    [ -z "$NEXT_TOKEN" ] && break
  done
done

echo "Export terminé dans $OUTPUT"

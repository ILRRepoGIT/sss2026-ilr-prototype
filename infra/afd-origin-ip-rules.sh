#!/usr/bin/env bash
# Standard-tier alternative to a Private Link origin (provisioning guide §5.3):
# load the CURRENT AzureFrontDoor.Backend IPv4 ranges into the web storage
# account's firewall so that only Front Door's backends can reach the static
# website endpoint. Azure Storage cannot use a service tag by name, so the
# ranges are copied in; Microsoft changes them from time to time, so re-run
# this monthly and after any Front Door service announcement. A stale list
# means Front Door is refused at the origin and the reports stop being served.
#
#   bash infra/afd-origin-ip-rules.sh <storage account> <resource group>
set -euo pipefail
ACCT="${1:?storage account}"; RG="${2:?resource group}"

# the service-tag list for the subscription's cloud; jq extracts the IPv4 prefixes
LOC=uksouth
RANGES=$(az network list-service-tags --location $LOC \
  --query "values[?name=='AzureFrontDoor.Backend'].properties.addressPrefixes[]" -o tsv | grep -v ':' )
COUNT=$(echo "$RANGES" | wc -l | tr -d ' ')
echo "AzureFrontDoor.Backend IPv4 prefixes: $COUNT"

# storage IP rules take public ranges only and do not accept /31 or /32 with a
# prefix; single addresses are added bare
EXISTING=$(az storage account network-rule list --account-name "$ACCT" --resource-group "$RG" --query "ipRules[].ipAddressOrRange" -o tsv)
for r in $RANGES; do
  v="$r"; case "$r" in */32) v="${r%/32}";; esac
  if ! grep -qx "$v" <<<"$EXISTING"; then
    az storage account network-rule add --account-name "$ACCT" --resource-group "$RG" --ip-address "$v" >/dev/null && echo "  + $v"
  fi
done
# remove rules that are no longer in the tag (keeps the firewall exactly equal to the tag)
for e in $EXISTING; do
  if ! grep -qx "$e" <<<"$(echo "$RANGES" | sed 's#/32$##')"; then
    az storage account network-rule remove --account-name "$ACCT" --resource-group "$RG" --ip-address "$e" >/dev/null && echo "  - $e"
  fi
done
az storage account update --name "$ACCT" --resource-group "$RG" --default-action Deny >/dev/null
echo "firewall on $ACCT now equals AzureFrontDoor.Backend ($COUNT prefixes); default action Deny"

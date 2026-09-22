#!/usr/bin/env bash
# One-shot provisioning of the SSS2026 ILR estate with the Bicep templates
# (provisioning guide §10). Equivalent to guide §§2–7 done by hand.
#
#   bash infra/deploy.sh [--custom-domain reports.example.wales] [--sku Premium|Standard] \
#                        [--custodian <object id>] [--admin-ip <your public ip>] [--budget 400]
#
# Prerequisites: az login; az account set --subscription <id>; an SSH key at
# ~/.ssh/id_ed25519.pub (or set SSH_PUBKEY_FILE); the DASv5 quota (guide §1).
# Re-runnable: every step is idempotent.
set -euo pipefail
LOC=uksouth; RG=SSS2026_Interactive_Learning_reports; RGB=$RG   # one existing resource group for everything (hosting note, 22 Sep 2026)
DATA=stsss2026ilrdata; WEB=stsss2026ilrweb; KV=kv-sss2026-ilr; AFD=afd-sss2026-ilr; EP=sss2026-reports
SKU=Premium; DOMAIN=""; CUSTODIAN=""; ADMIN_IP=""; BUDGET=400
SSH_PUBKEY_FILE="${SSH_PUBKEY_FILE:-$HOME/.ssh/id_ed25519.pub}"
while [ $# -gt 0 ]; do case "$1" in
  --custom-domain) DOMAIN="$2"; shift 2;; --sku) SKU="$2"; shift 2;; --custodian) CUSTODIAN="$2"; shift 2;;
  --admin-ip) ADMIN_IP="$2"; shift 2;; --budget) BUDGET="$2"; shift 2;; *) echo "unknown option $1"; exit 2;; esac; done
[ -z "$ADMIN_IP" ] && ADMIN_IP=$(curl -s https://api.ipify.org)
[ -f "$SSH_PUBKEY_FILE" ] || { echo "no SSH public key at $SSH_PUBKEY_FILE (ssh-keygen -t ed25519)"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
SKUNAME="${SKU}_AzureFrontDoor"

echo "== resource groups"
# the resource group already exists (created by Industryline); create only if it does not
az group show --name $RG >/dev/null 2>&1 || az group create --name $RG --location $LOC --tags project=SSS2026-ILR owner=Industryline >/dev/null

echo "== persistent estate (main.bicep, Front Door $SKU)"
az deployment group create -g $RG -f "$HERE/main.bicep" -n ilr-main \
  -p dataAccountName=$DATA webAccountName=$WEB keyVaultName=$KV frontDoorName=$AFD endpointName=$EP \
     frontDoorSku=$SKUNAME customDomainHost="$DOMAIN" custodianObjectId="$CUSTODIAN" --query properties.outputs -o json > /tmp/ilr-main.json
WEBURL=$(jq -r .webEndpoint.value /tmp/ilr-main.json)
EPHOST=$(jq -r .frontDoorEndpointHost.value /tmp/ilr-main.json)

echo "== static website on $WEB, health/404/robots"
ME=$(az ad signed-in-user show --query id -o tsv)
WEBID=$(az storage account show -n $WEB -g $RG --query id -o tsv)
az role assignment create --assignee-object-id $ME --assignee-principal-type User --role "Storage Blob Data Contributor" --scope $WEBID >/dev/null 2>&1 || true
az storage blob service-properties update --account-name $WEB --auth-mode login --static-website --index-document index.html --404-document 404.html >/dev/null
printf 'ok\n' > /tmp/health.txt
az storage blob upload --account-name $WEB --container-name '$web' --name health.txt --file /tmp/health.txt --auth-mode login --content-type text/plain --overwrite >/dev/null
az storage blob upload --account-name $WEB --container-name '$web' --name 404.html  --file "$HERE/404.html"  --auth-mode login --content-type text/html  --overwrite >/dev/null
az storage blob upload --account-name $WEB --container-name '$web' --name robots.txt --file "$HERE/robots.txt" --auth-mode login --content-type text/plain --overwrite >/dev/null

if [ "$SKU" = "Premium" ]; then
  echo "== approve Front Door's private endpoint on $WEB"
  for i in 1 2 3 4 5 6; do
    PEC=$(az network private-endpoint-connection list --id $WEBID --query "[?contains(properties.privateLinkServiceConnectionState.status,'Pending')].id" -o tsv || true)
    [ -n "$PEC" ] && break; sleep 20
  done
  [ -n "${PEC:-}" ] && az network private-endpoint-connection approve --id $PEC --description "Front Door $AFD" >/dev/null && echo "approved"
fi

echo "== build VM (build-vm.bicep)"
az deployment group create -g $RGB -f "$HERE/build-vm.bicep" -n ilr-vm \
  -p adminPublicKey="$(cat "$SSH_PUBKEY_FILE")" adminSourceIp=$ADMIN_IP --query properties.outputs -o json > /tmp/ilr-vm.json
PRINCIPAL=$(jq -r .principalId.value /tmp/ilr-vm.json); SUBNET=$(jq -r .subnetId.value /tmp/ilr-vm.json); VMIP=$(jq -r .publicIp.value /tmp/ilr-vm.json)

echo "== roles for the VM identity and network rules for its subnet"
az deployment group create -g $RG -f "$HERE/build-vm-roles.bicep" -n ilr-roles -p principalId=$PRINCIPAL >/dev/null
az storage account network-rule add --account-name $DATA -g $RG --subnet $SUBNET >/dev/null
az storage account network-rule add --account-name $WEB  -g $RG --subnet $SUBNET >/dev/null
az keyvault network-rule add --name $KV --subnet $SUBNET >/dev/null
az storage account update --name $WEB -g $RG --default-action Deny >/dev/null
if [ "$SKU" = "Standard" ]; then bash "$HERE/afd-origin-ip-rules.sh" $WEB $RG; fi

echo "== budget"
az consumption budget create --budget-name budget-sss2026-ilr --resource-group $RG --amount $BUDGET --time-grain Monthly \
  --start-date $(date +%Y-%m-01) --end-date 2027-09-01 --category Cost >/dev/null 2>&1 || true

echo "== link secret (created only if absent; never printed)"
MYIP=$(curl -s https://api.ipify.org)
az keyvault network-rule add --name $KV --ip-address $MYIP >/dev/null
KVID=$(az keyvault show -n $KV -g $RG --query id -o tsv)
az role assignment create --assignee-object-id $ME --assignee-principal-type User --role "Key Vault Secrets Officer" --scope $KVID >/dev/null 2>&1 || true
sleep 20
if ! az keyvault secret show --vault-name $KV --name sss2026-link-key-v1 >/dev/null 2>&1; then
  az keyvault secret set --vault-name $KV --name sss2026-link-key-v1 --value "$(openssl rand -base64 32)" \
    --content-type "HMAC-SHA256 key, link tokens, 2026 publication, version 1" >/dev/null && echo "secret created"
fi
az keyvault network-rule remove --name $KV --ip-address $MYIP >/dev/null

cat <<EOF

== hand-back sheet (guide §9)
Tenant id:                    $(az account show --query tenantId -o tsv)
Subscription:                 $(az account show --query '[name,id]' -o tsv | tr '\n' ' ')
Resource groups:              $RG / $RGB
Data storage account:         $DATA (upload the dataset per guide §3.1)
Web storage account:          $WEB (static website: $WEBURL)
Key Vault:                    $KV (secret: sss2026-link-key-v1; custodian: ${CUSTODIAN:-<to assign>})
Front Door:                   $AFD ($SKU), endpoint host $EPHOST
Custom domain:                ${DOMAIN:-<not yet>}  $( [ -n "$DOMAIN" ] && echo "validation: $(jq -c .customDomainValidation.value /tmp/ilr-main.json)")
VM:                           vm-sss2026-build at $VMIP (ssh ilrbuild@$VMIP), identity $PRINCIPAL
Log Analytics:                law-sss2026-ilr
Budget:                       budget-sss2026-ilr ($BUDGET / month)
Next: upload the dataset (guide §3.1), then on the VM: sudo ILR_GIT_URL=<repo> bash vm-bootstrap.sh <tag>
EOF

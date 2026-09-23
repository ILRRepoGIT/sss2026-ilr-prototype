#!/usr/bin/env bash
# Azure Front Door rule set for the SSS2026 ILR reports (provisioning guide §5.2).
#
#   bash infra/afd-ruleset.sh <profile> <resource-group> <route> <endpoint>
#
# Creates the rule set "sss2026reports" with four rules and attaches it to the
# route. Idempotent: re-running updates the rules in place. Azure Front Door
# allows at most FIVE actions per rule, so the six response headers are split
# across two unconditional rules (the colleague's preflight finding, 23 Sep 2026).
#
#   noindexsecurity     every response: X-Robots-Tag noindex, X-Content-Type-Options
#                       nosniff, Referrer-Policy no-referrer
#   securityheaders     every response: Strict-Transport-Security, Permissions-Policy,
#                       Content-Security-Policy
#   immutablerelease    /r/*    : cache 365 days, Cache-Control immutable
#                       (content-hashed release assets and state chunks)
#   entryrevalidate     /2026/* : Cache-Control no-cache, must-revalidate
#                       (the per-school entry pages that change on activation)
set -euo pipefail
PROFILE="${1:?profile}"; RG="${2:?resource group}"; ROUTE="${3:?route}"; ENDPOINT="${4:?endpoint}"
RS=sss2026reports

az afd rule-set create --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS >/dev/null

CSP="default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"

# --- rule 1: robots + content-type + referrer on every response (3 actions) ---
az afd rule delete --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS --rule-name noindexsecurity --yes 2>/dev/null || true
az afd rule create --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS --rule-name noindexsecurity --order 1 \
  --action-name ModifyResponseHeader --header-action Overwrite --header-name X-Robots-Tag --header-value "noindex, nofollow, noarchive" >/dev/null
for kv in "X-Content-Type-Options=nosniff" \
          "Referrer-Policy=no-referrer"; do
  name="${kv%%=*}"; value="${kv#*=}"
  az afd rule action add --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS --rule-name noindexsecurity \
    --action-name ModifyResponseHeader --header-action Overwrite --header-name "$name" --header-value "$value" >/dev/null
done

# --- rule 2: HSTS + Permissions-Policy + CSP on every response (3 actions) ----
az afd rule delete --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS --rule-name securityheaders --yes 2>/dev/null || true
az afd rule create --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS --rule-name securityheaders --order 2 \
  --action-name ModifyResponseHeader --header-action Overwrite --header-name Strict-Transport-Security --header-value "max-age=31536000; includeSubDomains" >/dev/null
for kv in "Permissions-Policy=camera=(), microphone=(), geolocation=()" \
          "Content-Security-Policy=$CSP"; do
  name="${kv%%=*}"; value="${kv#*=}"
  az afd rule action add --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS --rule-name securityheaders \
    --action-name ModifyResponseHeader --header-action Overwrite --header-name "$name" --header-value "$value" >/dev/null
done

# --- rule 3: immutable release assets ----------------------------------------
az afd rule delete --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS --rule-name immutablerelease --yes 2>/dev/null || true
az afd rule create --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS --rule-name immutablerelease --order 3 \
  --match-variable UrlPath --operator BeginsWith --match-values "/r/" \
  --action-name RouteConfigurationOverride --enable-caching true --cache-behavior OverrideAlways --cache-duration "365.00:00:00" \
  --query-string-caching-behavior IgnoreQueryString --enable-compression true >/dev/null
az afd rule action add --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS --rule-name immutablerelease \
  --action-name ModifyResponseHeader --header-action Overwrite --header-name Cache-Control --header-value "public, max-age=31536000, immutable" >/dev/null

# --- rule 4: entry pages always revalidate -----------------------------------
az afd rule delete --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS --rule-name entryrevalidate --yes 2>/dev/null || true
az afd rule create --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS --rule-name entryrevalidate --order 4 \
  --match-variable UrlPath --operator BeginsWith --match-values "/2026/" \
  --action-name RouteConfigurationOverride --enable-caching true --cache-behavior OverrideAlways --cache-duration "00:01:00" \
  --query-string-caching-behavior IgnoreQueryString --enable-compression true >/dev/null
az afd rule action add --profile-name "$PROFILE" --resource-group "$RG" --rule-set-name $RS --rule-name entryrevalidate \
  --action-name ModifyResponseHeader --header-action Overwrite --header-name Cache-Control --header-value "no-cache, must-revalidate" >/dev/null

# --- attach to the route ------------------------------------------------------
az afd route update --profile-name "$PROFILE" --resource-group "$RG" --endpoint-name "$ENDPOINT" --route-name "$ROUTE" --rule-sets $RS >/dev/null
echo "rule set $RS attached to route $ROUTE (4 rules; at most 3 actions each)"

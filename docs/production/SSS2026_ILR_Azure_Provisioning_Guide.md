# SSS2026 Interactive Learning Reports — Azure provisioning guide for the production build

Version 1.0 · 22 September 2026 · Industryline Research for Sport Wales · prepared from the V5.1 real-school round and the production deployment plan

This guide is for the colleague who will set up the cloud environment in which the School Sport Survey 2026 Interactive Learning Reports are generated, checked and published. It assumes no prior knowledge of the report pipeline. It tells you what to create, in what order, with the exact commands, and what to send back when you have finished. Everything in it can be done in one working day once the subscription exists; the quota request in step 1 is the only item that can take longer, so do it first.

What you will end up with is a small, private Azure estate: one storage account that holds the pupil dataset and the assurance evidence (never public), one storage account that serves the finished reports through a content delivery network, a key vault holding the secret that turns a school's identifier into its unguessable link, and one large virtual machine that exists only for the duration of the build and is deleted afterwards. The reports themselves are static files (HTML, JSON and shared assets); there is no application server, no database in the serving path and no login. Each school receives its own unique link, which is the access-control model Sport Wales has agreed with Welsh Government, and the reports are served under a subdomain of the School Sport Survey 2026 website.

---

## 0. Decisions already taken (do not re-open these while provisioning)

The architecture below follows the production deployment plan (15 September 2026), the in-depth technical review of that plan and the report owner's decisions of 22 September 2026. In short:

The reports are pre-generated, one complete package per school, from the finalised Stage 2 cleansed dataset (`SSS2026_pupil_stage2_full_cleaned.parquet`, Stage 2 v2 from cleansing handover v2.3, sha256 `802eda98fdeef512cce11e11aa38a45df5b0f33beb81b505acfc4ce9bbe13625`). Nothing is computed at view time.

Hosting is static: Azure Blob Storage (static website) as a private origin behind Azure Front Door (Premium with a Private Link origin is provisioned here; Standard is the lower-cost alternative, section 5.2), on a subdomain of the SSS2026 website (for example `reports.schoolsportsurvey2026.co.uk`). Access is by unique, unguessable link per school (HMAC-SHA256 of the school identifier under a secret held in Key Vault); search engines are told not to index; directory listing is impossible; an unknown link returns 404.

The build farm is one virtual machine in **UK South** with a 1 TB premium data disk: with the 64-vCPU quota Industryline has had approved, a Standard_D64s_v6 (64 vCPU, 256 GiB; the family of the approved quota) — the runner scales to the cores it finds; a D64as_v5 is the equivalent in the AMD family if that quota is granted instead, and a D32s_v6 or D16s_v6 works the same way, more slowly. It reads the dataset from the private storage account, runs several school builds at once, writes every report and its evidence, and uploads finished packages to storage. A run of all ~990 schools is expected to take well under one working day on this machine (the measured cost on a two-core sandbox is about three CPU-minutes for a 272-pupil school before its assurance reruns; section 8 gives the estimate).

Records of the run (the ledger of what was built, from what, with which results) are kept in SQLite on the VM by a single coordinator process and exported to the evidence container after the run. A managed PostgreSQL server is **not** required; the ledger code is written so that a Postgres connection string can be substituted later if Sport Wales wants a queryable register.

School reports are the first family. Local-authority and regional reports follow once Sport Wales has settled their design; the link scheme reserves `/2026/la/` and `/2026/region/` for them, so nothing here needs to change when they come.

---

## 1. Before you start

**Subscription.** Industryline's Azure subscription, in which the resource group already exists; you need Owner (or Contributor plus User Access Administrator, because role assignments are part of the setup). Record the subscription id and tenant id for the hand-back sheet (section 9). If the existing resource group has a different name from `SSS2026_Interactive_Learning_reports`, use yours consistently in every command below.

**Quota.** The 64-vCPU increase approved for Industryline's subscription in UK South is in the **`Standard Dsv6 Family vCPUs`** quota (checked 23 Sep 2026: Dsv6 = 64, DASv5 = 0, Total Regional vCPUs = 64), so the VM below is a **Standard_D64s_v6** — the Intel equivalent of the D64as_v5 this guide was first written for: the same 64 vCPU and 256 GiB, a newer processor, and the same build. Check the figure shows in Portal → Quotas → Compute (region UK South, provider Microsoft.Compute, "Dsv6") before creating the VM. If the family were ever changed, three things change with it: the `--size`, the disk controller (`--disk-controller-type NVMe` for a v6 size, `SCSI` for a v5 size — the v6 sizes support only NVMe), and nothing else; the bootstrap script finds the data disk under either controller.

**DNS.** The reports live at `reports.schoolsportsurvey2026.co.uk`, a subdomain of the School Sport Survey 2026 website (`schoolsportsurvey2026.co.uk`, owned by Industryline Research). You need access to that domain's DNS to add two records (one TXT for certificate validation, one CNAME to Front Door). Confirm who in Industryline administers the domain's DNS and that they are available on the day.

**Tools on your own computer.** Install the Azure CLI (`az`), AzCopy, Git and an SSH client. Sign in with `az login` and select the subscription with `az account set --subscription <id>`. Clone the repository at the release tag and run every `bash infra/…` command below from inside that clone (`git clone https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git && cd sss2026-ilr-prototype && git checkout v6.0-rc12` — the tag is named in `prod/release_manifest.json`; Alexander tells you if a later tag supersedes it). All commands below are Azure CLI and work in PowerShell, cmd or bash; long commands are shown with `\` line continuations, which PowerShell users should replace with a backtick or put on one line.

**Role assignments take a few minutes to propagate.** Every `az role assignment create` below is followed by a data-plane command that needs it (`--auth-mode login`, AzCopy). If such a command answers `403 AuthorizationPermissionMismatch`, wait two or three minutes and repeat it; nothing needs undoing.

**From Alexander.** You will receive (a) the dataset handover zip `SSS2026_pupil_cleansing_handover_v2.3_2026-09-09.zip` (53 MB) — the build reads three files from it: `01_cleaned_files/SSS2026_pupil_stage2_full_cleaned.parquet` (the pupil dataset), `01_cleaned_files/CLEANED_FILES_SHA256SUMS.txt` (its checksums) and `06_pipeline/plasc2026.xlsx` (the PLASC 2026 school list the recipient register takes school names and phases from) — and (b) access to the GitHub repository (`ILRRepoGIT`) at the tagged release the run will use. Do not copy the dataset anywhere other than the private storage account described in step 3; it is pupil-level data.

---

## 2. Naming, region and resource groups

Use these names unless your organisation's naming standard requires otherwise; if you change them, change them consistently and record the final names on the hand-back sheet. Storage account names must be globally unique, lower-case, 3–24 characters, letters and digits only, so add a short suffix of your own (`stsss2026ilrdata` → `stsss2026ilrdata01`, for example) if a name is taken.

| Purpose | Name | Notes |
|---|---|---|
| Region | `uksouth` | Data residency: all resources in the UK |
| Resource group | `SSS2026_Interactive_Learning_reports` | Already exists in Industryline's subscription; everything is deployed into it. The VM and its network are deleted after the run; the rest lives for the publication period |
| Storage account, private data | `stsss2026ilrdata` | Dataset, recipient register, evidence, ledger exports. Never public. |
| Storage account, web origin | `stsss2026ilrweb` | Static website (`$web`) served through Front Door; `staging` container for release candidates |
| Key Vault | `kv-sss2026-ilr` | Holds the link-token secret; nothing else |
| Front Door profile | `afd-sss2026-ilr` | Premium tier (Private Link origin); Standard is the documented alternative |
| Front Door endpoint | `sss2026-reports` | Gives `sss2026-reports-<hash>.z01.azurefd.net` until the custom domain is bound |
| VM | `vm-sss2026-build` | Standard_D64s_v6 (64 vCPU, 256 GiB; NVMe disk controller), Ubuntu 24.04 LTS — the family of the approved quota |
| Managed identity (VM) | system-assigned | Granted read on the data account, write on the web staging container and the evidence container |
| Budget | `budget-sss2026-ilr` | Alert at 50 / 80 / 100 % of the agreed monthly amount (recipients added in the portal, step 7) |

**The resource group already exists.** Industryline's subscription carries the resource group `SSS2026_Interactive_Learning_reports`, created for this run; everything below — storage, Key Vault, Front Door, Log Analytics and the build VM with its network — is deployed into it, and nothing is created in a second group. Check it and note its location (the commands below assume `uksouth`; if the group is elsewhere, use that region throughout):

```
az group show --name SSS2026_Interactive_Learning_reports --query "{name:name, location:location}" -o table
az resource list --resource-group SSS2026_Interactive_Learning_reports -o table       # empty at the 23 Sep 2026 check — everything below is created

# resource providers the estate uses; a subscription that has never used a service has its provider unregistered,
# and the first create then fails with "MissingSubscriptionRegistration". Register once (a minute or two each):
for ns in Microsoft.Storage Microsoft.KeyVault Microsoft.Cdn Microsoft.Compute Microsoft.Network Microsoft.OperationalInsights Microsoft.Consumption; do
  az provider register --namespace $ns --wait
done
az provider list --query "[?namespace=='Microsoft.Cdn' || namespace=='Microsoft.KeyVault'].{ns:namespace, state:registrationState}" -o table
```

The build VM is the only resource that is deleted after the run (guide §8); the rest lives for the publication period.

---

## 3. The private data storage account

This account holds the pupil dataset, the recipient register, and every piece of assurance evidence the run produces. It must never be reachable anonymously, must keep versions so that nothing can be silently overwritten, and must be readable by the build VM's identity only.

```
az storage account create --name stsss2026ilrdata --resource-group SSS2026_Interactive_Learning_reports --location uksouth \
  --sku Standard_ZRS --kind StorageV2 --access-tier Hot \
  --min-tls-version TLS1_2 --allow-blob-public-access false --allow-shared-key-access false \
  --https-only true --public-network-access Enabled --default-action Deny

az storage account blob-service-properties update --account-name stsss2026ilrdata --resource-group SSS2026_Interactive_Learning_reports \
  --enable-versioning true --enable-delete-retention true --delete-retention-days 30 \
  --enable-container-delete-retention true --container-delete-retention-days 30

# containers through the management plane (works with the firewall closed and before any data role exists)
for c in dataset register evidence ledger; do
  az storage container-rm create --name $c --storage-account stsss2026ilrdata --resource-group SSS2026_Interactive_Learning_reports
done

# your own account gets the data role now, so that the upload in 3.1 and the checks below can use --auth-mode login
az role assignment create --assignee <your user principal name> --role "Storage Blob Data Contributor" \
  --scope $(az storage account show -n stsss2026ilrdata -g SSS2026_Interactive_Learning_reports --query id -o tsv)
```

Being Owner or Contributor of the subscription does not include reading or writing blobs — those are data actions, which only the `Storage Blob Data …` roles grant — which is why the role is assigned explicitly here and again for the web account in step 5.1. `--default-action Deny` closes the account to all networks; you will add your own IP for the upload in step 3.1 and the VM's virtual network in step 6. `--allow-shared-key-access false` means nothing can use the account key: every access is by Entra identity, which is what makes the audit trail meaningful.

### 3.1 Upload the dataset

Allow your own public IP temporarily, upload, then remove the rule:

```
MYIP=$(curl -s https://api.ipify.org)
az storage account network-rule add --account-name stsss2026ilrdata --resource-group SSS2026_Interactive_Learning_reports --ip-address $MYIP

# unzip the handover on your machine first; upload only the three files the build reads
azcopy login
azcopy copy "01_cleaned_files/SSS2026_pupil_stage2_full_cleaned.parquet" "https://stsss2026ilrdata.blob.core.windows.net/dataset/"
azcopy copy "01_cleaned_files/CLEANED_FILES_SHA256SUMS.txt"              "https://stsss2026ilrdata.blob.core.windows.net/dataset/"
azcopy copy "06_pipeline/plasc2026.xlsx"                                  "https://stsss2026ilrdata.blob.core.windows.net/dataset/"

az storage account network-rule remove --account-name stsss2026ilrdata --resource-group SSS2026_Interactive_Learning_reports --ip-address $MYIP
```

Check the upload: `az storage blob show --account-name stsss2026ilrdata --container-name dataset --name SSS2026_pupil_stage2_full_cleaned.parquet --auth-mode login --query properties.contentLength` should print `20447561`. The build verifies the sha256 (`802eda98…`) itself before it reads a row; if the file is wrong the run refuses to start.

Delete the local unzipped copy of the dataset when the upload is verified. The zip itself should go back to Alexander's controlled folder, not stay on a laptop.

---

## 4. The key vault and the link secret

Each school's link is derived from its school identifier with HMAC-SHA256 under a secret key. The key never appears in the repository, in a report, in the ledger or in a log; the build VM reads it from Key Vault at run time to compute the tokens and forgets it. If the key were ever exposed, new tokens are computed and the same files are republished under new links — the reports do not change.

```
az keyvault create --name kv-sss2026-ilr --resource-group SSS2026_Interactive_Learning_reports --location uksouth \
  --enable-rbac-authorization true --enable-purge-protection true --retention-days 90 \
  --public-network-access Enabled --default-action Deny

MYIP=$(curl -s https://api.ipify.org)
az keyvault network-rule add --name kv-sss2026-ilr --ip-address $MYIP
az role assignment create --assignee <your user principal name> --role "Key Vault Secrets Officer" \
  --scope $(az keyvault show -n kv-sss2026-ilr -g SSS2026_Interactive_Learning_reports --query id -o tsv)

# 32 random bytes, base64 — generated once, never written down anywhere else
az keyvault secret set --vault-name kv-sss2026-ilr --name sss2026-link-key-v1 \
  --value "$(openssl rand -base64 32)" --content-type "HMAC-SHA256 key, link tokens, 2026 publication, version 1"

az keyvault network-rule remove --name kv-sss2026-ilr --ip-address $MYIP
```

Custody: the report owner (Sport Wales, or Industryline on its behalf) is the custodian of this secret. Give the "Key Vault Secrets Officer" role to the custodian's account and remove it from your own when the setup is finished. Nobody needs to read the value by hand; the build reads it by identity.

---

## 5. The web origin storage account and the CDN

### 5.1 Storage with static website hosting

```
az storage account create --name stsss2026ilrweb --resource-group SSS2026_Interactive_Learning_reports --location uksouth \
  --sku Standard_ZRS --kind StorageV2 --access-tier Hot \
  --min-tls-version TLS1_2 --allow-blob-public-access false --allow-shared-key-access false --https-only true

# your own account's data role on this account too (needed by every --auth-mode login command that follows)
az role assignment create --assignee <your user principal name> --role "Storage Blob Data Contributor" \
  --scope $(az storage account show -n stsss2026ilrweb -g SSS2026_Interactive_Learning_reports --query id -o tsv)

az storage blob service-properties update --account-name stsss2026ilrweb --auth-mode login \
  --static-website --index-document index.html --404-document 404.html

az storage account blob-service-properties update --account-name stsss2026ilrweb --resource-group SSS2026_Interactive_Learning_reports \
  --enable-versioning true --enable-delete-retention true --delete-retention-days 14

az storage container create --name staging --account-name stsss2026ilrweb --auth-mode login
```

Static website hosting creates the `$web` container and a web endpoint of the form `https://stsss2026ilrweb.z33.web.core.windows.net/` (the `z33` part varies; read it with `az storage account show -n stsss2026ilrweb -g SSS2026_Interactive_Learning_reports --query primaryEndpoints.web -o tsv`). Files in `$web` are readable by anyone who can reach that endpoint; step 5.3 restricts the endpoint so that only Front Door can. The `staging` container is private and is where a release is uploaded and verified before it is promoted into `$web`.

Note `--allow-blob-public-access false` here applies to the ordinary blob endpoint; the static-website endpoint is a separate feature and still serves `$web`. That is intended.

### 5.2 Front Door

Two tiers are possible and the choice is Industryline's; the reports are identical under either. Since the Welsh Government has confirmed that unique-URL distribution is acceptable (the school-level content is also published through the national dashboards), the Standard tier is sufficient for this publication — the hosting note of 22 Sep 2026 says the same; Premium remains the option if the origin must be isolated. Record the confirmation in the decision register either way. **Premium** (about $330 a month base) connects to the storage origin over a Private Link, so the origin is closed to the whole internet and only this Front Door profile can reach it — the configuration the technical review asked for, with nothing to maintain. **Standard** (about $35 a month base) reaches the origin over its public endpoint; the storage firewall then has to be fed the current list of Front Door backend IP ranges (the `AzureFrontDoor.Backend` service tag, which Azure Storage cannot use by name and which Microsoft changes from time to time), so it is cheaper but needs a monthly check that the ranges are still current, and a stale list means the reports stop being served. This guide provisions Premium; the Standard variant is the same commands with `--sku Standard_AzureFrontDoor`, without the `--enable-private-link` options, plus the IP-range script `infra/afd-origin-ip-rules.sh` run instead of step 5.3.

```
az afd profile create --profile-name afd-sss2026-ilr --resource-group SSS2026_Interactive_Learning_reports --sku Premium_AzureFrontDoor
az afd endpoint create --profile-name afd-sss2026-ilr --resource-group SSS2026_Interactive_Learning_reports --endpoint-name sss2026-reports --enabled-state Enabled

WEBHOST=$(az storage account show -n stsss2026ilrweb -g SSS2026_Interactive_Learning_reports --query primaryEndpoints.web -o tsv | sed -e 's#https://##' -e 's#/$##')
WEB=$(az storage account show -n stsss2026ilrweb -g SSS2026_Interactive_Learning_reports --query id -o tsv)
az afd origin-group create --profile-name afd-sss2026-ilr --resource-group SSS2026_Interactive_Learning_reports --origin-group-name og-reports \
  --probe-request-type HEAD --probe-protocol Https --probe-interval-in-seconds 120 --probe-path /health.txt \
  --sample-size 4 --successful-samples-required 3 --additional-latency-in-milliseconds 50
az afd origin create --profile-name afd-sss2026-ilr --resource-group SSS2026_Interactive_Learning_reports --origin-group-name og-reports \
  --origin-name origin-web --host-name $WEBHOST --origin-host-header $WEBHOST --priority 1 --weight 1000 \
  --enabled-state Enabled --http-port 80 --https-port 443 \
  --enable-private-link true --private-link-resource $WEB --private-link-location uksouth \
  --private-link-sub-resource-type web --private-link-request-message "SSS2026 ILR reports origin"

# approve the private endpoint connection that Front Door has just requested on the storage account
PEC=$(az network private-endpoint-connection list --id $WEB --query "[?contains(properties.privateLinkServiceConnectionState.status,'Pending')].id" -o tsv)
az network private-endpoint-connection approve --id $PEC --description "Front Door afd-sss2026-ilr"

az afd route create --profile-name afd-sss2026-ilr --resource-group SSS2026_Interactive_Learning_reports --endpoint-name sss2026-reports \
  --route-name route-reports --origin-group og-reports --supported-protocols Http Https --https-redirect Enabled \
  --forwarding-protocol HttpsOnly --patterns-to-match "/*" --link-to-default-domain Enabled \
  --enable-caching true --enable-compression true --query-string-caching-behavior IgnoreQueryString \
  --content-types-to-compress "application/json" "text/html" "text/css" "application/javascript" "text/javascript" "image/svg+xml" "text/plain"
```

The response headers, cache rules and 404 behaviour are applied by a rule set. Create it once and attach it to the route (the repository's `infra/afd-ruleset.sh` does exactly this; the rules are listed here so the intent is clear):

Rules `noindexsecurity` and `securityheaders` (all requests; Front Door allows at most five actions per rule, so the six headers are split across two unconditional rules): add response headers `X-Robots-Tag: noindex, nofollow, noarchive`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` (the first rule) and `Strict-Transport-Security: max-age=31536000; includeSubDomains`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`, `Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'` (the second). Together they keep the reports out of search engines, forbid embedding, and confine every script and fetch to the reports host.

Rule `immutablerelease` (path begins with `/r/`): override cache to 365 days and add `Cache-Control: public, max-age=31536000, immutable`. Everything under `/r/<release>/` has a content hash in its name and never changes.

Rule `entryrevalidate` (path begins with `/2026/`): add `Cache-Control: no-cache, must-revalidate`. A school's entry page is the one file that changes when a new release is activated, so it must always be revalidated.

```
bash infra/afd-ruleset.sh afd-sss2026-ilr SSS2026_Interactive_Learning_reports route-reports sss2026-reports
```

### 5.3 Seed the origin, then lock it to Front Door

First, while the account is still open to your own IP, upload the three small files the origin needs so that Front Door's health probe goes green and a wrong link answers properly from the first minute:

```
printf 'ok\n' > health.txt
az storage blob upload --account-name stsss2026ilrweb --container-name '$web' --name health.txt --file health.txt --auth-mode login --content-type text/plain
az storage blob upload --account-name stsss2026ilrweb --container-name '$web' --name 404.html --file infra/404.html --auth-mode login --content-type text/html
az storage blob upload --account-name stsss2026ilrweb --container-name '$web' --name robots.txt --file infra/robots.txt --auth-mode login --content-type text/plain
```

(`infra/404.html` is a bilingual "report not found" page with no information about what exists; `infra/robots.txt` disallows everything. The publication step re-copies all three from the release, so they never go stale.)

Then, with the Private Link connection approved, close the origin's public endpoint to everything except the build VM's subnet (added in step 6):

```
az storage account update --name stsss2026ilrweb --resource-group SSS2026_Interactive_Learning_reports --default-action Deny
```

After this, a request straight to the `web.core.windows.net` endpoint from the public internet is refused (403); Front Door reaches the origin privately, and the VM reaches it through its virtual-network rule for uploads. Nothing else can. (Under the Standard-tier variant this step is replaced by `bash infra/afd-origin-ip-rules.sh stsss2026ilrweb SSS2026_Interactive_Learning_reports`, which loads the current Front Door backend ranges into the firewall and should be re-run monthly; another organisation's Front Door could then still reach the origin, though only with a school's unguessable link and without any ability to list what exists — a residual to be risk-accepted in writing if that tier is chosen.)


### 5.4 Custom domain

The subdomain is `reports.schoolsportsurvey2026.co.uk`:

```
az afd custom-domain create --profile-name afd-sss2026-ilr --resource-group SSS2026_Interactive_Learning_reports \
  --custom-domain-name reports-domain --host-name reports.schoolsportsurvey2026.co.uk \
  --certificate-type ManagedCertificate --minimum-tls-version TLS12
az afd custom-domain show --profile-name afd-sss2026-ilr --resource-group SSS2026_Interactive_Learning_reports --custom-domain-name reports-domain \
  --query validationProperties
```

Add two records to the schoolsportsurvey2026.co.uk zone: the TXT record `_dnsauth.reports.schoolsportsurvey2026.co.uk` with the validation token the command prints, and a CNAME from `reports.schoolsportsurvey2026.co.uk` to the endpoint host name (`az afd endpoint show … --query hostName`). When the domain shows `Approved`, associate it with the route:

```
az afd route update --profile-name afd-sss2026-ilr --resource-group SSS2026_Interactive_Learning_reports --endpoint-name sss2026-reports \
  --route-name route-reports --custom-domains reports-domain --link-to-default-domain Disabled
```

Disabling the default `azurefd.net` domain on the route means the reports answer only on the custom domain, so there is exactly one hostname to protect, monitor and, if ever necessary, withdraw.

---

## 6. The build virtual machine

The VM is created in its own resource group so that it — and its disk — can be deleted in one action when the run is over. It has no public IP: you reach it through Azure Bastion (simplest) or through an SSH rule limited to your own address; the commands below use the SSH rule because it costs nothing, and note the Bastion alternative.

```
az network vnet create --resource-group SSS2026_Interactive_Learning_reports --name vnet-sss2026-build --address-prefix 10.40.0.0/24 \
  --subnet-name snet-build --subnet-prefix 10.40.0.0/26 --location uksouth
az network vnet subnet update --resource-group SSS2026_Interactive_Learning_reports --vnet-name vnet-sss2026-build --name snet-build \
  --service-endpoints Microsoft.Storage Microsoft.KeyVault

MYIP=$(curl -s https://api.ipify.org)
az network nsg create --resource-group SSS2026_Interactive_Learning_reports --name nsg-sss2026-build --location uksouth
az network nsg rule create --resource-group SSS2026_Interactive_Learning_reports --nsg-name nsg-sss2026-build --name allow-ssh-admin \
  --priority 100 --direction Inbound --access Allow --protocol Tcp --source-address-prefixes $MYIP --destination-port-ranges 22

az vm create --resource-group SSS2026_Interactive_Learning_reports --name vm-sss2026-build --location uksouth \
  --image Canonical:ubuntu-24_04-lts:server:latest --size Standard_D64s_v6 --disk-controller-type NVMe \
  --admin-username ilrbuild --generate-ssh-keys --authentication-type ssh \
  --vnet-name vnet-sss2026-build --subnet snet-build --nsg nsg-sss2026-build --public-ip-sku Standard \
  --os-disk-size-gb 128 --storage-sku Premium_LRS \
  --data-disk-sizes-gb 1024 --data-disk-caching ReadWrite \
  --os-disk-delete-option Delete --data-disk-delete-option Delete --nic-delete-option Delete \
  --assign-identity [system] --tags project=SSS2026-ILR lifetime=temporary
```

Give the VM's identity the roles it needs and allow its subnet through the storage and key-vault firewalls:

```
VMID=$(az vm show -g SSS2026_Interactive_Learning_reports -n vm-sss2026-build --query identity.principalId -o tsv)
DATA=$(az storage account show -n stsss2026ilrdata -g SSS2026_Interactive_Learning_reports --query id -o tsv)
WEB=$(az storage account show -n stsss2026ilrweb -g SSS2026_Interactive_Learning_reports --query id -o tsv)
KV=$(az keyvault show -n kv-sss2026-ilr -g SSS2026_Interactive_Learning_reports --query id -o tsv)
az role assignment create --assignee-object-id $VMID --assignee-principal-type ServicePrincipal --role "Storage Blob Data Reader"      --scope "$DATA/blobServices/default/containers/dataset"
az role assignment create --assignee-object-id $VMID --assignee-principal-type ServicePrincipal --role "Storage Blob Data Contributor" --scope "$DATA/blobServices/default/containers/register"
az role assignment create --assignee-object-id $VMID --assignee-principal-type ServicePrincipal --role "Storage Blob Data Contributor" --scope "$DATA/blobServices/default/containers/evidence"
az role assignment create --assignee-object-id $VMID --assignee-principal-type ServicePrincipal --role "Storage Blob Data Contributor" --scope "$DATA/blobServices/default/containers/ledger"
az role assignment create --assignee-object-id $VMID --assignee-principal-type ServicePrincipal --role "Storage Blob Data Contributor" --scope "$WEB/blobServices/default/containers/staging"
az role assignment create --assignee-object-id $VMID --assignee-principal-type ServicePrincipal --role "Storage Blob Data Contributor" --scope "$WEB/blobServices/default/containers/\$web"
az role assignment create --assignee-object-id $VMID --assignee-principal-type ServicePrincipal --role "Key Vault Secrets User" --scope $KV
AFD=$(az afd profile show -g SSS2026_Interactive_Learning_reports --profile-name afd-sss2026-ilr --query id -o tsv)
az role assignment create --assignee-object-id $VMID --assignee-principal-type ServicePrincipal --role "CDN Profile Contributor" --scope $AFD   # Front Door purge on activation

SUBNET=$(az network vnet subnet show -g SSS2026_Interactive_Learning_reports --vnet-name vnet-sss2026-build -n snet-build --query id -o tsv)
az storage account network-rule add --account-name stsss2026ilrdata --resource-group SSS2026_Interactive_Learning_reports --subnet $SUBNET
az storage account network-rule add --account-name stsss2026ilrweb  --resource-group SSS2026_Interactive_Learning_reports --subnet $SUBNET
az keyvault network-rule add --name kv-sss2026-ilr --subnet $SUBNET
```

The separation of duties the review asks for is expressed here as scopes: the VM can read the dataset but not change it, can write evidence and staging but cannot touch `dataset`, and can write `$web` and purge Front Door only because it is also the publisher in this first release. Before the first publication, the runbook (Phase F1) moves the `$web` and purge roles from the VM to a named publisher — a person who runs `az login` as themselves on the VM (the storage firewall admits only the VM's subnet, so the publication commands run there, with `--auth azcli` so that AzCopy uses that person's sign-in rather than the machine's identity); a build then cannot publish itself. The publisher needs three assignments, listed in F1: Storage Blob Data Contributor on `$web`, Storage Blob Data Reader on `staging` (the activation is a server-side copy from `staging`) and CDN Profile Contributor on the Front Door profile (the purge).

### 6.1 Prepare the VM

SSH in (`ssh ilrbuild@<public ip>`), then run the bootstrap script from the repository, which installs Python 3.11 (the interpreter every prototype lock was produced with; Ubuntu 24.04's own is 3.12, so it comes from the deadsnakes archive), Node 22, Git, AzCopy, the Azure CLI, Playwright's Chromium for the browser gate, mounts and formats the 1 TB data disk at `/data`, and clones the tagged release. The repository is private, so the VM needs a read-only credential to clone it: a GitHub fine-grained token with *Contents: read* on this one repository (created by whoever administers `ILRRepoGIT`; it is used once and can be revoked after the bootstrap). The token is **never put in the clone URL** — git saves the URL in the clone's `.git/config`, credentials included — and never on the command line, which goes into the shell history. The script prompts for it, keeps it in memory for the clone and the fetch only (a per-process credential helper, with any configured helpers disabled), unsets it, and refuses a URL that carries credentials; the clone keeps the clean URL `https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git`.

```
# copy the script to the VM from your own clone (scp), or paste it — the repository is private, so raw.githubusercontent.com will not serve it
scp infra/vm-bootstrap.sh ilrbuild@<public ip>:
sudo bash vm-bootstrap.sh v6.0-rc12
#   → "GitHub read-only token for the clone (not echoed, not stored):"  paste the token, press Enter
```

The same rule applies to your own clone on your laptop: clone the clean URL and give the token transiently (the Git Credential Manager prompt, or `git -c credential.helper= -c 'credential.helper=!f() { echo username=x-access-token; echo "password=$TOKEN"; }; f' clone …` with `TOKEN` exported for that shell only); never `git clone https://<token>@…`.

`v6.0-rc12` is the release tag this guide was written for (the value in `prod/release_manifest.json`); if Alexander names a later tag, use that. The script accepts the storage, vault and Front Door names as environment variables (`ILR_DATA_ACCOUNT`, `ILR_WEB_ACCOUNT`, `ILR_KEY_VAULT`, `ILR_AFD_PROFILE`, `ILR_AFD_ENDPOINT`, `ILR_RG`) if you changed any of them from section 2, and writes them all to `/etc/profile.d/ilr.sh` so the runbook's commands can use them.

The script ends by printing the sha256 of every file that takes part in a build and comparing them with the release manifest; it stops if any differ. It also runs `az login --identity` and checks that the identity can list the `dataset` container and read the link secret's metadata (not its value). If both checks pass, the machine is ready for the runbook (`docs/production/SSS2026_ILR_Operations_Runbook.md`).

---

## 7. Logging, budget and alerts

```
az monitor log-analytics workspace create --resource-group SSS2026_Interactive_Learning_reports --workspace-name law-sss2026-ilr --location uksouth --retention-time 90
LAW=$(az monitor log-analytics workspace show -g SSS2026_Interactive_Learning_reports -n law-sss2026-ilr --query id -o tsv)
AFD=$(az afd profile show -g SSS2026_Interactive_Learning_reports --profile-name afd-sss2026-ilr --query id -o tsv)
az monitor diagnostic-settings create --name afd-logs --resource $AFD --workspace $LAW \
  --logs '[{"category":"FrontDoorAccessLog","enabled":true},{"category":"FrontDoorHealthProbeLog","enabled":true}]' \
  --metrics '[{"category":"AllMetrics","enabled":true}]'
az consumption budget create --budget-name budget-sss2026-ilr --resource-group SSS2026_Interactive_Learning_reports --amount 400 --time-grain Monthly \
  --start-date $(date +%Y-%m-01) --end-date 2027-09-01 --category Cost
```

The CLI creates the budget without alert recipients; add the 50 / 80 / 100 % e-mail alerts in the portal (Cost Management → Budgets → `budget-sss2026-ilr` → Edit → Alert conditions) and record the recipient on the hand-back sheet.

Front Door access logs contain the request path, which for a school report is its unguessable link. Treat the Log Analytics workspace as confidential: restrict Reader access to the operations team, keep the 90-day retention, and never paste a logged URL into email or a ticket. Alerts on the budget should go to the service owner named on the hand-back sheet.

---

## 8. What it costs and how long it takes

Indicative list prices, pay-as-you-go, September 2026, before any organisational discount; confirm in the [Azure pricing calculator](https://azure.microsoft.com/en-us/pricing/calculator/) in GBP for your subscription. The build VM is the only significant cost and it exists only for the run.

| Item | Basis | Indicative cost |
|---|---|---|
| VM Standard_D64s_v6 (64 vCPU, 256 GiB) | of the order of $3 per hour pay-as-you-go (the D64as_v5 it replaces is about $2.75/hour — four times the D16as_v5's $0.69/hour on [Vantage](https://instances.vantage.sh/azure/vm/d16as-v5); confirm the v6 figure in the calculator); 3 days of provisioning, pilot, full run and verification = 72 hours | about $200–$250 |
| 1 TB Premium SSD data disk (P30) + 128 GB OS disk | per month while the VM exists | about $150 per month, pro-rated |
| Front Door Premium (Private Link origin) | about $330 base per month + egress (around $0.08/GB in Europe) + requests ([Microsoft](https://learn.microsoft.com/en-us/azure/frontdoor/understanding-pricing)); 1,000 schools each opening their report a handful of times a month is under 100 GB | $340–$360 per month |
| Front Door Standard (alternative, IP-range firewall) | $35 base per month + egress + $0.009 per 10,000 requests | $40–$60 per month |
| Two storage accounts (ZRS, hot) | ~200 GB of reports and evidence, versioned | $10–$20 per month |
| Key Vault, Log Analytics, Bastion (if used) | small | under $30 per month (Bastion Basic about $140 per month if you choose it over the SSH rule) |

Run time. On a two-core sandbox one 272-pupil primary school builds in 3½ minutes including its full assurance pass (peak memory 1.5 GiB); the two larger schools in the same round took 6½–7 minutes (peak 2.2 GiB). Allowing about five CPU-minutes per school all in, the 935 eligible schools are roughly 80 CPU-hours: on 64 vCPUs running about 50 builds at once that is roughly 1½–2 hours; on 16 vCPUs about 6–7 hours. The pilot in the runbook measures the real figures on the VM before the full run, and the runner adapts its concurrency to the memory it sees (about 3 GiB per job is enough).

Teardown — **the VM and its network only, never the resource group.** Everything lives in the one resource group `SSS2026_Interactive_Learning_reports`: the storage accounts holding the reports and the evidence, the Key Vault and the Front Door serve the publication for its whole life and must stay. When the publication is verified and the evidence is in the `evidence` container, remove the build resources one by one (the VM was created with its disks and NIC set to delete with it):

```
RG=SSS2026_Interactive_Learning_reports
az vm delete -g $RG -n vm-sss2026-build --yes                      # the VM; its OS disk, data disk and NIC are deleted with it (deleteOption Delete)
az disk list -g $RG --query "[?contains(name,'vm-sss2026-build')].name" -o tsv | xargs -r -n1 az disk delete -g $RG --yes -n   # any disk left behind
az network nic list -g $RG --query "[?contains(name,'vm-sss2026-build')].name" -o tsv | xargs -r -n1 az network nic delete -g $RG -n   # any NIC left behind
az network public-ip delete -g $RG -n vm-sss2026-buildPublicIP 2>/dev/null || az network public-ip list -g $RG -o table   # the public IP (name as `az network public-ip list` shows it)
az storage account network-rule remove --account-name stsss2026ilrdata -g $RG --subnet $(az network vnet subnet show -g $RG --vnet-name vnet-sss2026-build -n snet-build --query id -o tsv)
az storage account network-rule remove --account-name stsss2026ilrweb  -g $RG --subnet $(az network vnet subnet show -g $RG --vnet-name vnet-sss2026-build -n snet-build --query id -o tsv)
az keyvault network-rule remove --name kv-sss2026-ilr --subnet $(az network vnet subnet show -g $RG --vnet-name vnet-sss2026-build -n snet-build --query id -o tsv)
az network vnet delete -g $RG -n vnet-sss2026-build
az network nsg delete -g $RG -n nsg-sss2026-build
az resource list -g $RG -o table                                    # what remains must be: the two storage accounts, the Key Vault, the Front Door profile, Log Analytics
```

Never run `az group delete` on this group while the publication is live: it would delete the reports, the evidence and the serving infrastructure together. The VM's role assignments on the storage accounts and the vault disappear with its identity.

---

## 9. Hand-back sheet

Send Alexander the following (a plain text file is fine). None of these values is secret; the link secret stays in Key Vault and is not to be sent.

```
Tenant id:                    
Subscription id / name:       
Resource groups:              SSS2026_Interactive_Learning_reports / SSS2026_Interactive_Learning_reports
Data storage account:         stsss2026ilrdata   (dataset container: parquet uploaded, contentLength 20447561)
Web storage account:          stsss2026ilrweb    (static website endpoint: https://…web.core.windows.net/)
Key Vault:                    kv-sss2026-ilr     (secret name: sss2026-link-key-v1; custodian: <name>)
Front Door endpoint host:     sss2026-reports-<hash>.z01.azurefd.net
Custom domain:                reports.schoolsportsurvey2026.co.uk  (status: Pending / Approved)
VM:                           vm-sss2026-build   (public IP or Bastion; admin user ilrbuild)
VM managed identity id:       <principalId>
Log Analytics workspace:      law-sss2026-ilr
Budget:                       budget-sss2026-ilr, £/$ <amount>, alerts to <email>
Quota:                        Dsv6 vCPUs in UK South = <number>   (DASv5 = <number>, if requested)
DNS administrator:            <name / contact>
Publisher identity (later):   <name / object id>
```

---

## 10. If you use the infrastructure-as-code instead

Everything in sections 2–7 is also expressed as Bicep in `infra/main.bicep` with `infra/deploy.sh`, so that the estate can be recreated identically (for a second environment, a rehearsal, or after an incident). The two are equivalent; the CLI steps are given in full so that the guide can be followed without reading Bicep, and so that any step can be repeated on its own. Whichever route you take, the checks are the same: the dataset blob is `20447561` bytes, the origin refuses direct requests, the health probe is green, the custom domain is approved, and the VM bootstrap ends with "release manifest verified".

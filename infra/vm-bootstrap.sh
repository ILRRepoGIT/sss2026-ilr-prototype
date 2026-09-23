#!/usr/bin/env bash
# Build-VM bootstrap for the SSS2026 ILR production run (provisioning guide §6.1).
#
#   sudo bash vm-bootstrap.sh <tag>          # prompts for the read-only GitHub token (not echoed)
#
# The repository is private. The token is held in memory only: it is read from a
# prompt (or from ILR_GIT_TOKEN if you must set it), handed to git through a
# per-process credential helper, and unset when the clone and fetch are done. The
# clone keeps the CLEAN URL as remote.origin.url; a URL with credentials in it is
# refused, because git would save it in .git/config (preflight finding, 23 Sep 2026).
#
# Optional environment:
#   ILR_GIT_URL      clean clone URL (default https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git)
#   ILR_GIT_TOKEN    the read-only token, if not given at the prompt (do not put it on the
#                    command line — that goes into the shell history; prefer the prompt)
#   ILR_DATA_ACCOUNT storage account holding the dataset (default stsss2026ilrdata)
#   ILR_WEB_ACCOUNT  web-origin storage account (default stsss2026ilrweb)
#   ILR_KEY_VAULT    key vault holding the link secret (default kv-sss2026-ilr)
#   ILR_LINK_SECRET  secret name (default sss2026-link-key-v1)
#   ILR_AFD_PROFILE / ILR_AFD_ENDPOINT / ILR_RG   Front Door profile, endpoint and
#                    resource group (defaults afd-sss2026-ilr / sss2026-reports / SSS2026_Interactive_Learning_reports)
#
# What it does, in order: system packages; Python 3.11 (the interpreter every
# V5.x lock and the V6.0 pilot were produced with — from the deadsnakes PPA on
# Ubuntu 24.04) with the pinned requirements; Node 22 and jsdom; Playwright's Chromium;
# AzCopy and the Azure CLI; the 1 TB data disk formatted and mounted at /data;
# the repository cloned at the tag into /data/ilr/repo; the release manifest
# verified (every participating file's sha256); the managed identity's access
# to the dataset container and the link secret checked. Stops at the first
# failure. Re-runnable.
set -euo pipefail
TAG="${1:?release tag, e.g. v6.0}"
ILR_GIT_URL="${ILR_GIT_URL:-https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git}"
ILR_GIT_TOKEN="${ILR_GIT_TOKEN:-}"
ILR_DATA_ACCOUNT="${ILR_DATA_ACCOUNT:-stsss2026ilrdata}"
ILR_WEB_ACCOUNT="${ILR_WEB_ACCOUNT:-stsss2026ilrweb}"
ILR_AFD_PROFILE="${ILR_AFD_PROFILE:-afd-sss2026-ilr}"
ILR_AFD_ENDPOINT="${ILR_AFD_ENDPOINT:-sss2026-reports}"
ILR_RG="${ILR_RG:-SSS2026_Interactive_Learning_reports}"
export PLAYWRIGHT_BROWSERS_PATH=/data/ilr/pw-browsers
ILR_KEY_VAULT="${ILR_KEY_VAULT:-kv-sss2026-ilr}"
ILR_LINK_SECRET="${ILR_LINK_SECRET:-sss2026-link-key-v1}"
export DEBIAN_FRONTEND=noninteractive

echo "== 1/8 system packages"
apt-get update -qq
apt-get install -y -qq git curl ca-certificates gnupg lsb-release jq unzip time software-properties-common \
  python3 python3-venv python3-pip build-essential \
  fonts-liberation libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
  libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2t64 libpango-1.0-0 libcairo2 >/dev/null

echo "== 2/8 data disk at /data"
if ! mountpoint -q /data; then
  # The data disk is LUN 0. Under the NVMe disk controller (the v6 sizes, e.g. D64s_v6) Ubuntu 24.04's
  # azure-vm-utils names it /dev/disk/azure/data/by-lun/0; under SCSI (the v5 sizes) the agent names it
  # /dev/disk/azure/scsi1/lun0. If neither link exists, the one unformatted, unpartitioned block device
  # of the data disk's size that is not the OS disk is taken; anything else stops here.
  DEV=$(readlink -f /dev/disk/azure/data/by-lun/0 2>/dev/null || readlink -f /dev/disk/azure/scsi1/lun0 2>/dev/null || true)
  if [ -z "$DEV" ]; then
    OSDEV=$(lsblk -no PKNAME "$(findmnt -no SOURCE /)" 2>/dev/null | head -1)
    CANDS=$(lsblk -dnbo NAME,SIZE,TYPE | awk -v os="$OSDEV" '$3=="disk" && $1!=os && $2>=500000000000 {print "/dev/"$1}')
    FREE=""
    for c in $CANDS; do
      if [ -z "$(lsblk -no FSTYPE "$c" | tr -d '[:space:]')" ] && [ "$(lsblk -no NAME "$c" | wc -l)" -eq 1 ]; then FREE="$FREE $c"; fi
    done
    set -- $FREE
    if [ "$#" -eq 1 ]; then DEV="$1"; else
      echo "cannot identify the data disk (candidates:${FREE:- none}) — attach the 1 TB disk at LUN 0 and re-run"; lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT; exit 1
    fi
  fi
  echo "data disk: $DEV"
  if ! blkid "$DEV" >/dev/null 2>&1; then mkfs.ext4 -q -L ilrdata "$DEV"; fi
  mkdir -p /data
  UUID=$(blkid -s UUID -o value "$DEV")
  grep -q "$UUID" /etc/fstab || echo "UUID=$UUID /data ext4 defaults,nofail,noatime 0 2" >> /etc/fstab
  mount /data
fi
mkdir -p /data/ilr /data/ilr/work /data/ilr/private /data/ilr/out /data/ilr/evidence
chmod 700 /data/ilr/private
df -h /data | tail -1

echo "== 3/8 Node 22 + jsdom"
if ! command -v node >/dev/null || [ "$(node -v | cut -c2-3)" -lt 22 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null
  apt-get install -y -qq nodejs >/dev/null
fi
mkdir -p /data/ilr/node && cd /data/ilr/node && npm install --silent jsdom@24 >/dev/null
node -v; node -e "require('/data/ilr/node/node_modules/jsdom'); console.log('jsdom ok')"

echo "== 4/8 Azure CLI + AzCopy"
if ! command -v az >/dev/null; then curl -sL https://aka.ms/InstallAzureCLIDeb | bash >/dev/null; fi
if ! command -v azcopy >/dev/null; then
  curl -sL https://aka.ms/downloadazcopy-v10-linux -o /tmp/azcopy.tgz
  tar -xzf /tmp/azcopy.tgz -C /tmp && install -m 755 /tmp/azcopy_linux_amd64_*/azcopy /usr/local/bin/azcopy
fi
az version --query '"azure-cli"' -o tsv; azcopy --version | head -1

echo "== 5/8 repository at $TAG"
cd /data/ilr
if [ ! -d repo/.git ]; then
  case "$ILR_GIT_URL" in *@*) echo "ILR_GIT_URL must be the clean URL (no credentials in it — git would save them in .git/config); give the token at the prompt or in ILR_GIT_TOKEN"; exit 1;; esac
fi
# transient authentication: a credential helper that answers from the environment of THIS process,
# with any configured helpers disabled for the call; nothing is written to disk or logged
if [ -z "$ILR_GIT_TOKEN" ]; then
  if [ -t 0 ]; then read -rs -p "GitHub read-only token for the clone (not echoed, not stored): " ILR_GIT_TOKEN; echo; fi
fi
if [ -z "$ILR_GIT_TOKEN" ] && [ ! -d repo/.git ]; then echo "no token given and /data/ilr/repo does not exist"; exit 1; fi
export ILR_GIT_TOKEN
export GIT_TERMINAL_PROMPT=0
GITAUTH=(-c credential.helper= -c 'credential.helper=!f() { echo "username=x-access-token"; echo "password=${ILR_GIT_TOKEN}"; }; f')
if [ ! -d repo/.git ]; then
  git "${GITAUTH[@]}" clone --quiet "$ILR_GIT_URL" repo
fi
cd repo
git "${GITAUTH[@]}" fetch --quiet --tags
unset ILR_GIT_TOKEN
case "$(git remote get-url origin)" in *@*) echo "remote URL carries credentials — refusing to continue"; exit 1;; esac
git checkout --quiet "$TAG"
git status --porcelain | grep -q . && { echo "working copy is not clean — a production build runs only from the tag"; exit 1; }
echo "at $(git describe --tags --exact-match) $(git rev-parse HEAD)"

echo "== 6/8 Python 3.11 environment (pinned)"
if ! command -v python3.11 >/dev/null; then
  add-apt-repository -y ppa:deadsnakes/ppa >/dev/null
  apt-get update -qq
  apt-get install -y -qq python3.11 python3.11-venv python3.11-dev >/dev/null
fi
python3.11 -c 'import sys; assert sys.version_info[:2] == (3, 11), sys.version'
python3.11 -m venv /data/ilr/venv
/data/ilr/venv/bin/pip install --quiet --upgrade pip
/data/ilr/venv/bin/pip install --quiet -r prod/requirements.lock
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"
/data/ilr/venv/bin/python -m playwright install chromium >/dev/null     # into $PLAYWRIGHT_BROWSERS_PATH, readable by the build user
/data/ilr/venv/bin/python -c "import sys, openpyxl, pandas, pyarrow, PIL, yaml, docx; print('python', sys.version.split()[0], 'ok')"
/data/ilr/venv/bin/python -c "from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); print('chromium', b.version, 'ok'); b.close()"

echo "== 7/8 release manifest"
/data/ilr/venv/bin/python -m prod.release verify --repo /data/ilr/repo --tag "$TAG"

echo "== 8/8 managed identity access"
az login --identity --allow-no-subscriptions >/dev/null
az storage blob list --account-name "$ILR_DATA_ACCOUNT" --container-name dataset --auth-mode login --query "[].{name:name,bytes:properties.contentLength}" -o table
az keyvault secret show --vault-name "$ILR_KEY_VAULT" --name "$ILR_LINK_SECRET" --query "{enabled:attributes.enabled, contentType:contentType}" -o table

cat > /etc/profile.d/ilr.sh <<EOF
export ILR_HOME=/data/ilr
export ILR_REPO=/data/ilr/repo
export ILR_VENV=/data/ilr/venv
export JSDOM=/data/ilr/node/node_modules/jsdom
export ILR_DATA_ACCOUNT=$ILR_DATA_ACCOUNT
export ILR_WEB_ACCOUNT=$ILR_WEB_ACCOUNT
export ILR_KEY_VAULT=$ILR_KEY_VAULT
export ILR_LINK_SECRET=$ILR_LINK_SECRET
export ILR_AFD_PROFILE=$ILR_AFD_PROFILE
export ILR_AFD_ENDPOINT=$ILR_AFD_ENDPOINT
export ILR_RG=$ILR_RG
export PLAYWRIGHT_BROWSERS_PATH=$PLAYWRIGHT_BROWSERS_PATH
export PATH=/data/ilr/venv/bin:\$PATH
EOF
chown -R "${SUDO_USER:-root}" /data/ilr
echo "bootstrap complete — release manifest verified; continue with docs/production/SSS2026_ILR_Operations_Runbook.md"

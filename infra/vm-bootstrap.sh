#!/usr/bin/env bash
# Build-VM bootstrap for the SSS2026 ILR production run (provisioning guide §6.1).
#
#   sudo ILR_GIT_URL=https://github.com/<org>/<repo>.git bash vm-bootstrap.sh <tag>
#
# Optional environment:
#   ILR_GIT_URL      clone URL (a private repo: use a deploy key in /root/.ssh, or a
#                    read-only token in the URL — https://<token>@github.com/<org>/<repo>.git;
#                    the URL is not logged)
#   ILR_DATA_ACCOUNT storage account holding the dataset (default stsss2026ilrdata)
#   ILR_WEB_ACCOUNT  web-origin storage account (default stsss2026ilrweb)
#   ILR_KEY_VAULT    key vault holding the link secret (default kv-sss2026-ilr)
#   ILR_LINK_SECRET  secret name (default sss2026-link-key-v1)
#   ILR_AFD_PROFILE / ILR_AFD_ENDPOINT / ILR_RG   Front Door profile, endpoint and
#                    resource group (defaults afd-sss2026-ilr / sss2026-reports / rg-sss2026-ilr)
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
ILR_GIT_URL="${ILR_GIT_URL:-}"
ILR_DATA_ACCOUNT="${ILR_DATA_ACCOUNT:-stsss2026ilrdata}"
ILR_WEB_ACCOUNT="${ILR_WEB_ACCOUNT:-stsss2026ilrweb}"
ILR_AFD_PROFILE="${ILR_AFD_PROFILE:-afd-sss2026-ilr}"
ILR_AFD_ENDPOINT="${ILR_AFD_ENDPOINT:-sss2026-reports}"
ILR_RG="${ILR_RG:-rg-sss2026-ilr}"
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
  DEV=$(readlink -f /dev/disk/azure/scsi1/lun0 2>/dev/null || true)
  if [ -z "$DEV" ]; then echo "no data disk at lun0 — attach the 1 TB disk and re-run"; exit 1; fi
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
  if [ -z "$ILR_GIT_URL" ]; then echo "ILR_GIT_URL is not set and /data/ilr/repo does not exist"; exit 1; fi
  git clone --quiet "$ILR_GIT_URL" repo
fi
cd repo && git fetch --quiet --tags && git checkout --quiet "$TAG"
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

#!/usr/bin/env bash
# =============================================================================
# Oracle ARM Instance Provisioner
# Retries VM.Standard.A1.Flex (4 OCPU / 24GB) across all ADs until capacity
# is available. Run this once your Oracle PAYG upgrade is approved.
#
# Usage:
#   bash provision_oracle_arm.sh              # retry indefinitely every 15m
#   bash provision_oracle_arm.sh --once       # try once and exit
# =============================================================================

TENANCY="ocid1.tenancy.oc1..aaaaaaaaarpguhwhqq4ladn3asodgnwxnykjgffldwhik4ippigtlleyjdhq"
SUBNET_ID="ocid1.subnet.oc1.phx.aaaaaaaavtyfxco7zrrv35zcr7ud7drhrof2knduf2ucifvw65poc5e2cmna"
IMAGE_ID="ocid1.image.oc1.phx.aaaaaaaawjpnj53xygrfc2dlnoc6m2atx4brqpjeegny2uiegqbie6ajynea"
SSH_KEY_FILE="$HOME/.ssh/oracle_vm.pub"
DISPLAY_NAME="nexus-llm-worker"
OCPUS=4
MEMORY_GB=24
RETRY_INTERVAL=900  # 15 minutes
ADS=("sibW:PHX-AD-1" "sibW:PHX-AD-2" "sibW:PHX-AD-3")
LOG="$HOME/nexus-ai/logs/oracle_provision.log"
ONCE=false

[[ "$1" == "--once" ]] && ONCE=true

mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

try_launch() {
    local ad="$1"
    log "Trying $ad (${OCPUS} OCPU / ${MEMORY_GB}GB)..."

    RESULT=$(oci compute instance launch \
        --compartment-id "$TENANCY" \
        --availability-domain "$ad" \
        --shape "VM.Standard.A1.Flex" \
        --shape-config "{\"ocpus\": ${OCPUS}, \"memoryInGBs\": ${MEMORY_GB}}" \
        --image-id "$IMAGE_ID" \
        --subnet-id "$SUBNET_ID" \
        --assign-public-ip true \
        --display-name "$DISPLAY_NAME" \
        --ssh-authorized-keys-file "$SSH_KEY_FILE" 2>&1)

    if echo "$RESULT" | grep -q '"lifecycle-state"'; then
        INSTANCE_ID=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null)
        log "✅ SUCCESS in $ad — Instance ID: $INSTANCE_ID"
        log "Waiting for public IP..."

        # Poll for public IP
        for i in $(seq 1 20); do
            sleep 15
            IP=$(oci compute instance list-vnics \
                --instance-id "$INSTANCE_ID" \
                --query 'data[0]."public-ip"' \
                --raw-output 2>/dev/null)
            if [[ -n "$IP" && "$IP" != "null" ]]; then
                log "🌐 Public IP: $IP"
                log "SSH: ssh -i ~/.ssh/nexus_oracle opc@$IP"
                # Send Telegram notification
                if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]]; then
                    curl -s -X POST \
                        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
                        -d "chat_id=${TELEGRAM_CHAT_ID}" \
                        -d "text=✅ Oracle ARM instance provisioned!%0AIP: ${IP}%0ASSH: ssh -i ~/.ssh/nexus_oracle opc@${IP}%0AShape: VM.Standard.A1.Flex (${OCPUS} OCPU / ${MEMORY_GB}GB)" \
                        > /dev/null
                fi
                return 0
            fi
            log "  Waiting for IP... attempt $i/20"
        done
        log "Instance running but IP not assigned yet. Check OCI console."
        return 0
    elif echo "$RESULT" | grep -qi "out of host capacity\|out of capacity"; then
        log "  → $ad: Out of capacity"
        return 1
    elif echo "$RESULT" == *"NotAuthorizedOrNotFound"*; then
        log "  → Auth error — upgrade may not be approved yet"
        return 2
    else
        log "  → $ad error: $(echo "$RESULT" | head -c 200)"
        return 1
    fi
}

# Load .env for Telegram
ENV_FILE="$HOME/nexus-ai/.env"
if [[ -f "$ENV_FILE" ]]; then
    export $(grep -v '^#' "$ENV_FILE" | grep -E "TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID" | xargs) 2>/dev/null
fi

log "=== Oracle ARM Provisioner starting ==="
log "Shape: VM.Standard.A1.Flex | OCPUs: $OCPUS | RAM: ${MEMORY_GB}GB"
log "Region: us-phoenix-1 | Retry every: ${RETRY_INTERVAL}s"

ATTEMPT=0
while true; do
    ATTEMPT=$((ATTEMPT + 1))
    log "--- Attempt $ATTEMPT ---"

    for AD in "${ADS[@]}"; do
        try_launch "$AD"
        STATUS=$?
        if [[ $STATUS -eq 0 ]]; then
            log "=== Provisioning complete ==="
            exit 0
        fi
    done

    if $ONCE; then
        log "All ADs out of capacity (--once mode). Exiting."
        exit 1
    fi

    log "All ADs out of capacity. Retrying in $((RETRY_INTERVAL / 60)) minutes..."
    sleep $RETRY_INTERVAL
done

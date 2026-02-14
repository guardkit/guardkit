#!/usr/bin/env bash
#
# graphiti-backup.sh - FalkorDB backup and restore for GuardKit's Graphiti knowledge graph
#
# Usage:
#   ./scripts/graphiti-backup.sh backup [--output DIR]
#   ./scripts/graphiti-backup.sh restore <BACKUP_FILE>
#   ./scripts/graphiti-backup.sh list
#   ./scripts/graphiti-backup.sh verify
#
# Methods:
#   backup  - Redis BGSAVE + volume tar (consistent, no downtime for BGSAVE)
#   restore - Stop container, restore volume, restart
#
# Requirements:
#   - Docker running with guardkit-falkordb container
#

set -euo pipefail

# Configuration
CONTAINER_NAME="guardkit-falkordb"
VOLUME_NAME="docker_falkordb_data"  # Docker Compose prefixes with directory name
BACKUP_DIR="${BACKUP_DIR:-./backups/graphiti}"
COMPOSE_FILE="docker/docker-compose.graphiti.yml"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ─── Helpers ──────────────────────────────────────────────────────────────────

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  GuardKit Graphiti - FalkorDB Backup & Restore${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        exit 1
    fi
}

check_container_running() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        error "Container '${CONTAINER_NAME}' is not running"
        echo "  Start it with: docker compose -f ${COMPOSE_FILE} up -d"
        exit 1
    fi
}

ensure_backup_dir() {
    local dir="${1:-$BACKUP_DIR}"
    mkdir -p "$dir"
}

get_volume_name() {
    # Find the actual volume name (Docker Compose prefixes with project name)
    local volume
    volume=$(docker volume ls --format '{{.Name}}' | grep 'falkordb_data' | head -1)
    if [ -z "$volume" ]; then
        error "FalkorDB data volume not found"
        echo "  Expected a volume matching '*falkordb_data'"
        echo "  Available volumes:"
        docker volume ls --format '  - {{.Name}}' | grep -i falkor || echo "  (none found)"
        exit 1
    fi
    echo "$volume"
}

# ─── Commands ─────────────────────────────────────────────────────────────────

cmd_backup() {
    local output_dir="${1:-$BACKUP_DIR}"
    ensure_backup_dir "$output_dir"

    print_header
    info "Method: Redis BGSAVE + volume backup (tar archive)"

    check_docker

    local volume_name
    volume_name=$(get_volume_name)
    info "Found volume: ${volume_name}"

    local backup_file="${output_dir}/falkordb-backup-${TIMESTAMP}.tar.gz"

    # Trigger BGSAVE if container is running (ensures data flushed to disk)
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        info "Triggering Redis BGSAVE for consistency..."
        docker exec "${CONTAINER_NAME}" redis-cli BGSAVE > /dev/null 2>&1 || true
        # Wait for BGSAVE to complete
        local retries=30
        while [ $retries -gt 0 ]; do
            local bg_status
            bg_status=$(docker exec "${CONTAINER_NAME}" redis-cli LASTSAVE 2>/dev/null || echo "0")
            sleep 1
            local bg_status_new
            bg_status_new=$(docker exec "${CONTAINER_NAME}" redis-cli LASTSAVE 2>/dev/null || echo "0")
            if [ "$bg_status" = "$bg_status_new" ] && [ "$bg_status" != "0" ]; then
                break
            fi
            retries=$((retries - 1))
        done
        info "BGSAVE complete"
    fi

    # Stop container for consistent volume tar
    local was_running=false
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        was_running=true
        info "Stopping FalkorDB for consistent backup..."
        docker compose -f "${COMPOSE_FILE}" down
        sleep 2
    fi

    info "Creating backup archive..."
    docker run --rm \
        -v "${volume_name}:/data" \
        -v "$(cd "$output_dir" && pwd):/backup" \
        alpine tar czf "/backup/$(basename "$backup_file")" -C /data .

    # Restart if it was running
    if [ "$was_running" = true ]; then
        info "Restarting FalkorDB..."
        docker compose -f "${COMPOSE_FILE}" up -d
        info "Waiting for FalkorDB to be healthy..."
        sleep 5
    fi

    local size
    size=$(du -h "$backup_file" | cut -f1)
    echo ""
    info "Backup complete!"
    echo -e "  File: ${GREEN}${backup_file}${NC}"
    echo -e "  Size: ${size}"
    echo ""
    echo "To restore: $0 restore ${backup_file}"
}

cmd_restore() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: ${backup_file}"
        exit 1
    fi

    print_header
    info "Method: Volume restore (tar archive)"
    info "Restoring from: ${backup_file}"

    check_docker

    local volume_name
    volume_name=$(get_volume_name)
    info "Target volume: ${volume_name}"

    # Must stop container
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        warn "Stopping FalkorDB for restore..."
        docker compose -f "${COMPOSE_FILE}" down
        sleep 2
    fi

    info "Restoring data volume..."
    docker run --rm \
        -v "${volume_name}:/data" \
        -v "$(cd "$(dirname "$backup_file")" && pwd):/backup" \
        alpine sh -c "rm -rf /data/* && tar xzf /backup/$(basename "$backup_file") -C /data"

    info "Starting FalkorDB..."
    docker compose -f "${COMPOSE_FILE}" up -d

    info "Waiting for FalkorDB to be healthy..."
    sleep 5

    echo ""
    info "Restore complete!"
    echo "  Run 'guardkit graphiti status' to verify"
}

cmd_list() {
    print_header
    ensure_backup_dir

    info "Backups in ${BACKUP_DIR}:"
    echo ""

    local count=0
    if [ -d "$BACKUP_DIR" ]; then
        for f in "$BACKUP_DIR"/falkordb-backup-*.tar.gz "$BACKUP_DIR"/falkordb-*.rdb "$BACKUP_DIR"/neo4j-backup-*.tar.gz "$BACKUP_DIR"/neo4j-dump-*.dump; do
            if [ -f "$f" ]; then
                local size
                size=$(du -h "$f" | cut -f1)
                local name
                name=$(basename "$f")
                echo -e "  ${GREEN}${name}${NC}  (${size})"
                count=$((count + 1))
            fi
        done
    fi

    if [ "$count" -eq 0 ]; then
        echo "  (no backups found)"
    fi
    echo ""
    echo "Total: ${count} backup(s)"
}

cmd_verify() {
    print_header
    info "Verifying FalkorDB and Graphiti status..."

    check_docker
    check_container_running

    echo ""

    # Check container health
    local health
    health=$(docker inspect --format='{{.State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "unknown")
    if [ "$health" = "healthy" ]; then
        info "Container health: ${GREEN}healthy${NC}"
    else
        warn "Container health: ${YELLOW}${health}${NC}"
    fi

    # Check FalkorDB connectivity via redis-cli
    info "Testing FalkorDB connectivity..."
    if docker exec "${CONTAINER_NAME}" redis-cli PING 2>/dev/null | grep -q "PONG"; then
        info "FalkorDB connection: ${GREEN}OK${NC}"
    else
        error "FalkorDB connection: FAILED"
        exit 1
    fi

    # List graphs
    info "Checking graphs..."
    local graphs
    graphs=$(docker exec "${CONTAINER_NAME}" redis-cli GRAPH.LIST 2>/dev/null || echo "(none)")
    info "Graphs: ${graphs}"

    # Check GuardKit status if available
    if command -v guardkit &> /dev/null; then
        echo ""
        info "Running guardkit graphiti status..."
        guardkit graphiti status
    fi

    echo ""
    info "Verification complete"
}

cmd_help() {
    cat << 'EOF'
GuardKit Graphiti - FalkorDB Backup & Restore

USAGE:
    ./scripts/graphiti-backup.sh <COMMAND> [OPTIONS]

COMMANDS:
    backup [--output DIR]     Volume-based backup (BGSAVE + tar archive)
    restore <BACKUP_FILE>     Restore from volume backup
    list                      List available backups
    verify                    Verify FalkorDB connectivity and data

BACKUP METHOD:

  Volume Backup (backup/restore):
    - Triggers Redis BGSAVE to flush data to disk
    - Stops container briefly for consistent tar of data volume
    - Restarts container after backup completes
    - Best for: Local backups, same-machine restore

OPTIONS:
    --output DIR    Output directory (default: ./backups/graphiti)

ENVIRONMENT:
    BACKUP_DIR      Override default backup directory

EXAMPLES:
    # Create a backup
    ./scripts/graphiti-backup.sh backup

    # Create backup to custom directory
    ./scripts/graphiti-backup.sh backup --output /tmp/backups

    # Restore from backup
    ./scripts/graphiti-backup.sh restore backups/graphiti/falkordb-backup-20260211_120000.tar.gz

    # List all backups (includes legacy Neo4j backups)
    ./scripts/graphiti-backup.sh list

    # Verify after restore
    ./scripts/graphiti-backup.sh verify

MIGRATION FROM NEO4J:
    Old Neo4j backups (neo4j-backup-*.tar.gz, neo4j-dump-*.dump) are still
    listed by the 'list' command but cannot be restored to FalkorDB.
    To migrate data, re-seed using: guardkit graphiti seed --force

NOTES:
    - backup will automatically stop and restart FalkorDB
    - Always run 'verify' after a restore operation
    - FalkorDB data is stored as Redis dump.rdb in the volume
EOF
}

# ─── Main ─────────────────────────────────────────────────────────────────────

main() {
    local command="${1:-help}"
    shift || true

    case "$command" in
        backup)
            local output_dir="$BACKUP_DIR"
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --output) output_dir="$2"; shift 2 ;;
                    *) error "Unknown option: $1"; exit 1 ;;
                esac
            done
            cmd_backup "$output_dir"
            ;;
        restore)
            if [ $# -lt 1 ]; then
                error "Usage: $0 restore <BACKUP_FILE>"
                exit 1
            fi
            cmd_restore "$1"
            ;;
        list)
            cmd_list
            ;;
        verify)
            cmd_verify
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            error "Unknown command: ${command}"
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac
}

main "$@"

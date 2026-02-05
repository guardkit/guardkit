#!/usr/bin/env bash
#
# graphiti-backup.sh - Neo4j backup and restore for GuardKit's Graphiti knowledge graph
#
# Usage:
#   ./scripts/graphiti-backup.sh backup [--output DIR]
#   ./scripts/graphiti-backup.sh restore <BACKUP_FILE>
#   ./scripts/graphiti-backup.sh dump [--output DIR]
#   ./scripts/graphiti-backup.sh load <DUMP_FILE>
#   ./scripts/graphiti-backup.sh list
#   ./scripts/graphiti-backup.sh verify
#
# Methods:
#   backup/restore - Volume-based (fast, same Neo4j version required)
#   dump/load      - neo4j-admin database dump (portable, cross-version)
#
# Requirements:
#   - Docker running with guardkit-neo4j container
#   - For dump/load: Neo4j container must be stopped
#

set -euo pipefail

# Configuration
CONTAINER_NAME="guardkit-neo4j"
VOLUME_NAME="docker_neo4j_data"  # Docker Compose prefixes with directory name
BACKUP_DIR="${BACKUP_DIR:-./backups/graphiti}"
COMPOSE_FILE="docker/docker-compose.graphiti.yml"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="password123"
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
    echo -e "${BLUE}  GuardKit Graphiti - Neo4j Backup & Restore${NC}"
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

check_container_stopped() {
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        error "Container '${CONTAINER_NAME}' must be stopped for this operation"
        echo "  Stop it with: docker compose -f ${COMPOSE_FILE} down"
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
    volume=$(docker volume ls --format '{{.Name}}' | grep 'neo4j_data' | head -1)
    if [ -z "$volume" ]; then
        error "Neo4j data volume not found"
        echo "  Expected a volume matching '*neo4j_data'"
        echo "  Available volumes:"
        docker volume ls --format '  - {{.Name}}' | grep -i neo4j || echo "  (none found)"
        exit 1
    fi
    echo "$volume"
}

# ─── Commands ─────────────────────────────────────────────────────────────────

cmd_backup() {
    local output_dir="${1:-$BACKUP_DIR}"
    ensure_backup_dir "$output_dir"

    print_header
    info "Method: Volume backup (tar archive)"
    info "Backing up Neo4j data volume..."

    check_docker

    local volume_name
    volume_name=$(get_volume_name)
    info "Found volume: ${volume_name}"

    local backup_file="${output_dir}/neo4j-backup-${TIMESTAMP}.tar.gz"

    # Stop container for consistent backup
    local was_running=false
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        was_running=true
        info "Stopping Neo4j for consistent backup..."
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
        info "Restarting Neo4j..."
        docker compose -f "${COMPOSE_FILE}" up -d
        info "Waiting for Neo4j to be healthy..."
        sleep 10
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
        warn "Stopping Neo4j for restore..."
        docker compose -f "${COMPOSE_FILE}" down
        sleep 2
    fi

    info "Restoring data volume..."
    docker run --rm \
        -v "${volume_name}:/data" \
        -v "$(cd "$(dirname "$backup_file")" && pwd):/backup" \
        alpine sh -c "rm -rf /data/* && tar xzf /backup/$(basename "$backup_file") -C /data"

    info "Starting Neo4j..."
    docker compose -f "${COMPOSE_FILE}" up -d

    info "Waiting for Neo4j to be healthy..."
    sleep 15

    echo ""
    info "Restore complete!"
    echo "  Run 'guardkit graphiti status' to verify"
}

cmd_dump() {
    local output_dir="${1:-$BACKUP_DIR}"
    ensure_backup_dir "$output_dir"

    print_header
    info "Method: neo4j-admin database dump (portable)"
    info "Creating database dump..."

    check_docker

    # Container must be stopped for neo4j-admin dump
    local was_running=false
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        was_running=true
        info "Stopping Neo4j (required for neo4j-admin dump)..."
        docker compose -f "${COMPOSE_FILE}" down
        sleep 2
    fi

    local volume_name
    volume_name=$(get_volume_name)
    local dump_file="${output_dir}/neo4j-dump-${TIMESTAMP}.dump"

    info "Running neo4j-admin database dump..."
    docker run --rm \
        -v "${volume_name}:/data" \
        -v "$(cd "$output_dir" && pwd):/dumps" \
        neo4j:5.26.0 \
        neo4j-admin database dump neo4j --to-path=/dumps --overwrite-destination

    # neo4j-admin creates the dump as neo4j.dump in the target directory
    if [ -f "${output_dir}/neo4j.dump" ]; then
        mv "${output_dir}/neo4j.dump" "$dump_file"
    fi

    # Restart if it was running
    if [ "$was_running" = true ]; then
        info "Restarting Neo4j..."
        docker compose -f "${COMPOSE_FILE}" up -d
        sleep 10
    fi

    local size
    size=$(du -h "$dump_file" | cut -f1)
    echo ""
    info "Dump complete!"
    echo -e "  File: ${GREEN}${dump_file}${NC}"
    echo -e "  Size: ${size}"
    echo ""
    echo "This dump is portable across Neo4j 5.x installations."
    echo "To load:  $0 load ${dump_file}"
}

cmd_load() {
    local dump_file="$1"

    if [ ! -f "$dump_file" ]; then
        error "Dump file not found: ${dump_file}"
        exit 1
    fi

    print_header
    info "Method: neo4j-admin database load (portable)"
    info "Loading from: ${dump_file}"

    check_docker

    local volume_name
    volume_name=$(get_volume_name)

    # Must stop container
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        warn "Stopping Neo4j for load..."
        docker compose -f "${COMPOSE_FILE}" down
        sleep 2
    fi

    # Copy dump to temp name expected by neo4j-admin
    local dump_dir
    dump_dir=$(cd "$(dirname "$dump_file")" && pwd)
    local temp_dump="${dump_dir}/neo4j.dump"
    cp "$dump_file" "$temp_dump"

    info "Loading database dump..."
    docker run --rm \
        -v "${volume_name}:/data" \
        -v "${dump_dir}:/dumps" \
        neo4j:5.26.0 \
        neo4j-admin database load neo4j --from-path=/dumps --overwrite-destination

    # Clean up temp file
    rm -f "$temp_dump"

    info "Starting Neo4j..."
    docker compose -f "${COMPOSE_FILE}" up -d

    info "Waiting for Neo4j to be healthy..."
    sleep 15

    echo ""
    info "Load complete!"
    echo "  Run 'guardkit graphiti status' to verify"
}

cmd_list() {
    print_header
    ensure_backup_dir

    info "Backups in ${BACKUP_DIR}:"
    echo ""

    local count=0
    if [ -d "$BACKUP_DIR" ]; then
        for f in "$BACKUP_DIR"/neo4j-backup-*.tar.gz "$BACKUP_DIR"/neo4j-dump-*.dump; do
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
    info "Verifying Neo4j and Graphiti status..."

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

    # Check Neo4j connectivity via cypher-shell
    info "Testing Neo4j connectivity..."
    if docker exec "${CONTAINER_NAME}" cypher-shell -u "${NEO4J_USER}" -p "${NEO4J_PASSWORD}" "RETURN 1 AS test" &> /dev/null; then
        info "Neo4j connection: ${GREEN}OK${NC}"
    else
        error "Neo4j connection: FAILED"
        exit 1
    fi

    # Count nodes
    local node_count
    node_count=$(docker exec "${CONTAINER_NAME}" cypher-shell -u "${NEO4J_USER}" -p "${NEO4J_PASSWORD}" \
        --format plain "MATCH (n) RETURN count(n) AS count" 2>/dev/null | tail -1 | tr -d ' ')
    info "Total nodes: ${node_count}"

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
GuardKit Graphiti - Neo4j Backup & Restore

USAGE:
    ./scripts/graphiti-backup.sh <COMMAND> [OPTIONS]

COMMANDS:
    backup [--output DIR]     Volume-based backup (fast, tar archive)
    restore <BACKUP_FILE>     Restore from volume backup
    dump [--output DIR]       neo4j-admin database dump (portable)
    load <DUMP_FILE>          Load from neo4j-admin dump
    list                      List available backups
    verify                    Verify Neo4j connectivity and data

BACKUP METHODS:

  Volume Backup (backup/restore):
    - Fast: Direct tar of the data volume
    - Requires same Neo4j version on restore
    - Best for: Local backups, same-machine restore

  Database Dump (dump/load):
    - Portable: Works across Neo4j 5.x versions
    - Best for: Migration to another server or Neo4j version
    - Slightly larger file size

OPTIONS:
    --output DIR    Output directory (default: ./backups/graphiti)

ENVIRONMENT:
    BACKUP_DIR      Override default backup directory

EXAMPLES:
    # Create a volume backup
    ./scripts/graphiti-backup.sh backup

    # Create a portable dump for migration
    ./scripts/graphiti-backup.sh dump

    # Restore from backup
    ./scripts/graphiti-backup.sh restore backups/graphiti/neo4j-backup-20250205_120000.tar.gz

    # Load a dump on a new server
    ./scripts/graphiti-backup.sh load backups/graphiti/neo4j-dump-20250205_120000.dump

    # List all backups
    ./scripts/graphiti-backup.sh list

    # Verify after restore
    ./scripts/graphiti-backup.sh verify

MIGRATION TO REMOTE SERVER:
    # 1. Create portable dump on local machine
    ./scripts/graphiti-backup.sh dump

    # 2. Copy dump file to remote server
    scp backups/graphiti/neo4j-dump-*.dump user@remote:/path/to/guardkit/backups/graphiti/

    # 3. On remote server: load the dump
    ./scripts/graphiti-backup.sh load backups/graphiti/neo4j-dump-*.dump

    # 4. Verify on remote
    ./scripts/graphiti-backup.sh verify

NOTES:
    - backup/restore will automatically stop and restart Neo4j
    - dump/load require Neo4j to be stopped (handled automatically)
    - Always run 'verify' after a restore or load operation
    - For production, change the default Neo4j password in docker-compose.graphiti.yml
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
        dump)
            local output_dir="$BACKUP_DIR"
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --output) output_dir="$2"; shift 2 ;;
                    *) error "Unknown option: $1"; exit 1 ;;
                esac
            done
            cmd_dump "$output_dir"
            ;;
        load)
            if [ $# -lt 1 ]; then
                error "Usage: $0 load <DUMP_FILE>"
                exit 1
            fi
            cmd_load "$1"
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

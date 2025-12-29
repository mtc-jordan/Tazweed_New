#!/bin/bash
#===============================================================================
# Tazweed_New Deployment Script
# Repository: mtc-jordan/Tazweed_New
# Branch: main
#===============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - MODIFY THESE FOR YOUR ENVIRONMENT
ODOO_USER="odoo"
ODOO_HOME="/opt/odoo"
ODOO_ADDONS="${ODOO_HOME}/custom-addons"
ODOO_CONFIG="/etc/odoo/odoo.conf"
ODOO_SERVICE="odoo"
REPO_URL="https://github.com/mtc-jordan/Tazweed_New.git"
BRANCH="main"
BACKUP_DIR="/opt/odoo/backups"

#===============================================================================
# Helper Functions
#===============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
}

#===============================================================================
# Pre-deployment Checks
#===============================================================================

pre_checks() {
    log_info "Running pre-deployment checks..."
    
    # Check if Odoo service exists
    if ! systemctl list-units --type=service | grep -q "$ODOO_SERVICE"; then
        log_warning "Odoo service '$ODOO_SERVICE' not found. Adjust ODOO_SERVICE variable."
    fi
    
    # Check if git is installed
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed. Please install git first."
        exit 1
    fi
    
    # Create backup directory if not exists
    mkdir -p "$BACKUP_DIR"
    
    log_success "Pre-deployment checks passed"
}

#===============================================================================
# Backup Function
#===============================================================================

create_backup() {
    log_info "Creating backup of existing addons..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="${BACKUP_DIR}/tazweed_backup_${TIMESTAMP}.tar.gz"
    
    if [ -d "${ODOO_ADDONS}/tazweed_core" ]; then
        tar -czf "$BACKUP_FILE" -C "$ODOO_ADDONS" \
            tazweed_core \
            tazweed_placement \
            tazweed_job_board \
            tazweed_payroll \
            tazweed_wps \
            tazweed_document_center \
            tazweed_automated_workflows \
            tazweed_esignature \
            2>/dev/null || true
        log_success "Backup created: $BACKUP_FILE"
    else
        log_warning "No existing Tazweed modules found to backup"
    fi
}

#===============================================================================
# Stop Odoo Service
#===============================================================================

stop_odoo() {
    log_info "Stopping Odoo service..."
    
    if systemctl is-active --quiet "$ODOO_SERVICE"; then
        systemctl stop "$ODOO_SERVICE"
        log_success "Odoo service stopped"
    else
        log_warning "Odoo service was not running"
    fi
}

#===============================================================================
# Deploy Code
#===============================================================================

deploy_code() {
    log_info "Deploying Tazweed modules from GitHub..."
    
    # Create temp directory
    TEMP_DIR=$(mktemp -d)
    
    # Clone repository
    log_info "Cloning repository..."
    git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$TEMP_DIR"
    
    # List of Tazweed modules to deploy
    MODULES=(
        "tazweed_core"
        "tazweed_placement"
        "tazweed_job_board"
        "tazweed_payroll"
        "tazweed_wps"
        "tazweed_document_center"
        "tazweed_automated_workflows"
        "tazweed_esignature"
    )
    
    # Create addons directory if not exists
    mkdir -p "$ODOO_ADDONS"
    
    # Copy modules
    for module in "${MODULES[@]}"; do
        if [ -d "${TEMP_DIR}/${module}" ]; then
            log_info "Deploying ${module}..."
            rm -rf "${ODOO_ADDONS}/${module}"
            cp -r "${TEMP_DIR}/${module}" "${ODOO_ADDONS}/"
            log_success "${module} deployed"
        else
            log_warning "${module} not found in repository"
        fi
    done
    
    # Set permissions
    chown -R "$ODOO_USER:$ODOO_USER" "$ODOO_ADDONS"
    chmod -R 755 "$ODOO_ADDONS"
    
    # Cleanup
    rm -rf "$TEMP_DIR"
    
    log_success "Code deployment completed"
}

#===============================================================================
# Update Odoo Configuration
#===============================================================================

update_config() {
    log_info "Checking Odoo configuration..."
    
    if [ -f "$ODOO_CONFIG" ]; then
        # Check if addons_path includes our directory
        if ! grep -q "$ODOO_ADDONS" "$ODOO_CONFIG"; then
            log_warning "Adding custom addons path to Odoo config..."
            # Backup config
            cp "$ODOO_CONFIG" "${ODOO_CONFIG}.bak"
            # Add addons path (this is a simple approach, may need adjustment)
            sed -i "s|^addons_path.*|&,${ODOO_ADDONS}|" "$ODOO_CONFIG"
            log_success "Odoo configuration updated"
        else
            log_info "Addons path already configured"
        fi
    else
        log_warning "Odoo config file not found at $ODOO_CONFIG"
    fi
}

#===============================================================================
# Start Odoo Service
#===============================================================================

start_odoo() {
    log_info "Starting Odoo service..."
    
    systemctl start "$ODOO_SERVICE"
    
    # Wait for service to start
    sleep 5
    
    if systemctl is-active --quiet "$ODOO_SERVICE"; then
        log_success "Odoo service started successfully"
    else
        log_error "Failed to start Odoo service"
        log_info "Check logs with: journalctl -u $ODOO_SERVICE -f"
        exit 1
    fi
}

#===============================================================================
# Update Modules in Odoo
#===============================================================================

update_modules() {
    log_info "To update modules in Odoo, run the following command:"
    echo ""
    echo -e "${YELLOW}Option 1: Update via command line${NC}"
    echo "  sudo -u $ODOO_USER $ODOO_HOME/odoo-bin -c $ODOO_CONFIG -d YOUR_DATABASE -u tazweed_core,tazweed_placement,tazweed_job_board,tazweed_payroll,tazweed_wps,tazweed_document_center,tazweed_automated_workflows,tazweed_esignature --stop-after-init"
    echo ""
    echo -e "${YELLOW}Option 2: Update via Odoo UI${NC}"
    echo "  1. Go to Apps menu"
    echo "  2. Click 'Update Apps List'"
    echo "  3. Search for each Tazweed module and click 'Upgrade'"
    echo ""
}

#===============================================================================
# Rollback Function
#===============================================================================

rollback() {
    log_info "Rolling back to previous version..."
    
    # Find latest backup
    LATEST_BACKUP=$(ls -t ${BACKUP_DIR}/tazweed_backup_*.tar.gz 2>/dev/null | head -1)
    
    if [ -z "$LATEST_BACKUP" ]; then
        log_error "No backup found to rollback"
        exit 1
    fi
    
    log_info "Restoring from: $LATEST_BACKUP"
    
    stop_odoo
    
    # Remove current modules
    for module in tazweed_core tazweed_placement tazweed_job_board tazweed_payroll tazweed_wps tazweed_document_center tazweed_automated_workflows tazweed_esignature; do
        rm -rf "${ODOO_ADDONS}/${module}"
    done
    
    # Restore from backup
    tar -xzf "$LATEST_BACKUP" -C "$ODOO_ADDONS"
    chown -R "$ODOO_USER:$ODOO_USER" "$ODOO_ADDONS"
    
    start_odoo
    
    log_success "Rollback completed"
}

#===============================================================================
# Quick Deploy (Pull only - for updates)
#===============================================================================

quick_deploy() {
    log_info "Quick deployment (pull latest changes)..."
    
    if [ -d "${ODOO_ADDONS}/.git" ]; then
        cd "$ODOO_ADDONS"
        git fetch origin
        git reset --hard origin/$BRANCH
        chown -R "$ODOO_USER:$ODOO_USER" "$ODOO_ADDONS"
        log_success "Quick deploy completed"
    else
        log_warning "Not a git repository. Running full deployment..."
        deploy_code
    fi
}

#===============================================================================
# Health Check
#===============================================================================

health_check() {
    log_info "Running health check..."
    
    # Check Odoo service
    if systemctl is-active --quiet "$ODOO_SERVICE"; then
        log_success "Odoo service is running"
    else
        log_error "Odoo service is not running"
        return 1
    fi
    
    # Check if modules exist
    MISSING_MODULES=()
    for module in tazweed_core tazweed_placement tazweed_job_board tazweed_payroll tazweed_wps tazweed_document_center tazweed_automated_workflows tazweed_esignature; do
        if [ ! -d "${ODOO_ADDONS}/${module}" ]; then
            MISSING_MODULES+=("$module")
        fi
    done
    
    if [ ${#MISSING_MODULES[@]} -eq 0 ]; then
        log_success "All Tazweed modules are deployed"
    else
        log_warning "Missing modules: ${MISSING_MODULES[*]}"
    fi
    
    # Check Odoo logs for errors
    if journalctl -u "$ODOO_SERVICE" --since "5 minutes ago" | grep -q "ERROR"; then
        log_warning "Errors found in recent Odoo logs"
        log_info "Check with: journalctl -u $ODOO_SERVICE -f"
    else
        log_success "No errors in recent logs"
    fi
}

#===============================================================================
# Print Usage
#===============================================================================

usage() {
    echo "Tazweed Deployment Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  deploy      Full deployment (backup, stop, deploy, start)"
    echo "  quick       Quick deploy (pull latest changes only)"
    echo "  rollback    Rollback to previous backup"
    echo "  backup      Create backup only"
    echo "  start       Start Odoo service"
    echo "  stop        Stop Odoo service"
    echo "  restart     Restart Odoo service"
    echo "  status      Check deployment status"
    echo "  health      Run health check"
    echo "  help        Show this help message"
    echo ""
    echo "Example:"
    echo "  sudo $0 deploy"
    echo ""
}

#===============================================================================
# Main
#===============================================================================

main() {
    case "${1:-deploy}" in
        deploy)
            check_root
            pre_checks
            create_backup
            stop_odoo
            deploy_code
            update_config
            start_odoo
            health_check
            update_modules
            log_success "Deployment completed successfully!"
            ;;
        quick)
            check_root
            stop_odoo
            quick_deploy
            start_odoo
            health_check
            ;;
        rollback)
            check_root
            rollback
            ;;
        backup)
            check_root
            create_backup
            ;;
        start)
            check_root
            start_odoo
            ;;
        stop)
            check_root
            stop_odoo
            ;;
        restart)
            check_root
            stop_odoo
            start_odoo
            ;;
        status|health)
            health_check
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            log_error "Unknown command: $1"
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

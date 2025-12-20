#!/bin/bash

# Configuration
LOG_FILE="/var/log/monitoring.log"
ALERT_EMAIL="admin@etatcivil.cm"

# Fonction pour logger les messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Vérifier l'utilisation du disque
check_disk_usage() {
    local usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    if [ "$usage" -gt 80 ]; then
        log "ALERTE: Utilisation du disque à ${usage}%"
        # Envoyer une alerte par email
        echo "L'utilisation du disque est à ${usage}% sur $(hostname)" | mail -s "[ALERTE] Utilisation élevée du disque" "${ALERT_EMAIL}"
    fi
}

# Vérifier l'utilisation de la mémoire
check_memory_usage() {
    local total_mem=$(free -m | awk '/^Mem:/{print $2}')
    local used_mem=$(free -m | awk '/^Mem:/{print $3}')
    local usage=$((used_mem * 100 / total_mem))
    
    if [ "$usage" -gt 80 ]; then
        log "ALERTE: Utilisation de la mémoire à ${usage}%"
    fi
}

# Vérifier que les services essentiels sont en cours d'exécution
check_services() {
    local services=("postgres" "redis" "nginx" "gunicorn")
    
    for service in "${services[@]}"; do
        if ! pgrep -x "$service" > /dev/null; then
            log "ERREUR: Le service $service ne fonctionne pas"
            # Tenter de redémarrer le service
            systemctl restart "$service" 2>/dev/null || true
        fi
    done
}

# Vérifier la santé de l'application
check_app_health() {
    local health_url="http://localhost/health/"
    local status=$(curl -s -o /dev/null -w "%{http_code}" "$health_url" 2>/dev/null || echo "000")
    
    if [ "$status" != "200" ]; then
        log "ERREUR: L'application ne répond pas correctement (HTTP $status)"
    fi
}

# Exécuter les vérifications
log "Début du monitoring"
check_disk_usage
check_memory_usage
check_services
check_app_health
log "Fin du monitoring"

exit 0

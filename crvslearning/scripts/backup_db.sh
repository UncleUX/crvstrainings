#!/bin/bash

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"
LOG_FILE="/var/log/backup.log"

# Charger les variables d'environnement si nécessaire
if [ -f "/app/.env" ]; then
    export $(grep -v '^#' /app/.env | xargs)
fi

# Créer le répertoire de sauvegarde s'il n'existe pas
mkdir -p "${BACKUP_DIR}"

# Fonction pour logger les messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Vérifier les variables d'environnement nécessaires
if [ -z "${DB_NAME}" ] || [ -z "${DB_USER}" ] || [ -z "${DB_PASSWORD}" ]; then
    log "ERREUR: Les variables d'environnement DB_NAME, DB_USER et DB_PASSWORD doivent être définies"
    exit 1
fi

log "Début de la sauvegarde de la base de données ${DB_NAME}"

# Exécuter la sauvegarde avec pg_dump
if PGPASSWORD="${DB_PASSWORD}" pg_dump -h "${DB_HOST:-db}" -U "${DB_USER}" -d "${DB_NAME}" \
    --no-owner --no-acl --format=custom | gzip > "${BACKUP_FILE}"; then
    
    # Vérifier que le fichier de sauvegarde a été créé et n'est pas vide
    if [ -s "${BACKUP_FILE}" ]; then
        log "Sauvegarde réussie : ${BACKUP_FILE}"
        
        # Nettoyer les anciennes sauvegardes (conservez les 7 dernières)
        ls -t "${BACKUP_DIR}"/backup_*.sql.gz | tail -n +8 | xargs rm -f 2>/dev/null
        log "Nettoyage des anciennes sauvegardes terminé"
        
        # Vérifier l'intégrité de la sauvegarde
        if gzip -t "${BACKUP_FILE}" 2>/dev/null; then
            log "Vérification de l'intégrité de la sauvegarde : OK"
            exit 0
        else
            log "ERREUR: La sauvegarde est corrompue"
            exit 1
        fi
    else
        log "ERREUR: Le fichier de sauvegarde est vide"
        exit 1
    fi
else
    log "ERREUR: Échec de la sauvegarde de la base de données"
    exit 1
fi

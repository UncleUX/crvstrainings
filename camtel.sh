#!/bin/bash
# PROD-INTEGRITY BACKEND-ONLY + WHITENOISE | VERSION 2026.05.30
# VPS IP: 172.16.2.40 | PORT: 8000
set -e

# --- Configuration ---
APP="crvslearning"
PORT=8000
LISTEN_IP="172.16.2.40"
DIR="/opt/peace/crvslearning"
VENV="$DIR/venv"
REPO_URL="VOTRE_URL_GIT_ICI" # Remplacez par votre URL
CONFIG_SOURCE="/opt/peace/settings.py"
CONFIG_DEST="$DIR/crvslearning/settings.py"

# --- Design ---
CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log_step() { echo -e "\n${CYAN}>> ${1}${NC}"; }
log_err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- 1. Préparation du répertoire (Correction de l'imbrication) ---
log_step "PREPARATION DU REPERTOIRE"
if [ ! -d "$DIR" ]; then
    sudo mkdir -p "$DIR"
fi
sudo chown $USER:$USER "$DIR"
cd "$DIR"

# Nettoyage et Clonage propre (évite l'imbrication)
log_step "SYNCHRONISATION DU DEPOT GIT"
rm -rf ./* ./.git
git clone "$REPO_URL" .

# --- 2. Audit et Libération du Port ---
log_step "AUDIT ET LIBERATION DU PORT $PORT"
if command -v lsof >/dev/null 2>&1; then
    sudo lsof -t -i:$PORT | xargs sudo kill -9 || true
fi

# --- 3. Dépendances ---
log_step "SYNCHRONISATION DES COUCHES LOGICIELLES"
sudo apt update
sudo apt install -y python3-venv python3-pip

# --- 4. Build Python & WhiteNoise ---
log_step "CONFIGURATION ENVIRONNEMENT & WHITENOISE"
rm -rf "$VENV"
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install psycopg2-binary psutil gunicorn whitenoise

# --- 5. Synchronisation Settings ---
log_step "APPLICATION DE LA CONFIGURATION (SETTINGS.PY)"
if [ -f "$CONFIG_SOURCE" ]; then
    cp "$CONFIG_SOURCE" "$CONFIG_DEST"
else
    log_err "Le fichier $CONFIG_SOURCE est introuvable."
fi

# --- 6. Intégration Assets ---
log_step "PREPARATION DES ASSETS (WHITENOISE)"
python manage.py collectstatic --noinput

# --- 7. Service Systemd ---
log_step "ACTIVATION DU SERVICE BACKEND"
cat <<EOF | sudo tee /etc/systemd/system/$APP.service > /dev/null
[Unit]
Description=Gunicorn Backend for $APP
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$DIR
ExecStart=$VENV/bin/gunicorn --workers 3 --bind $LISTEN_IP:$PORT $APP.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $APP
sudo systemctl restart $APP

# --- 8. Vérification ---
sleep 2
if systemctl is-active --quiet $APP; then
    echo -e "\n${GREEN}============================================================"
    echo " MISSION ACCOMPLIE : BACKEND OPERATIONNEL"
    echo " REPERTOIRE : $DIR (Propre)"
    echo -e "============================================================${NC}\n"
fi

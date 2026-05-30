#!/bin/bash
# PROD-INTEGRITY | STYLE: TERMINAL-VINTAGE
# ARCHITECTURE: RACINE (settings/req) -> crvslearning (manage.py)
# REPO: https://github.com/UncleUX/peace

set -e

# --- Design ---
GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'
typewrite() { for (( i=0; i<${#1}; i++ )); do echo -n "${1:$i:1}"; sleep 0.015; done; echo ""; }
log_step() { echo -e "\n${CYAN}>> ${1}${NC}"; }

# --- Configuration ---
APP="crvslearning"
REPO_URL="https://github.com/UncleUX/peace"
DIR="/opt/peace/crvslearning"
DJANGO_PROJECT_DIR="$DIR/crvslearning"
CONFIG_SOURCE="$DIR/settings.py"
CONFIG_DEST="$DJANGO_PROJECT_DIR/crvslearning/settings.py"
VENV="$DIR/venv"

# --- 1. Initialisation ---
clear
echo -e "${GREEN}************************************************************"
echo -e "*  BUNEC // SECURE DEPLOYMENT // SYSTEM 2026.05            *"
echo -e "************************************************************${NC}"

sudo mkdir -p "$DIR"
sudo chown $USER:$USER "$DIR"
cd "$DIR"

# --- 2. Clonage ---
log_step "SYNC DEPOT GIT"
if [ ! -d ".git" ]; then
    git clone "$REPO_URL" .
else
    git pull origin main
fi
typewrite "Dépôt synchronisé."

# --- 3. Copie Config (settings.py) ---
log_step "APPLICATION DE LA CONFIGURATION"
if [ -f "$CONFIG_SOURCE" ]; then
    cp "$CONFIG_SOURCE" "$CONFIG_DEST"
    typewrite "settings.py déplacé vers le sous-dossier de configuration."
else
    echo -e "${RED}[!] Erreur: settings.py introuvable à la racine.${NC}"
    exit 1
fi

# --- 4. Environnement ---
log_step "SYNCHRONISATION DES COUCHES"
python3 -m venv "$VENV"
source "$VENV/bin/activate"
pip install -q -r requirements.txt gunicorn whitenoise psycopg2-binary

# --- 5. Assets ---
log_step "PREPARATION ASSETS"
cd "$DJANGO_PROJECT_DIR"
python manage.py collectstatic --noinput > /dev/null
typewrite "Assets statiques compilés."

# --- 6. Service Systemd ---
log_step "ACTIVATION DU SERVICE"
cat <<EOF | sudo tee /etc/systemd/system/$APP.service > /dev/null
[Unit]
Description=Gunicorn Backend for $APP
After=network.target

[Service]
User=$USER
WorkingDirectory=$DJANGO_PROJECT_DIR
ExecStart=$VENV/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 crvslearning.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $APP
sudo systemctl restart $APP

# --- 7. Conclusion ---
echo -e "\n${GREEN}============================================================"
typewrite ">> MISSION ACCOMPLIE // SYSTEME ONLINE"
typewrite ">> REPO: $REPO_URL"
typewrite ">> STATUS: SECURE // OPERATIONAL"
echo -e "============================================================${NC}\n"

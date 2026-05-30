#!/bin/bash
# PROD-INTEGRITY | STYLE: TERMINAL-VINTAGE
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
DJANGO_DIR="$DIR/crvslearning"
VENV="$DIR/venv"
CONFIG_SOURCE="$DIR/settings.py"
CONFIG_DEST="$DJANGO_DIR/crvslearning/settings.py"
REQ_FILE="$DJANGO_DIR/requirements.txt"

# --- 1. Initialisation ---
clear
echo -e "${GREEN}************************************************************"
echo -e "* BUNEC // SECURE DEPLOYMENT // SYSTEM 2026.05             *"
echo -e "************************************************************${NC}"

typewrite "Initialisation de la structure système..."
sudo mkdir -p "$DIR"
sudo chown $USER:$USER "$DIR"
cd "$DIR"

# --- 2. Clonage ---
log_step "SYNC DEPOT GIT"
typewrite "Connexion au dépôt distant..."
if [ ! -d ".git" ]; then
    git clone "$REPO_URL" .
else
    git pull origin main
fi
typewrite "Dépôt synchronisé avec succès."

# --- 3. Copie Config ---
log_step "APPLICATION DE LA CONFIGURATION"
typewrite "Vérification et injection du fichier settings.py..."
if [ -f "$CONFIG_SOURCE" ]; then
    cp "$CONFIG_SOURCE" "$CONFIG_DEST"
    typewrite "Configuration appliquée dans le dossier projet."
else
    echo -e "${RED}[!] Erreur: settings.py introuvable à la racine.${NC}"
    exit 1
fi

# --- 4. Environnement & Dépendances ---
log_step "SYNCHRONISATION DES COUCHES LOGICIELLES"
typewrite "Création de l'environnement virtuel..."
python3 -m venv "$VENV"
source "$VENV/bin/activate"

if [ -f "$REQ_FILE" ]; then
    typewrite "DEBUT DE L'INSTALLATION DES DEPENDANCES :"
    # On affiche tout sans -q pour que vous voyiez tout défiler
    pip install -r "$REQ_FILE"
    typewrite "Installation des dépendances terminée."
else
    echo -e "${RED}[!] Erreur: requirements.txt introuvable dans $DJANGO_DIR${NC}"
    exit 1
fi

typewrite "Installation des services complémentaires..."
pip install gunicorn whitenoise psycopg2-binary
typewrite "Couches logicielles synchronisées."

# --- 5. Assets ---
log_step "PREPARATION ASSETS"
typewrite "Collecte des fichiers statiques pour le serveur..."
cd "$DJANGO_DIR"
python manage.py collectstatic --noinput
typewrite "Assets compilés avec succès."

# --- 6. Service Systemd ---
log_step "ACTIVATION DU SERVICE"
typewrite "Configuration du démon systemd..."
cat <<EOF | sudo tee /etc/systemd/system/$APP.service > /dev/null
[Unit]
Description=Gunicorn Backend for $APP
After=network.target

[Service]
User=$USER
WorkingDirectory=$DJANGO_DIR
ExecStart=$VENV/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 crvslearning.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

typewrite "Rechargement des services système..."
sudo systemctl daemon-reload
sudo systemctl enable $APP
sudo systemctl restart $APP
typewrite "Service Gunicorn actif."

# --- 7. Conclusion ---
echo -e "\n${GREEN}============================================================"
typewrite ">> MISSION ACCOMPLIE // SYSTEME ONLINE"
typewrite ">> REPO: $REPO_URL"
typewrite ">> STATUS: SECURE // OPERATIONAL"
echo -e "============================================================${NC}\n"

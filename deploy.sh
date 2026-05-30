#!/bin/bash
# PROD-INTEGRITY | DEPLOYMENT CONTROLLER: peacecrvs
# Usage: sudo ./deploy.sh
set -e

# --- Configuration ---
SERVICE_NAME="peacecrvs"
PORT=8000
LISTEN_IP="172.16.2.40"
REPO_URL="https://github.com/UncleUX/peace"
DIR="/opt/peace/crvslearning"
VENV="$DIR/venv"
CONFIG_SOURCE="/opt/peace/settings.py"
CONFIG_DEST="$DIR/crvslearning/settings.py"
REQUIRED_PORTS=( 8000 )

# --- 1. Audit des Ports (Logique OpenCRVS) ---
echo "=== AUDIT D'INTEGRITE DES PORTS ==="
for port in "${REQUIRED_PORTS[@]}"
do
    if lsof -nP -iTCP:$port -sTCP:LISTEN >/dev/null; then
        echo -e "Le port \033[31m$port\033[0m est déjà utilisé."
        echo "Veuillez identifier le processus avec : lsof -i :$port"
        exit 1
    else
        echo -e "Port $port : \033[32mDISPONIBLE\033[0m"
    fi
done

# --- 2. Confirmation ---
echo -e "\n\033[1;33mATTENTION : Le déploiement de peacecrvs va écraser l'instance existante.\033[0m"
read -p "Voulez-vous procéder ? [y/N] " confirm
if [[ $confirm != [yY] ]]; then
    echo "Déploiement annulé."
    exit 0
fi

# --- 3. Arrêt Propre ---
echo -e "\n>>> ARRÊT DU SERVICE $SERVICE_NAME..."
sudo systemctl stop $SERVICE_NAME || true

# --- 4. Mise à jour / Clonage ---
echo ">>> SYNCHRONISATION DU CODE..."
if [ ! -d "$DIR/.git" ]; then
    sudo mkdir -p $DIR
    sudo git clone $REPO_URL $DIR
else
    cd $DIR && sudo git pull origin main
fi

# --- 5. Build et Configuration ---
echo ">>> CONSTRUCTION DE L'ENVIRONNEMENT..."
cd $DIR
sudo apt update && sudo apt install -y python3-venv python3-pip
[ -d "venv" ] && rm -rf venv
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install psycopg2-binary psutil gunicorn whitenoise

if [ -f "$CONFIG_SOURCE" ]; then
    cp "$CONFIG_SOURCE" "$CONFIG_DEST"
fi

python manage.py collectstatic --noinput

# --- 6. Installation Systemd ---
echo ">>> MISE EN SERVICE..."
cat <<EOF | sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null
[Unit]
Description=Gunicorn Backend for $SERVICE_NAME
After=network.target

[Service]
User=root
WorkingDirectory=$DIR
ExecStart=$VENV/bin/gunicorn --workers 3 --bind $LISTEN_IP:$PORT crvslearning.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

echo -e "\n\033[32m=============================================================="
echo " MISSION ACCOMPLIE : $SERVICE_NAME EST OPÉRATIONNEL"
echo " STATUS : RUNNING (PORT $PORT)"
echo "==============================================================\033[0m"

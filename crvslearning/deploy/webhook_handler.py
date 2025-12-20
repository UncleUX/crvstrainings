#!/usr/bin/env python3
"""
Serveur webhook pour le déploiement automatique
"""
import hmac
import hashlib
import subprocess
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from os import getenv
from pathlib import Path

# Configuration
SECRET = getenv('WEBHOOK_SECRET', 'votre_secret_ici').encode()
REPO_DIR = Path(__file__).parent.parent.absolute()
LOG_FILE = REPO_DIR / 'deploy' / 'deploy.log'
BRANCH = 'main'  # Branche à surveiller

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Gère les requêtes POST du webhook"""
        if self.path != '/webhook':
            self.send_response(404)
            self.end_headers()
            return

        # Vérifier la signature
        signature = self.headers.get('X-Hub-Signature-256', '').replace('sha256=', '')
        if not self.verify_signature(signature):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'Invalid signature')
            return

        # Lire les données
        content_length = int(self.headers['Content-Length'])
        payload = self.rfile.read(content_length)
        
        try:
            data = json.loads(payload.decode('utf-8'))
            
            # Vérifier si c'est un push sur la branche surveillée
            if data.get('ref') == f'refs/heads/{BRANCH}':
                self.log('Démarrage du déploiement...')
                self.deploy()
                self.log('Déploiement terminé avec succès')
                self.send_response(200)
            else:
                self.log(f'Push détecté sur une autre branche: {data.get("ref")}')
                self.send_response(200)
                
        except Exception as e:
            self.log(f'Erreur: {str(e)}', level='ERROR')
            self.send_response(500)
            
        self.end_headers()

    def verify_signature(self, signature):
        """Vérifie la signature du webhook"""
        if not SECRET:
            return True  # Désactive la vérification si aucun secret n'est défini
            
        payload = self.rfile.read(int(self.headers['Content-Length']))
        expected = hmac.new(SECRET, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)

    def log(self, message, level='INFO'):
        """Écrit dans le fichier de log"""
        log_entry = f'[{level}] {message}\n'
        with open(LOG_FILE, 'a') as f:
            f.write(log_entry)
        
        print(log_entry, end='')

    def deploy(self):
        """Exécute le processus de déploiement"""
        try:
            # Se déplacer dans le répertoire du dépôt
            self.log('Mise à jour du dépôt...')
            subprocess.run(['git', 'pull'], cwd=REPO_DIR, check=True)
            
            # Redémarrer les conteneurs
            self.log('Redémarrage des services...')
            subprocess.run(
                ['docker-compose', '-f', 'docker-compose.prod.yml', 'up', '-d', '--build'],
                cwd=REPO_DIR,
                check=True
            )
            
            # Exécuter les migrations
            self.log('Exécution des migrations...')
            subprocess.run(
                ['docker-compose', '-f', 'docker-compose.prod.yml', 'exec', 'web', 'python', 'manage.py', 'migrate', '--noinput'],
                cwd=REPO_DIR,
                check=True
            )
            
            # Collecter les fichiers statiques
            self.log('Collecte des fichiers statiques...')
            subprocess.run(
                ['docker-compose', '-f', 'docker-compose.prod.yml', 'exec', 'web', 'python', 'manage.py', 'collectstatic', '--noinput'],
                cwd=REPO_DIR,
                check=True
            )
            
        except subprocess.CalledProcessError as e:
            self.log(f'Erreur lors du déploiement: {str(e)}', level='ERROR')
            raise

def run(server_class=HTTPServer, handler_class=WebhookHandler, port=8001):
    """Démarre le serveur webhook"""
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Démarrage du serveur webhook sur le port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()

# Plateforme d'E-Learning CRVS

Plateforme complète d'apprentissage en ligne avec gestion des cours, évaluations, certifications et interactions en temps réel.

## 🚀 Fonctionnalités principales

- **Gestion des utilisateurs** avec rôles multiples (Étudiants, Formateurs, Administrateurs)
- **Cours en ligne** avec supports multimédias
- **Système d'évaluation** avec quiz et devoirs
- **Chat en temps réel** entre utilisateurs
- **Notifications** en temps réel
- **Gestion des certifications**
- **Classes virtuelles** avec intégration Jitsi Meet
- Tableau de bord d'administration avancé avec Django Jazzmin

## 🛠 Prérequis

- Python 3.8+
- PostgreSQL / MySQL / SQLite
- Redis (pour les tâches asynchrones et le chat en temps réel)
- Node.js & npm (pour les assets frontend)
- Docker & Docker Compose (recommandé pour le déploiement)

## ⚙️ Configuration

### Variables d'environnement

Créez un fichier `.env` à la racine du projet avec les variables suivantes :

```env
# Configuration Django
SECRET_KEY=votre_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de données
DATABASE_URL=postgres://user:password@db:5432/dbname

# Redis
REDIS_URL=redis://redis:6379/0

# Configuration Jitsi Meet
MEETING_BASE_URL=https://meet.jit.si

# Configuration Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-email-password
```

### Installation des dépendances

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: .\venv\Scripts\activate

# Installer les dépendances Python
pip install -r requirements.txt

# Installer les dépendances frontend (si nécessaire)
npm install
```

## 🚀 Déploiement avec Docker (Recommandé)

1. **Configurer les variables d'environnement** dans `.env`

2. **Démarrer les conteneurs** :
   ```bash
   docker-compose -f docker-compose.base.yml -f docker-compose.prod.yml up -d --build
   ```

3. **Appliquer les migrations** :
   ```bash
   docker-compose -f docker-compose.base.yml -f docker-compose.prod.yml exec web python manage.py migrate
   ```

4. **Créer un superutilisateur** :
   ```bash
   docker-compose -f docker-compose.base.yml -f docker-compose.prod.yml exec web python manage.py createsuperuser
   ```

5. **Collecter les fichiers statiques** :
   ```bash
   docker-compose -f docker-compose.base.yml -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
   ```

## 🛠 Développement

### Lancer l'environnement de développement

```bash
# Démarrer les services
docker-compose -f docker-compose.base.yml -f docker-compose.dev.yml up -d

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser

# Lancer le serveur de développement
python manage.py runserver
```

### Structure du projet

```
crvslearning/
├── apps/
│   ├── users/           # Gestion des utilisateurs
│   ├── courses/         # Gestion des cours
│   ├── evaluations/     # Système d'évaluation
│   ├── notifications/   # Notifications en temps réel
│   ├── interactions/    # Chat et interactions
│   └── certifications/  # Gestion des certifications
├── core/               # Fonctionnalités principales
├── static/             # Fichiers statiques (CSS, JS, images)
├── media/              # Fichiers uploadés
├── templates/          # Templates HTML
├── requirements/       # Fichiers de dépendances
└── docker/             # Configuration Docker
```

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support

Pour toute question ou support, veuillez ouvrir une issue sur le dépôt ou contacter l'équipe de développement.

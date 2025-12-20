# CRVS Classroom — Lives, Enregistrements et Classes par Catégorie

Ce document décrit:
- La migration des classes vers une liaison par Catégorie
- Le flux d’un Live (Jitsi) avec enregistrement (Option A: Jibri) et publication
- Les endpoints et la charge utile du webhook d’enregistrement

## 1) Classes liées à une Catégorie (au lieu d’un Cours)

Changements majeurs:
- `classrooms.models.Classroom`
  - Champ `course` supprimé
  - Nouveau champ `category = ForeignKey(Category, SET_NULL, null=True, blank=True)`
- Vues et templates mis à jour:
  - Création de classe (`classrooms:create`) attend `category_id` (obligatoire)
  - Pages affichent la Catégorie au lieu du Cours

Migrations à exécuter:
```
python manage.py makemigrations classrooms
python manage.py migrate
```

Notes:
- Si vous aviez des classes existantes, adaptez une migration de données si besoin (copie de l’ancienne `course.category` vers `classroom.category`).

## 2) Lives Jitsi et enregistrement (Option A — Jibri)

Changements majeurs:
- `classrooms.models.LiveSession`
  - Ajout `recording_ready: bool = False`
  - Ajout `recording_url: URLField(blank=True)`
- Endpoint webhook (non authentifié par défaut) pour finaliser l’enregistrement:
  - `POST /classrooms/recording/webhook/`
  - `Content-Type: application/json`
  - Corps JSON: `{ "session_id": <int>, "recording_url": "https://.../file.mp4" }`
  - Effet: met à jour la session (`recording_ready=true`, `recording_url`) — l’UI affiche un bouton “Voir l’enregistrement” dans la page Détail Classe

### 2.1 Démarrer/Rejoindre un Live
- `classrooms:session_start` et `classrooms:session_join` construisent un nom de salle déterministe: `CRVS_<JOINCODE>_<SESSIONID>` et redirigent vers `MEETING_BASE_URL` (par défaut `https://meet.jit.si`).
- Réglez la variable d’environnement `MEETING_BASE_URL` si vous utilisez une instance Jitsi auto-hébergée.

### 2.2 Brancher Jibri
1. Déployer Jibri et le configurer pour votre instance Jitsi (voir doc Jitsi/Jibri officielle).
2. À la fin d’un enregistrement, faites appeler par Jibri (ou un service relais) le webhook:
```
POST https://<votre-domaine>/classrooms/recording/webhook/
Content-Type: application/json

{
  "session_id": 123,
  "recording_url": "https://storage.example.com/recordings/CRVS_XXXX_123.mp4"
}
```
3. L’interface Détail Classe affichera “Voir l’enregistrement” en face de la session.

### 2.3 Sécuriser le webhook (recommandé)
- Ajoutez un en-tête secret, par ex `X-Webhook-Token: <SECRET>` côté Jibri ou service émetteur, et vérifiez-le dans la vue `recording_webhook`.
- Option alternative: signature HMAC du corps et validation serveur.

## 3) Publication vers une Leçon (optionnel)
- Étape suivante possible: ajouter un bouton “Publier vers une leçon” à partir d’une session avec `recording_ready=true`.
- Flux: sélection Cours > Module > Leçon (modale), puis création d’un `LessonVideo` qui pointe vers `recording_url` (si vous utilisez une URL HTTP) ou déclenche un upload.

## 4) Points UI/UX
- Navbar: icône loupe pour la recherche, icône d’alimentation (⏻) pour la déconnexion.
- Page Classe: affiche la Catégorie et le lien d’enregistrement lorsque disponible.

## 5) Dépannage
- Si les modales ne s’ouvrent pas (Bootstrap): vérifier l’inclusion de `bootstrap.bundle.min.js` en bas de `base.html`.
- Si le webhook renvoie 400: vérifier `session_id` (existant) et `recording_url` (non vide), ainsi que le `Content-Type: application/json`.

## 6) Roadmap
- Sécurisation du webhook par secret/signature.
- Publication automatique d’une `LessonVideo` vers une leçon cible selon une règle (ex: dernière leçon suivie, ou mapping classe→leçon).

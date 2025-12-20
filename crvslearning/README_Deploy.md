# Déploiement one-host (App + Jitsi + Jibri)

Ce guide décrit le déploiement de l’application CRVSCLASSROOM, de Jitsi et de Jibri sur un seul hôte avec docker compose.

## 1) Prérequis
- Docker Engine + docker compose v2
- Ports ouverts: 80 (HTTP), 10000/udp (JVB), 8443 (Jitsi web si conservé), 6379 (dev), etc.
- DNS pointant vers votre hôte si exposition publique

## 2) Variables d’environnement
- Copiez `.env.example` vers `.env` et renseignez:
  - SECRET_KEY (Django)
  - WEBHOOK_TOKEN (secret pour le webhook enregistrement)
  - MEETING_BASE_URL (url publique Jitsi, par ex https://meet.local ou votre domaine)
  - PUBLIC_MEET_URL (url publique utilisée par jitsi/web)
  - XMPP_DOMAIN, JICOFO_* et JVB_* (secrets Jitsi)
  - Optionnel Jibri finalize:
    - PUBLIC_BASE_URL (si vous servez /recordings via Nginx)
    - WEBHOOK_URL (ex: http://nginx/classrooms/recording/webhook/)

## 3) Démarrage
Exécutez:
```
docker compose \
  -f docker-compose.base.yml \
  -f docker-compose.jitsi.yml \
  -f docker-compose.override.yml \
  up -d --build
```

Cela démarre:
- web (Django) + nginx + redis (stack app)
- prosody + web-meet + jicofo + jvb + jibri (stack Jitsi/Jibri)

## 4) Vérifications
- Application: http://<host>/ → doit répondre
- Jitsi: https://<host>:8443/ → interface Jitsi
- Webhook: tester avec curl (remplacez tokens/ids):
```
curl -X POST http://<host>/classrooms/recording/webhook/ \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: $WEBHOOK_TOKEN" \
  -d '{"session_id":1,"recording_url":"http://<host>/recordings/test.mp4"}'
```
Réponse attendue: `{ "status": "ok" }` si la session existe.

## 5) Enregistrements
- Les fichiers produits par Jibri sont montés dans `./deploy/jibri/recordings` et servis par Nginx sur `/recordings/`.
- Le script `deploy/jibri/finalize.sh` tente d’extraire `session_id` du nom de fichier (pattern `_*_<SESSIONID>.mp4`) et poste le webhook.
- Adaptez la logique si votre schéma de nommage diffère.

## 6) Débogage
- Logs app: `docker compose logs -f web`
- Logs nginx: `docker compose logs -f nginx`
- Logs Jibri: `docker compose -f docker-compose.jitsi.yml logs -f jibri`
- Erreurs communes:
  - 400 invalid token: vérifier `X-Webhook-Token` et `WEBHOOK_TOKEN`.
  - 400 missing fields: vérifier `session_id` et `recording_url` dans le JSON.
  - Pas d’enregistrement: vérifier `finalize.sh`, droits volumes, présence des MP4, et la connectivité réseau vers `WEBHOOK_URL`.
  - JVB NAT: si derrière NAT strict, exposez et mappez correctement le port UDP 10000 et configurez STUN/TURN au besoin.

## 7) Production
- Ajoutez un reverse proxy TLS (ex: Nginx avec certbot) pour servir en HTTPS.
- Externalisez Redis et la base de données si nécessaire.
- Ajustez `PUBLIC_MEET_URL`, `MEETING_BASE_URL` vers votre domaine HTTPS.

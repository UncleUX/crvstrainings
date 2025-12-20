import json
import logging
import time
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from core.models import MessageModel

# Configuration du logger
logger = logging.getLogger(__name__)
User = get_user_model()

# Configure logger
logger = logging.getLogger(__name__)
User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Ce consommateur gère les connexions WebSocket pour la messagerie instantanée.
    Il gère les connexions utilisateur, l'envoi/réception de messages et la gestion des groupes.
    """
    
    async def connect(self):
        """Gère une nouvelle connexion WebSocket."""
        try:
            # Vérifier si l'utilisateur est authentifié
            if self.scope["user"].is_anonymous:
                logger.warning("Tentative de connexion WebSocket non authentifiée")
                await self.close()
                return
            
            # Stocker les informations utilisateur et de groupe
            self.user = self.scope["user"]
            self.group_name = f"user_{self.user.id}"
            
            # Ajouter l'utilisateur à son groupe personnel
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            # Accepter la connexion WebSocket
            await self.accept()
            logger.info(f"WebSocket connecté: {self.user.username} dans le groupe {self.group_name}")
            
            # Mettre à jour le statut de dernière connexion
            await self.update_last_seen()
            
            # Envoyer la confirmation de connexion
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Vous êtes maintenant connecté au chat !',
                'user': {
                    'id': self.user.id,
                    'username': self.user.username,
                    'avatar': self.user.get_avatar_display() if hasattr(self.user, 'get_avatar_display') else None,
                    'is_online': True
                },
                'status': 'connected',
                'timestamp': timezone.now().isoformat()
            }, cls=DjangoJSONEncoder))
            
        except Exception as e:
            logger.error(f"Error in WebSocket connect: {str(e)}", exc_info=True)
            try:
                await self.close()
            except:
                pass

    async def disconnect(self, close_code):
        """Gère la déconnexion WebSocket."""
        if hasattr(self, 'group_name'):
            try:
                # Retirer l'utilisateur de son groupe
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name
                )
                logger.info(f"WebSocket déconnecté: {getattr(self, 'user', 'Inconnu')} du groupe {self.group_name}")
                
                # Mettre à jour le statut de dernière connexion
                if hasattr(self, 'user'):
                    await self.update_last_seen()
            except Exception as e:
                logger.error(f"Erreur lors de la déconnexion WebSocket: {str(e)}", exc_info=True)

    @database_sync_to_async
    def update_last_seen(self):
        """Met à jour le champ last_seen de l'utilisateur."""
        if hasattr(self.user, 'last_seen'):
            self.user.last_seen = timezone.now()
            self.user.save(update_fields=['last_seen'])
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Gère les messages WebSocket entrants.
        
        Format de message attendu :
        {
            'type': 'chat_message',  # ou 'typing', 'read_receipt', 'typing_status'
            'recipient_id': <int>,
            'message': <str>,
            'message_id': <int> (optionnel, pour les accusés de lecture)
        }
        """
        if not text_data:
            logger.warning("Message vide reçu")
            return
            
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            # Mettre à jour le statut de dernière connexion à chaque message
            await self.update_last_seen()
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing_indicator(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
            elif message_type == 'typing_status':
                await self.handle_typing_status(data)
            else:
                logger.warning(f"Type de message inconnu: {message_type}")
                await self.send_error(f"Type de message non pris en charge: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            await self.send_error("Invalid message format")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            await self.send_error("An error occurred while processing your message")
    
    async def handle_chat_message(self, data):
        """Gère les messages de chat entrants."""
        recipient_id = data.get('recipient_id')
        message_text = data.get('message')
        
        if not recipient_id or not message_text:
            await self.send_error("Destinataire ou message manquant")
            return
        
        if not recipient_id or not message_text:
            logger.warning(f"Missing required fields in chat message: {data}")
            await self.send_error("Missing required fields")
            return
        
        # Get or generate message ID
        message_id = data.get('message_id') or f"msg_{self.user.id}_{int(time.time() * 1000)}"
        
        # Save message to database
        try:
            message = await self.save_message(
                user=self.user,
                recipient_id=recipient_id,
                message=message_text,
                message_id=message_id
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du message: {str(e)}", exc_info=True)
            await self.send_error("Erreur lors de l'enregistrement du message")
            return
        
        # Envoyer le message au destinataire
        await self.channel_layer.group_send(
            f"user_{recipient_id}",
            {
            # Envoyer le message au WebSocket
            await self.send(text_data=json.dumps({
                'type': 'chat_message',
                'message': message_data
            }, cls=DjangoJSONEncoder))
            
            logger.info(f"Message sent to WebSocket: {message_data.get('id', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error in chat_message: {str(e)}")
            logger.error(f"Event data: {event}")
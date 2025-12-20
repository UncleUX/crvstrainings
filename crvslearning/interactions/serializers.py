from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatRoom, ChatMessage, Notification

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les profils utilisateurs"""
    full_name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'avatar']
        read_only_fields = ['id', 'username', 'email']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}" if obj.first_name else obj.username
    
    def get_avatar(self, obj):
        if hasattr(obj, 'profile') and obj.profile.avatar:
            return obj.profile.avatar.url
        return None

class ChatRoomSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les salles de chat"""
    members = UserProfileSerializer(many=True, read_only=True)
    member_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=User.objects.all(),
        source='members'
    )
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'roomId', 'type', 'name', 'members', 'member_ids', 
            'created_at', 'updated_at', 'last_message', 'unread_count'
        ]
        read_only_fields = ['roomId', 'created_at', 'updated_at', 'last_message', 'unread_count']
    
    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return {
                'content': last_message.message,
                'timestamp': last_message.timestamp,
                'sender': UserProfileSerializer(last_message.sender).data
            }
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.messages.filter(
                ~Q(sender=request.user),
                read=False
            ).count()
        return 0
    
    def create(self, validated_data):
        members = validated_data.pop('members', [])
        chat_room = ChatRoom.objects.create(**validated_data)
        chat_room.members.set(members)
        return chat_room

class ChatMessageSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les messages de chat"""
    sender = UserProfileSerializer(read_only=True)
    recipient = UserProfileSerializer(read_only=True)
    is_own = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'chat', 'sender', 'recipient', 'message', 
            'timestamp', 'read', 'read_at', 'is_own'
        ]
        read_only_fields = ['id', 'timestamp', 'read', 'read_at', 'is_own']
    
    def get_is_own(self, obj):
        request = self.context.get('request')
        return request and request.user == obj.sender
    
    def create(self, validated_data):
        request = self.context.get('request')
        chat_room = self.context.get('chat_room')
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("L'utilisateur doit être connecté pour envoyer un message.")
        
        if not chat_room:
            raise serializers.ValidationError("La salle de chat est requise.")
        
        # Déterminer le destinataire (pour les messages directs)
        recipient = None
        if chat_room.type == 'DM':
            recipient = chat_room.members.exclude(id=request.user.id).first()
        
        message = ChatMessage.objects.create(
            chat=chat_room,
            sender=request.user,
            recipient=recipient,
            **validated_data
        )
        
        return message

class NotificationSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les notifications"""
    sender = UserProfileSerializer(read_only=True)
    recipient = UserProfileSerializer(read_only=True)
    time_since = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'sender', 'recipient', 'message', 'notification_type',
            'read', 'created_at', 'url', 'time_since'
        ]
        read_only_fields = ['id', 'created_at', 'time_since']
    
    def get_time_since(self, obj):
        from django.utils.timesince import timesince
        return timesince(obj.created_at) + ' ago'
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Ajouter des données supplémentaires en fonction du type de notification
        if instance.notification_type == 'MESSAGE' and hasattr(instance, 'message'):
            representation['preview'] = instance.message.message[:100]  # Afficher un aperçu du message
        return representation

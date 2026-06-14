from rest_framework import serializers
from django.contrib.auth.models import User
from .models import StudyBlock, Comment, Permission, DiveActivity, DiveLog
from users.models import UserProfile, ProfileFieldTemplate

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_superuser']

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'role', 'is_instructor', 'profile_data', 'dni', 'age', 'phone', 'rank', 'destination', 'weight', 'height', 'first_name', 'last_name']

    def update(self, instance, validated_data):
        # Correct way to handle multiple pops from same nested dict if mapped by source
        # DRF merges source='user.first_name' into validated_data['user']['first_name']
        user_data = validated_data.pop('user', {})
        fname = user_data.get('first_name')
        lname = user_data.get('last_name')

        if fname is not None:
            instance.user.first_name = fname
        if lname is not None:
            instance.user.last_name = lname

        if fname is not None or lname is not None:
            instance.user.save()

        return super().update(instance, validated_data)

class ProfileFieldTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileFieldTemplate
        fields = '__all__'

class CommentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.ReadOnlyField(source='doctor.username')
    class Meta:
        model = Comment
        fields = ['id', 'block', 'doctor', 'doctor_name', 'content', 'status', 'created_at', 'verified_signature']
        read_only_fields = ['doctor']

class StudyBlockSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    user_details = UserSerializer(source='user', read_only=True)
    access_level = serializers.SerializerMethodField()

    class Meta:
        model = StudyBlock
        fields = ['id', 'user', 'user_details', 'title', 'description', 'created_at', 'study_date', 'pdf_attachment', 'comments', 'access_level']
        read_only_fields = ['user']

    def get_access_level(self, obj):
        request = self.context.get('request')
        if not request or request.user == obj.user:
            return 'OWNER'
        perms = Permission.objects.filter(grantor=obj.user, grantee=request.user)
        for p in perms:
            if "ALL" in p.shared_items or str(obj.id) in p.shared_items:
                return p.access_level
        return 'NONE'

class PermissionSerializer(serializers.ModelSerializer):
    grantee_email = serializers.EmailField(write_only=True, required=False)
    grantee_details = UserSerializer(source='grantee', read_only=True)
    grantor_details = UserSerializer(source='grantor', read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'grantor', 'grantor_details', 'grantee', 'grantee_details', 'grantee_email', 'access_level', 'shared_items', 'created_at']
        read_only_fields = ['grantor', 'grantee']

    def create(self, validated_data):
        # Remove grantee_email from validated_data before creating model instance
        validated_data.pop('grantee_email', None)
        return super().create(validated_data)

class DiveActivitySerializer(serializers.ModelSerializer):
    instructor_name = serializers.ReadOnlyField(source='instructor.username')
    safety_diver_name = serializers.ReadOnlyField(source='safety_diver.profile.first_name', default='')
    medic_name = serializers.ReadOnlyField(source='medic.profile.first_name', default='')
    supervisor_name = serializers.ReadOnlyField(source='supervisor.profile.first_name', default='')

    class Meta:
        model = DiveActivity
        fields = '__all__'
        read_only_fields = ['instructor']

class DiveLogSerializer(serializers.ModelSerializer):
    activity_details = DiveActivitySerializer(source='activity', read_only=True)
    diver_name = serializers.ReadOnlyField(source='diver.username')

    class Meta:
        model = DiveLog
        fields = '__all__'
        read_only_fields = ['token', 'diver', 'is_completed', 'completed_at']

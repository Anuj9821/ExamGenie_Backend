# papers/serializers.py
from rest_framework import serializers
from .models import Paper, Section, Question

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

class SectionSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Section
        fields = '__all__'

class PaperSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Paper
        fields = '__all__'
# papers/models.py
from django.db import models
from django.contrib.auth.models import User
from examgenie import settings

class Paper(models.Model):
    user_id = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=255)
    subject_name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    topics = models.JSONField()  # Store topics as a JSON array
    total_marks = models.IntegerField()
    duration = models.IntegerField()  # In minutes
    include_formula = models.BooleanField(default=False)
    include_diagrams = models.BooleanField(default=False)
    include_answer_key = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class Section(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=50)
    question_type = models.CharField(max_length=20)  # mcq, numerical, descriptive, programming
    num_questions = models.IntegerField()
    marks_per_question = models.IntegerField()
    
    def __str__(self):
        return f"{self.paper.title} - {self.name}"

class Question(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='questions')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=20)  # mcq, numerical, descriptive, programming
    difficulty = models.CharField(max_length=20)  # easy, medium, hard
    cognitive_level = models.CharField(max_length=20)  # remember, understand, apply, analyze
    marks = models.IntegerField()
    options = models.JSONField(null=True, blank=True)  # For MCQs
    answer = models.TextField()
    is_practical = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Question {self.id} - {self.paper.title}"
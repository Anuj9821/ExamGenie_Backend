from django.db import models
from django.utils import timezone

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
    status = models.CharField(max_length=20, default='draft')
    created_at = models.DateTimeField(default=timezone.now)  # Use default instead of auto_now_add
    updated_at = models.DateTimeField(default=timezone.now)  # Use default instead of auto_now
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()  # Set updated_at on every save
        super().save(*args, **kwargs)

class Section(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=50)
    question_type = models.CharField(max_length=20)  # mcq, numerical, descriptive, programming
    num_questions = models.IntegerField()
    marks_per_question = models.IntegerField()
    instructions = models.TextField(blank=True, null=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.paper.title} - {self.name}"
    
    class Meta:
        ordering = ['order']
    
    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

class Question(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='questions')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=20)  # mcq, numerical, descriptive, programming
    difficulty = models.CharField(max_length=20)  # easy, medium, hard
    cognitive_level = models.CharField(max_length=20)  # remember, understand, apply, analyze
    marks = models.IntegerField()
    options = models.JSONField(null=True, blank=True)  # For MCQs
    answer = models.TextField(blank=True)
    is_practical = models.BooleanField(default=False)
    topic = models.CharField(max_length=100, blank=True, null=True)
    tags = models.JSONField(null=True, blank=True)
    diagram = models.TextField(blank=True, null=True)
    formula_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Question {self.id} - {self.paper.title}"
    
    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
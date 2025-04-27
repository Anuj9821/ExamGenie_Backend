# papers/views.py
import json
import requests
import traceback
import random
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from .models import Paper, Section, Question
from .serializers import PaperSerializer

class TestOllamaView(APIView):
    def get(self, request):
        try:
            return Response({"message": "Ollama API is working!"})
        except Exception as e:
            print(f"Error in TestOllamaView: {str(e)}")
            traceback.print_exc()
            return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaperViewSet(viewsets.ModelViewSet):
    serializer_class = PaperSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Paper.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def user(self, request):
        papers = self.get_queryset()
        serializer = self.get_serializer(papers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        data = request.data if request.data else self.get_dummy_paper_params()
        
        try:
            # Create paper object with status
            paper = Paper.objects.create(
                user_id=request.user.id,
                title=f"{data['subjectName']} Exam Paper",
                subject_name=data['subjectName'],
                department=data['department'],
                topics=data['topics'],
                total_marks=data['totalMarks'],
                duration=data['duration'],
                include_formula=data.get('includeFormula', False),
                include_diagrams=data.get('includeDiagrams', False),
                include_answer_key=data.get('includeAnswerKey', True),
                status='draft'
            )
            
            # Create sections with order
            for index, section_data in enumerate(data['sections']):
                section = Section.objects.create(
                    paper=paper,
                    name=section_data['name'],
                    question_type=section_data['questionType'],
                    num_questions=section_data['numQuestions'],
                    marks_per_question=section_data['marksPerQuestion'],
                    instructions=section_data.get('instructions', ''),
                    order=index
                )
            
            # Generate questions using Ollama
            generated_questions = self.generate_questions_with_ollama(data)
            
            # Save generated questions with additional fields
            for question_data in generated_questions:
                section = Section.objects.filter(paper=paper, name=question_data['sectionName']).first()
                
                if not section:
                    continue
                
                Question.objects.create(
                    paper=paper,
                    section=section,
                    text=question_data['text'],
                    question_type=question_data['questionType'],
                    difficulty=question_data['difficulty'],
                    cognitive_level=question_data['cognitiveLevel'],
                    marks=question_data['marks'],
                    options=question_data.get('options'),
                    answer=question_data.get('answer', ''),
                    is_practical=question_data['isPractical'],
                    topic=question_data.get('topic', ''),
                    tags=question_data.get('tags', []),
                    diagram=question_data.get('diagram', None),
                    formula_required=question_data.get('formulaRequired', False)
                )
            
            # Update paper status to complete
            paper.status = 'published'
            paper.save()
            
            serializer = self.get_serializer(paper)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_dummy_paper_params(self):
        """Return dummy paper parameters for testing"""
        return {
            'subjectName': 'Database Management Systems',
            'department': 'Computer Science',
            'topics': ['SQL', 'Normalization', 'Transaction Management', 'Indexing', 'ER Modeling'],
            'totalMarks': 100,
            'duration': 180,
            'includeFormula': True,
            'includeDiagrams': True,
            'includeAnswerKey': True,
            'sections': [
                {
                    'name': 'Multiple Choice Questions',
                    'questionType': 'mcq',
                    'numQuestions': 10,
                    'marksPerQuestion': 2
                },
                {
                    'name': 'Short Answer Questions',
                    'questionType': 'descriptive',
                    'numQuestions': 5,
                    'marksPerQuestion': 5
                },
                {
                    'name': 'SQL Programming',
                    'questionType': 'programming',
                    'numQuestions': 3,
                    'marksPerQuestion': 10
                },
                {
                    'name': 'Numerical Problems',
                    'questionType': 'numerical',
                    'numQuestions': 5,
                    'marksPerQuestion': 4
                }
            ],
            'difficultyDistribution': {
                'easy': 30,
                'medium': 50,
                'hard': 20
            },
            'cognitiveDistribution': {
                'remember': 20,
                'understand': 30,
                'apply': 30,
                'analyze': 20
            },
            'practicalTheoretical': {
                'theoretical': 60,
                'practical': 40
            }
        }
    
    def generate_questions_with_ollama(self, paper_params):
        """Generate questions using Ollama API"""
        # Skip actual API call and directly use mock questions
        # return self.generate_mock_questions(paper_params)
        
        # The code below is kept for reference but not used
    
        # Prepare a detailed prompt for Ollama
        prompt = self.prepare_ollama_prompt(paper_params)
        
        # Call Ollama API
        try:
            # Adjust the URL and model based on your Ollama setup
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'mistral', # or whatever model you're using
                    'prompt': prompt,
                    'stream': False
                }
            )
            
            if response.status_code == 200:
                # Parse the response to extract questions
                result = response.json()
                generated_content = result.get('response', '')
                
                # Process the generated content to extract questions
                questions = self.parse_ollama_response(generated_content, paper_params)  
            else:
                # Fallback to mock questions if Ollama fails
                questions = self.generate_mock_questions(paper_params)
                
        except Exception as e:
            print(f"Error calling Ollama API: {e}")
            # Fallback to mock questions
            questions = self.generate_mock_questions(paper_params)
            
        return questions
    
    def prepare_ollama_prompt(self, paper_params):
        """Prepare a detailed prompt for Ollama to generate appropriate questions"""
        prompt = f"""
        Generate a question paper for the subject '{paper_params['subjectName']}' in the '{paper_params['department']}' department.
        The paper covers the following topics: {', '.join(paper_params['topics'])}.
        
        The paper has the following sections:
        """
        
        for section in paper_params['sections']:
            prompt += f"\n- {section['name']}: {section['numQuestions']} {section['questionType']} questions, {section['marksPerQuestion']} marks each"
        
        prompt += f"""
        
        The difficulty distribution should be:
        - Easy: {paper_params['difficultyDistribution']['easy']}%
        - Medium: {paper_params['difficultyDistribution']['medium']}%
        - Hard: {paper_params['difficultyDistribution']['hard']}%
        
        The cognitive level distribution should be:
        - Remember/Knowledge: {paper_params['cognitiveDistribution']['remember']}%
        - Understand/Comprehension: {paper_params['cognitiveDistribution']['understand']}%
        - Apply: {paper_params['cognitiveDistribution']['apply']}%
        - Analyze: {paper_params['cognitiveDistribution']['analyze']}%
        
        The balance between theoretical and practical questions should be:
        - Theoretical: {paper_params['practicalTheoretical']['theoretical']}%
        - Practical: {paper_params['practicalTheoretical']['practical']}%
        
        Generate the questions in JSON format as an array where each question has the following structure:
        {{
            "id": number,
            "sectionName": "section name",
            "text": "question text",
            "questionType": "mcq/numerical/descriptive/programming",
            "difficulty": "easy/medium/hard",
            "cognitiveLevel": "remember/understand/apply/analyze",
            "marks": number,
            "options": ["A", "B", "C", "D"] (only for MCQs),
            "answer": "correct answer",
            "isPractical": boolean
        }}
        
        Return only the JSON array of questions, properly formatted.
        """
        
        return prompt
    
    def parse_ollama_response(self, generated_content, paper_params):
        """Parse the response from Ollama to extract questions"""
        # This implementation will depend on how your Ollama model formats its response
        try:
            # Try to extract JSON array from the response
            # The response might be the raw JSON or might contain other text
            start_idx = generated_content.find('[')
            end_idx = generated_content.rfind(']') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_content = generated_content[start_idx:end_idx]
                questions = json.loads(json_content)
                return questions
            else:
                # Fallback to mock questions if parsing fails
                return self.generate_mock_questions(paper_params)
                
        except Exception as e:
            print(f"Error parsing Ollama response: {e}")
            # Fallback to mock questions
            return self.generate_mock_questions(paper_params)
    
    def generate_mock_questions(self, paper_params):
        """Generate mock questions as a fallback"""
        questions = []
        question_id = 1
        
        # Sample question templates for each topic and question type
        topic_templates = {
            'SQL': {
                'mcq': [
                    "Which SQL statement is used to retrieve data from a database?",
                    "What is the purpose of the GROUP BY clause in SQL?",
                    "Which of the following is NOT a valid SQL join type?"
                ],
                'descriptive': [
                    "Explain the difference between INNER JOIN and OUTER JOIN in SQL.",
                    "Describe how subqueries work in SQL and provide an example."
                ],
                'programming': [
                    "Write a SQL query to retrieve the name and department of all employees who earn more than the average salary.",
                    "Write a SQL query that uses GROUP BY and HAVING to find departments with more than 10 employees."
                ],
                'numerical': [
                    "If a database table has 1000 rows and a query returns 200 rows, what is the selectivity ratio of the query?"
                ]
            },
            'Normalization': {
                'mcq': [
                    "Which normal form eliminates transitive dependencies?",
                    "What is the highest normal form that a relation can satisfy?"
                ],
                'descriptive': [
                    "Explain the concept of functional dependency in database normalization.",
                    "Compare and contrast 3NF and BCNF with examples."
                ],
                'numerical': [
                    "A table has 5 attributes and 3 candidate keys. Calculate the maximum number of functional dependencies possible."
                ]
            },
            'Transaction Management': {
                'mcq': [
                    "Which property of ACID ensures that a transaction brings the database from one valid state to another?",
                    "What concurrency control protocol uses timestamps to order transactions?"
                ],
                'descriptive': [
                    "Explain the difference between optimistic and pessimistic concurrency control.",
                    "Describe the two-phase commit protocol and its importance in distributed transactions."
                ],
                'numerical': [
                    "Calculate the wait-for graph for the following transaction schedule: T1→T2, T2→T3, T3→T4, T4→T1."
                ]
            },
            'Indexing': {
                'mcq': [
                    "Which data structure is commonly used for implementing indexes in databases?",
                    "What type of index would be most efficient for range queries?"
                ],
                'descriptive': [
                    "Compare B-tree and hash-based indexing techniques.",
                    "Explain the concept of index clustering and when it should be used."
                ],
                'numerical': [
                    "Calculate the height of a B+ tree with 1000 records, if each node can store up to 100 keys."
                ]
            },
            'ER Modeling': {
                'mcq': [
                    "In ER modeling, what does a diamond shape represent?",
                    "Which relationship type has a maximum cardinality of one on both sides?"
                ],
                'descriptive': [
                    "Explain how to convert a many-to-many relationship to relational schema.",
                    "Describe the differences between strong and weak entities with examples."
                ],
                'programming': [
                    "Design an ER diagram for a library management system with entities for books, authors, and borrowers."
                ]
            }
        }
        
        # MCQ options templates
        mcq_options = {
            'SQL': [
                ["SELECT", "RETRIEVE", "GET", "FETCH"],
                ["To group rows with similar values", "To filter rows after aggregation", "To sort the result set", "To join tables"],
                ["INNER JOIN", "NATURAL JOIN", "OUTER JOIN", "BETWEEN JOIN"]
            ],
            'Normalization': [
                ["First Normal Form (1NF)", "Second Normal Form (2NF)", "Third Normal Form (3NF)", "Boyce-Codd Normal Form (BCNF)"],
                ["3NF", "BCNF", "4NF", "5NF"]
            ],
            'Transaction Management': [
                ["Atomicity", "Consistency", "Isolation", "Durability"],
                ["Two-Phase Locking", "Timestamp Ordering", "Multi-Version Concurrency Control", "Optimistic Concurrency Control"]
            ],
            'Indexing': [
                ["Linked List", "Array", "B-Tree", "Hash Table"],
                ["Hash Index", "B-Tree Index", "Bitmap Index", "Dense Index"]
            ],
            'ER Modeling': [
                ["Entity", "Attribute", "Relationship", "Cardinality"],
                ["One-to-one", "One-to-many", "Many-to-one", "Many-to-many"]
            ]
        }
        
        # Sample answers for MCQs
        mcq_answers = {
            'SQL': ["A", "A", "D"],
            'Normalization': ["C", "D"],
            'Transaction Management': ["B", "B"],
            'Indexing': ["C", "B"],
            'ER Modeling': ["C", "A"]
        }
        
        # Generate questions for each section
        for section in paper_params['sections']:
            section_name = section['name']
            question_type = section['questionType']
            num_questions = section['numQuestions']
            marks_per_question = section['marksPerQuestion']
            
            # Track which templates have been used to avoid duplicates
            used_templates = set()
            
            for i in range(num_questions):
                # Determine difficulty based on distribution
                difficulty = self.get_random_weighted_category(paper_params['difficultyDistribution'])
                
                # Determine cognitive level based on distribution
                cognitive_level = self.get_random_weighted_category(paper_params['cognitiveDistribution'])
                
                # Determine if question is practical or theoretical
                is_practical = random.random() * 100 < paper_params['practicalTheoretical']['practical']
                
                # Select a random topic that has templates for this question type
                available_topics = [topic for topic in paper_params['topics'] 
                                   if topic in topic_templates and question_type in topic_templates[topic]]
                if not available_topics:
                    # Fallback to any topic if no templates are available
                    topic = random.choice(paper_params['topics'])
                    question_text = f"{'Practical' if is_practical else 'Theoretical'} {question_type} question on {topic} ({difficulty} difficulty)"
                else:
                    topic = random.choice(available_topics)
                    
                    # Get templates for this topic and question type
                    templates = topic_templates[topic][question_type]
                    
                    # Get a template that hasn't been used yet
                    available_templates = [idx for idx, _ in enumerate(templates) if (topic, question_type, idx) not in used_templates]
                    if available_templates:
                        template_idx = random.choice(available_templates)
                        used_templates.add((topic, question_type, template_idx))
                        question_text = templates[template_idx]
                    else:
                        # All templates used, create a generic one
                        question_text = f"{'Practical' if is_practical else 'Theoretical'} {question_type} question on {topic} ({difficulty} difficulty)"
                
                # Create question object
                question = {
                    'id': question_id,
                    'sectionName': section_name,
                    'text': question_text,
                    'questionType': question_type,
                    'difficulty': difficulty,
                    'cognitiveLevel': cognitive_level,
                    'marks': marks_per_question,
                    'isPractical': is_practical,
                    'answer': 'Sample answer for this question'
                }
                
                # Add options for MCQs
                if question_type == 'mcq':
                    if topic in mcq_options and len(mcq_options[topic]) > 0:
                        options_idx = random.randint(0, len(mcq_options[topic])-1)
                        question['options'] = mcq_options[topic][options_idx]
                        
                        # Get corresponding answer if available
                        if topic in mcq_answers and options_idx < len(mcq_answers[topic]):
                            question['answer'] = mcq_answers[topic][options_idx]
                        else:
                            question['answer'] = random.choice(['A', 'B', 'C', 'D'])
                    else:
                        question['options'] = [f"Option A for {topic}", f"Option B for {topic}", 
                                              f"Option C for {topic}", f"Option D for {topic}"]
                        question['answer'] = random.choice(['A', 'B', 'C', 'D'])
                
                questions.append(question)
                question_id += 1
        
        return questions
    
    def get_random_weighted_category(self, distribution):
        """Get a random category based on weighted distribution"""
        rand = random.random() * 100
        cumulative_weight = 0
        
        for category, weight in distribution.items():
            cumulative_weight += weight
            if rand <= cumulative_weight:
                return category
        
        # Default fallback
        return list(distribution.keys())[0]
# papers/views.py
import hashlib
from io import BytesIO
import json
import re
from django.http import HttpResponse
import fitz
import requests
import traceback
import random
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import Paper
from .serializers import PaperSerializer
from bson import ObjectId
from pymongo import MongoClient
from utils.db_utils import get_paper
from datetime import datetime, timezone
from pymongo import ASCENDING
import os
from dotenv import load_dotenv
from rest_framework.decorators import api_view, permission_classes
from utils.db_utils import db
from xhtml2pdf import pisa
from django.template.loader import render_to_string
from utils.db_utils import insert_section, insert_question, update_paper_status, insert_paper
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.core.files.storage import FileSystemStorage


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        load_dotenv()  # Load .env variables

        mongo_uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DB")

        client = MongoClient(mongo_uri)
        self.db = client[db_name]

    def get_queryset(self):
        # This still uses Django ORM for relational models (Django's Paper model)
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

            # Ensure user.id is accessed correctly
            user_id = str(request.user._id)  # This will get the _id from the MongoDB user
            
            paper_doc = {
                "user_id": user_id,
                "title": f"{data['subjectName']} Exam Paper",
                "subject_name": data['subjectName'],
                "department": data['department'],
                "topics": data['topics'],
                "total_marks": data.get('totalMarks', 0),
                "duration": data['duration'],
                "include_formula": data.get('includeFormula', False),
                "include_diagrams": data.get('includeDiagrams', False),
                "include_answer_key": data.get('includeAnswerKey', True),
                "status": "draft",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            # 1. Insert Paper into MongoDB
            paper_id = insert_paper(paper_doc, user_id)
            # paper_id = ObjectId("681878d00b4563cb1baa6b48")  # Convert to ObjectId for MongoDB
            if not paper_id:
                return Response({"error": "Failed to create paper"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # # 2. Insert Sections into MongoDB and keep track of their IDs
            section_ids = {}
            for index, section_data in enumerate(data['sections']):
                section_id = insert_section(section_data, paper_id, index)
                section_ids[section_data['name']] = section_id

            # # 3. Generate Questions using Ollama
            generated_questions = self.generate_questions_with_ollama(data)
            # # 4. Insert Questions into MongoDB
            for question_data in generated_questions:
                section_name = question_data['sectionName']
                if section_name not in section_ids:
                    continue

                insert_question(question_data, paper_id, section_ids[section_name])

            # # 5. Update Paper Status to "published"
            update_paper_status(paper_id)

            #6. Retrieve the newly created paper data
            paper = get_paper(paper_id)
            if not paper:
                return Response({"error": "Paper not found"}, status=status.HTTP_404_NOT_FOUND)
            # 7. Return the paper data
            return Response(self.serialize_paper(paper,paper_id), status=status.HTTP_201_CREATED)

        except Exception as e:
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def serialize_paper(self, paper_doc, paper_id):
        # Get sections for this paper

        sections = list(self.db["sections"].find({"paper_id": paper_id}).sort([("order", ASCENDING)]))

        
        # Prepare section-wise question lists
        section_id_to_questions = {}
        for section in sections:
            questions = list(self.db["questions"].find({"section_id": section["_id"]}))
            section_id_to_questions[str(section["_id"])] = [
                {
                    "id": str(q["_id"]),
                    "text": q["text"],
                    "question_type": q["question_type"],
                    "difficulty": q["difficulty"],
                    "cognitive_level": q["cognitive_level"],
                    "marks": q["marks"],
                    "options": q.get("options"),
                    "answer": q.get("answer", ""),
                    "is_practical": q["is_practical"],
                    "topic": q.get("topic", ""),
                    "tags": q.get("tags", []),
                    "diagram": q.get("diagram"),
                    "formula_required": q.get("formula_required", False),
                }
                for q in questions
            ]

        # Serialize sections with nested questions
        serialized_sections = []
        for section in sections:
            serialized_sections.append({
                "id": str(section["_id"]),
                "name": section["name"],
                "question_type": section["question_type"],
                "num_questions": section["num_questions"],
                "marks_per_question": section["marks_per_question"],
                "instructions": section.get("instructions", ""),
                "order": section["order"],
                "questions": section_id_to_questions.get(str(section["_id"]), [])
            })
        # Final serialized paper with sections and questions
        return {
            "id": str(paper_doc["_id"]),
            "user_id": paper_doc["user_id"],
            "title": paper_doc["title"],
            "subject_name": paper_doc["subject_name"],
            "department": paper_doc["department"],
            "topics": paper_doc["topics"],
            "total_marks": paper_doc["total_marks"],
            "duration": paper_doc["duration"],
            "include_formula": paper_doc["include_formula"],
            "include_diagrams": paper_doc["include_diagrams"],
            "include_answer_key": paper_doc["include_answer_key"],
            "status": paper_doc["status"],
            "sections": serialized_sections
        }


    @action(detail=False, methods=['post'], url_path='upload-question-paper')
    def upload_question_paper(self, request):
        """Upload and process PDF question paper"""
        try:
            # Get form data
            uploaded_file = request.FILES.get('file')
            subject_name = request.data.get('subjectName', '')
            subject_code = request.data.get('subjectCode', '')
            exam_type = request.data.get('examType', '')

            if not uploaded_file:
                return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

            if not subject_name:
                return Response({'error': 'Subject name is required'}, status=status.HTTP_400_BAD_REQUEST)

            if not uploaded_file.name.lower().endswith('.pdf'):
                return Response({'error': 'Only PDF files are supported'}, status=status.HTTP_400_BAD_REQUEST)

            # Define local storage path
            temp_dir = os.path.join(settings.BASE_DIR, 'media', 'temp_pdfs')
            os.makedirs(temp_dir, exist_ok=True)

            # Use local file system storage (not S3)
            local_storage = FileSystemStorage(location=temp_dir)
            file_name = local_storage.save(uploaded_file.name, ContentFile(uploaded_file.read()))
            file_path = local_storage.path(file_name)

            try:
                # Process PDF and extract questions
                questions = self.extract_questions_from_pdf(
                    file_path, subject_name, subject_code, exam_type, request.user
                )

                # Save questions to MongoDB
                saved_questions = self.save_questions_to_db(questions)

                # Clean up temporary file
                local_storage.delete(file_name)

                return Response({
                    'success': True,
                    'message': f'Successfully processed {len(saved_questions)} questions',
                    'questions': saved_questions
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                # Clean up file if something goes wrong
                if local_storage.exists(file_name):
                    local_storage.delete(file_name)
                raise e

        except Exception as e:
            traceback.print_exc()
            return Response({
                'error': f'Processing failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='update-question')
    def update_question(self, request):
        """Update an existing question"""
        try:
            data = request.data
            question_id = data.get('id')
            question_text = data.get('question_text')
            unit = data.get('unit')
            marks = data.get('marks')

            if not question_id:
                return Response({'error': 'Question ID is required'}, status=status.HTTP_400_BAD_REQUEST)

            # Update the question in MongoDB
            update_data = {
                "question_text": question_text,
                "unit": int(unit) if unit else None,
                "marks": int(marks) if marks else None,
                "hash": hashlib.md5(question_text.encode()).hexdigest(),
                "updated_by": str(request.user._id),
                "updated_at": datetime.now()
            }

            result = db["pyq_questions"].update_one(
                {"_id": ObjectId(question_id)},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return Response({'success': True, 'message': 'Question updated successfully'})
            else:
                return Response({'error': 'Question not found or no changes made'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            traceback.print_exc()  # This will show the real error in the console
            return Response({"error": f"Update failed: {str(e)}"}, status=500)

    @action(detail=False, methods=['get'], url_path='questions')
    def get_questions(self, request):
        """Get questions with optional filtering"""
        try:
            # Get query parameters for filtering
            subject_name = request.query_params.get('subject_name')
            subject_code = request.query_params.get('subject_code')
            exam_type = request.query_params.get('exam_type')
            unit = request.query_params.get('unit')
            uploaded_by = request.query_params.get('uploaded_by')

            # Build filter query
            filter_query = {}
            if subject_name:
                filter_query['subject_name'] = {'$regex': subject_name, '$options': 'i'}
            if subject_code:
                filter_query['subject_code'] = subject_code
            if exam_type:
                filter_query['exam_type'] = exam_type
            if unit:
                filter_query['unit'] = int(unit)
            if uploaded_by:
                filter_query['uploaded_by'] = int(uploaded_by)

            # Get questions from MongoDB
            questions = list(db["pyq_questions"].find(filter_query).sort('uploaded_at', -1))
            
            # Convert ObjectId to string for JSON serialization
            for question in questions:
                question['_id'] = str(question['_id'])
                question['isEditing'] = False

            return Response({
                'success': True,
                'questions': questions,
                'count': len(questions)
            })

        except Exception as e:
            return Response({'error': f'Failed to fetch questions: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_question(self, request, pk=None):
        """Delete a specific question"""
        try:
            result = db["pyq_questions"].delete_one({"_id": ObjectId(pk)})
            
            if result.deleted_count > 0:
                return Response({'success': True, 'message': 'Question deleted successfully'})
            else:
                return Response({'error': 'Question not found'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'error': f'Delete failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='upload-history')
    def get_upload_history(self, request):
        """Get upload history for the current user"""
        try:
            # Get unique uploads by user
            pipeline = [
                {"$match": {"uploaded_by": str(request.user._id)}},
                {"$group": {
                    "_id": {
                        "subject_name": "$subject_name",
                        "subject_code": "$subject_code",
                        "exam_type": "$exam_type",
                        "uploaded_at": "$uploaded_at"
                    },
                    "question_count": {"$sum": 1},
                    "filename": {"$first": "$filename"}
                }},
                {"$sort": {"_id.uploaded_at": -1}},
                {"$limit": 20}
            ]
            
            history = list(db["pyq_questions"].aggregate(pipeline))
            
            # Format for frontend
            formatted_history = []
            for item in history:
                formatted_history.append({
                    'id': str(item['_id']['uploaded_at']),
                    'filename': item.get('filename', f"{item['_id']['subject_name']}.pdf"),
                    'date': item['_id']['uploaded_at'].strftime('%Y-%m-%d') if item['_id']['uploaded_at'] else '',
                    'subject_name': item['_id']['subject_name'],
                    'exam_type': item['_id']['exam_type'],
                    'question_count': item['question_count']
                })
            
            return Response({
                'success': True,
                'history': formatted_history
            })

        except Exception as e:
            return Response({'error': f'Failed to fetch history: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def extract_questions_from_pdf(self, file_path, subject_name, subject_code, exam_type, user):
        """Extract questions from PDF using the provided logic"""
        from datetime import datetime
        
        # Load PDF
        doc = fitz.open(file_path)
        full_text = "\n".join([page.get_text() for page in doc])
        doc.close()

        # Extract Metadata
        
        # 1. Academic Year (e.g., SE/TE/BE)
        year_match = re.search(r'(S\.E\.|T\.E\.|B\.E\.)', full_text, re.IGNORECASE)
        academic_year = year_match.group(1).upper().replace('.', '') if year_match else None

        # 2. Department
        dept_match = None
        if year_match:
            text_after_year = full_text.split(year_match.group(1), 1)[1] if len(full_text.split(year_match.group(1))) > 1 else ""
            dept_match = re.search(r'\((.*?)\)', text_after_year)
        department = dept_match.group(1).strip().title() if dept_match else None

        # 3. Subject Code
        subject_code_match = re.search(r'\((\d{6}[A-Z]?)\)', full_text)
        extracted_subject_code = subject_code_match.group(1).strip().replace(" ", "") if subject_code_match else subject_code

        # 4. Subject Name (first ALL CAPS line after department)
        subject_name_match = re.search(r'\n([A-Z][A-Z\s&\-]+)\n', full_text)
        extracted_subject_name = subject_name_match.group(1).strip().title() if subject_name_match else subject_name

        # 5. Full Paper Number (e.g., [6353] - 125)
        papernum_match = re.search(r'\[\d+\]\s*-\s*\d+', full_text)
        papernumber = papernum_match.group(0) if papernum_match else None
        if papernumber:
            papernumber = re.sub(r'[\[\]]', '', papernumber).strip()

        # Define unit mapping
        unit_map = {
            "Q1": 3, "Q2": 3,
            "Q3": 4, "Q4": 4,  
            "Q5": 5, "Q6": 5,
            "Q7": 6, "Q8": 6
        }

        # Extract Questions
        question_section = full_text
        if "Instructions to the candidates:" in full_text:
            question_section = full_text.split("Instructions to the candidates:")[-1]

        # Clean up the text by removing extra whitespace and normalizing
        question_section = re.sub(r'\s+', ' ', question_section).strip()

        # Split by main questions (Q1), Q2), etc.)
        main_questions = re.split(r'(Q\d+\))', question_section)[1:]  # Remove empty first element

        # Clean and Structure Data
        question_list = []
        current_time = datetime.now()

        # Process pairs of (question_number, question_content)
        for i in range(0, len(main_questions), 2):
            if i + 1 < len(main_questions):
                q_main = main_questions[i].strip()  # e.g., "Q1)"
                q_content = main_questions[i + 1].strip()
                
                # Remove the closing parenthesis for mapping
                q_main_clean = q_main.replace(")", "")  # "Q1)" -> "Q1"
                
                # Split by OR to handle alternative questions
                or_sections = re.split(r'\bOR\b', q_content)
                
                for section_idx, section in enumerate(or_sections):
                    section = section.strip()
                    if not section:
                        continue
                        
                    # Find all sub-questions (a), b), c), etc.) in this section
                    sub_questions = re.split(r'([a-z]\))', section)[1:]  # Remove empty first element
                    
                    # Process pairs of (sub_question_letter, sub_question_content)
                    for j in range(0, len(sub_questions), 2):
                        if j + 1 < len(sub_questions):
                            sub_letter = sub_questions[j].strip()  # e.g., "a)"
                            sub_content = sub_questions[j + 1].strip()
                            
                            if not sub_content:
                                continue
                            
                            # Extract marks
                            marks_match = re.search(r'\[(\d+)\]', sub_content)
                            marks = int(marks_match.group(1)) if marks_match else None
                            
                            # Clean the question text by removing marks
                            clean_text = re.sub(r'\[\d+\]', '', sub_content).strip()
                            
                            # Remove any trailing periods or extra whitespace
                            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                            clean_text = clean_text.rstrip('.')
                            
                            if clean_text:  # Only add non-empty questions
                                # Create full question identifier
                                full_question_id = f"{q_main_clean}{sub_letter}"
                                if section_idx > 0:  # If this is from an OR section
                                    full_question_id += f" (Alternative)"
                                
                                question_list.append({
                                    "academic_year": academic_year,
                                    "department": department,
                                    "subject_name": extracted_subject_name,
                                    "subject_code": extracted_subject_code,
                                    "papernumber": papernumber,
                                    "exam_type": exam_type,
                                    "question_id": full_question_id,
                                    "main_question": q_main_clean,
                                    "sub_question": sub_letter.replace(")", ""),
                                    "is_alternative": section_idx > 0,
                                    "question_text": clean_text,
                                    "unit": unit_map.get(q_main_clean, None),
                                    "marks": marks,
                                    "hash": hashlib.md5(clean_text.encode()).hexdigest(),
                                    "uploaded_by": str(user._id),
                                    "uploaded_at": current_time,
                                    "updated_at": current_time,
                                    "filename": file_path.split('/')[-1],
                                    "isEditing": False  # For frontend editing functionality
                                })

        return question_list

    def save_questions_to_db(self, questions):
        """Save questions to MongoDB and return saved questions with IDs"""
        saved_questions = []
        
        for question in questions:
            # Check if the question already exists
            existing_question = db["pyq_questions"].find_one({"hash": question["hash"]})
            
            if not existing_question:
                # Insert the new question
                result = db["pyq_questions"].insert_one(question)
                question["_id"] = str(result.inserted_id)
                saved_questions.append(question)
                print(f"Inserted: {question['question_text']}")
            else:
                # Return existing question with string ID
                existing_question["_id"] = str(existing_question["_id"])
                existing_question["isEditing"] = False
                saved_questions.append(existing_question)
                print(f"Already exists: {existing_question['question_text']}")
        
        return saved_questions
    
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
    
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_paper_pdf(request, paper_id):
    try:
        paper = db["papers"].find_one({"_id": ObjectId(paper_id)})
        if not paper:
            return Response({"error": "Paper not found"}, status=404)

        sections = list(db["sections"].find({"paper_id": ObjectId(paper_id)}).sort("order", 1))
        for section in sections:
            section["questions"] = list(db["questions"].find({"section_id": section["_id"]}))

        html = render_to_string("./papers/pdf_template.html", {
            "paper": paper,
            "sections": sections
        })

        buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=buffer)
        if pisa_status.err:
            return Response({"error": "PDF generation failed"}, status=500)

        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': f'attachment; filename="{paper["title"]}.pdf"'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)
from pymongo import MongoClient
from datetime import datetime, timezone
import traceback
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId
# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DB = os.getenv('MONGODB_DB')

if not MONGODB_URI or not MONGODB_DB:
    raise Exception("Missing MongoDB configuration in environment variables")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]


def insert_paper(data, user_id):
    # Ensure data is a dictionary
    if not isinstance(data, dict):
        raise ValueError("Expected 'data' to be a dictionary, but got: {}".format(type(data)))

    created_at = updated_at = datetime.now(timezone.utc)

    
    paper_doc = {
        "user_id": user_id,
        "title": f"{data['subject_name']} Exam Paper",
        "subject_name": data['subject_name'],
        "department": data['department'],
        "topics": data['topics'],
        "total_marks": data['total_marks'],
        "duration": data['duration'],
        "include_formula": data.get('includeFormula', False),
        "include_diagrams": data.get('includeDiagrams', False),
        "include_answer_key": data.get('includeAnswerKey', True),
        "status": "draft",
        "created_at": created_at,
        "updated_at": updated_at
    }


    paper_id = db['papers'].insert_one(paper_doc).inserted_id
    return paper_id

def insert_section(section_data, paper_id, index):
    created_at = updated_at = datetime.now(timezone.utc)

    section_doc = {
        "paper_id": paper_id,
        "name": section_data['name'],
        "question_type": section_data['questionType'],
        "num_questions": section_data['numQuestions'],
        "marks_per_question": section_data['marksPerQuestion'],
        "instructions": section_data.get('instructions', ''),
        "order": index,
        "created_at": created_at,
        "updated_at": updated_at
    }
    section_id = db['sections'].insert_one(section_doc).inserted_id
    return section_id

def insert_question(question_data, paper_id, section_id):
    created_at = updated_at = datetime.now(timezone.utc)

    question_doc = {
        "paper_id": paper_id,
        "section_id": section_id,
        "text": question_data['text'],
        "question_type": question_data['questionType'],
        "difficulty": question_data['difficulty'],
        "cognitive_level": question_data['cognitiveLevel'],
        "marks": question_data['marks'],
        "options": question_data.get('options'),
        "answer": question_data.get('answer', ''),
        "is_practical": question_data['isPractical'],
        "topic": question_data.get('topic', ''),
        "tags": question_data.get('tags', []),
        "diagram": question_data.get('diagram'),
        "formula_required": question_data.get('formulaRequired', False),
        "created_at": created_at,
        "updated_at": updated_at
    }
    db['questions'].insert_one(question_doc)

def update_paper_status(paper_id):
    updated_at = datetime.now(timezone.utc)
    db['papers'].update_one(
        {'_id': ObjectId(paper_id)},
        {'$set': {'status': 'published', 'updated_at': updated_at}}
    )

def get_paper(paper_id):
    paper = db['papers'].find_one({'_id': ObjectId(paper_id)})
    return paper
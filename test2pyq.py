import fitz  # PyMuPDF
import re
import hashlib
import json


mongodb = "mongodb://localhost:27017/"
db_name = "exam_papers" # database name
collection_name = "questions" # collection name
# === Connect to MongoDB ===
from pymongo import MongoClient
client = MongoClient(mongodb)
db = client[db_name]
collection = db[collection_name]

# === Load PDF ===
doc = fitz.open("adbms 1.pdf")
full_text = "\n".join([page.get_text() for page in doc])

# === Extract Metadata ===

# 1. Academic Year (e.g., SE/TE/BE)
year_match = re.search(r'(S\.E\.|T\.E\.|B\.E\.)', full_text, re.IGNORECASE)
academic_year = year_match.group(1).upper().replace('.', '') if year_match else None

# 2. Department
dept_match = re.search(r'\((.*?)\)', full_text.split(year_match.group(1))[1]) if year_match else None
department = dept_match.group(1).strip().title() if dept_match else None

# 3. Subject Code
subject_code_match = re.search(r'\((\d{6}[A-Z]?)\)', full_text)
subject_code = subject_code_match.group(1).strip().replace(" ", "") if subject_code_match else None


# 4. Subject Name (first ALL CAPS line after department)
subject_name_match = re.search(r'\n([A-Z][A-Z\s&\-]+)\n', full_text)
subject_name = subject_name_match.group(1).strip().title() if subject_name_match else None


# 5. Full Paper Number (e.g., [6353] - 125)
papernum_match = re.search(r'\[\d+\]\s*-\s*\d+', full_text)
papernumber = papernum_match.group(0) if papernum_match else None
if papernumber:
    papernumber = re.sub(r'[\[\]]', '', papernumber).strip()

# === Define unit mapping ===
unit_map = {
    "Q1": 3, "Q2": 3,
    "Q3": 4, "Q4": 4,
    "Q5": 5, "Q6": 5,
    "Q7": 6, "Q8": 6
}

# === Extract Questions ===
question_section = full_text.split("Instructions to the candidates:")[-1]
pattern = r'(Q\d\))\s*([a-z]\))\s*(.*?)(?=Q\d\)|[a-z]\)|\Z)'
matches = re.findall(pattern, question_section, re.DOTALL)

# === Clean and Structure Data ===
question_list = []
for q_main, q_sub, q_text in matches:
    clean_text = re.sub(r'\s+', ' ', q_text).strip()
    marks_match = re.search(r'\[(\d+)\]', clean_text)
    marks = int(marks_match.group(1)) if marks_match else None
    q_main_clean = q_main.strip().replace(")", "")  # Normalize "Q1)" -> "Q1"
    clean_text = re.sub(r'\[\d+\]', '', clean_text).strip()  # Remove [9] etc.

    question_list.append({
        "academic_year": academic_year,
        "department": department,
        "subject_name": subject_name,
        "subject_code": subject_code,
        "papernumber": papernumber,
        "question_text": clean_text,
        "unit": unit_map.get(q_main_clean, None),
        "marks": marks,
        "hash": hashlib.md5(clean_text.encode()).hexdigest()
    })


# === Insert into MongoDB ===
for question in question_list:
    # Check if the question already exists
    existing_question = collection.find_one({"hash": question["hash"]})
    if not existing_question:
        # Insert the new question
        collection.insert_one(question)
        print(f"Inserted: {question['question_text']}")
    else:
        print(f"Already exists: {existing_question['question_text']}")

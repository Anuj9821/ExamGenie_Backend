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

# Clean up the text by removing extra whitespace and normalizing
question_section = re.sub(r'\s+', ' ', question_section).strip()

# Split by main questions (Q1), Q2), etc.)
main_questions = re.split(r'(Q\d+\))', question_section)[1:]  # Remove empty first element

question_list = []

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
                            "subject_name": subject_name,
                            "subject_code": subject_code,
                            "papernumber": papernumber,
                            "question_id": full_question_id,
                            "main_question": q_main_clean,
                            "sub_question": sub_letter.replace(")", ""),
                            "is_alternative": section_idx > 0,
                            "question_text": clean_text,
                            "unit": unit_map.get(q_main_clean, None),
                            "marks": marks,
                            "hash": hashlib.md5(clean_text.encode()).hexdigest()
                        })

# === Insert into MongoDB ===
print(f"Found {len(question_list)} questions:")
print("-" * 50)

for question in question_list:
    # Check if the question already exists
    existing_question = collection.find_one({"hash": question["hash"]})
    if not existing_question:
        # Insert the new question
        collection.insert_one(question)
        print(f"✓ Inserted: {question['question_id']} - {question['question_text'][:80]}{'...' if len(question['question_text']) > 80 else ''}")
    else:
        print(f"⚠ Already exists: {question['question_id']} - {existing_question['question_text'][:80]}{'...' if len(existing_question['question_text']) > 80 else ''}")

print(f"\nTotal questions processed: {len(question_list)}")
print(f"Database: {db_name}")
print(f"Collection: {collection_name}")
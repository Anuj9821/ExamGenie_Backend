from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.timezone import now
from PyPDF2 import PdfReader
<<<<<<< HEAD
from datetime import datetime, timezone
import re
from utils.db_utils import db
from transformers import pipeline, set_seed

# === LOAD GPT-2 PIPELINE ===
generator = pipeline("text-generation", model="gpt2")
set_seed(42)

# === FUNCTION: Extract Units ===
def extract_unit_topics(text):
    # Match all unit headers
    unit_headers = list(re.finditer(r'(Unit\s+[IVXLC]+\s+.+?)\n', text, flags=re.IGNORECASE))

    units = []

    for i, header in enumerate(unit_headers):
        unit_heading = header.group(1).strip()
        unit_match = re.search(r'Unit\s+([IVXLC]+)', unit_heading, re.IGNORECASE)
        unit_number = unit_match.group(1).strip().upper() if unit_match else f"U{i+1}"


        # Start position of this unit
        start_pos = header.end()

        # End position = start of next unit or end of text
        if i + 1 < len(unit_headers):
            end_pos = unit_headers[i + 1].start()
        else:
            # This is the last unit
            end_pos = len(text)

        # Extract content between headers
        unit_body = text[start_pos:end_pos].strip()

        # Remove trailing Mapping line if present
        unit_body = re.sub(r'Mapping of Course Outcomes\s*for\s+Unit\s+[IVXLC]+\s+CO\d+', '', unit_body, flags=re.IGNORECASE).strip()

        # Skip if unit text is empty or heading is a CO line
        if not unit_body.strip():
            continue
        if re.search(r'\bCO\d+\b', unit_heading, re.IGNORECASE):
            continue

        units.append({
            "unit_number": unit_number,
            "heading": unit_heading,
            "topics_text": unit_body
        })


    return units



# === FUNCTION: Split unit text into topics ===
def split_into_topics(unit_text):
    clean_text = re.sub(r'\s+', ' ', unit_text).strip()
    clean_text = re.sub(r'Mapping of Course Outcomes\s*for.*$', '', clean_text, flags=re.IGNORECASE)
    return [topic.strip() for topic in clean_text.split(',') if topic.strip()]


# === FUNCTION: Generate Context using GPT-2 ===
def generate_context_with_gpt2(topic):
    prompt = (
        f"Write a short academic explanation in one paragraph about the topic: '{topic}'. "
        "Explain it in simple and informative language suitable for students."
    )
    try:
        output = generator(prompt, max_length=120, num_return_sequences=1)
        return output[0]["generated_text"].replace(prompt, "").strip()
    except Exception as e:
        return f"Context generation failed: {str(e)}"

# === MAIN API ===
=======
import re
from utils.db_utils import db

>>>>>>> 477e6f2f638857d639482762735e61bc10f003ac
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_syllabus(request):
    file = request.FILES.get("file")
    year = request.POST.get("year")
    department = request.POST.get("department")
<<<<<<< HEAD
    subject_name_input = request.POST.get("subjectName")
    subject_code_input = request.POST.get("subjectCode")
    print("DEBUG: request.POST =", dict(request.POST))
    print("DEBUG: request.FILES =", request.FILES)

=======
>>>>>>> 477e6f2f638857d639482762735e61bc10f003ac

    if not file or not year or not department:
        return Response({"error": "File, year and department are required."}, status=400)

    try:
        pdf_reader = PdfReader(file)
        full_text = "\n".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
    except Exception as e:
        return Response({"error": f"PDF extraction failed: {str(e)}"}, status=500)

<<<<<<< HEAD
=======
    # Split by subject code pattern (e.g., 414441)
>>>>>>> 477e6f2f638857d639482762735e61bc10f003ac
    subject_blocks = re.split(r'\n(414\d{3})', full_text)
    subject_codes = re.findall(r'414\d{3}', full_text)

    if not subject_codes or len(subject_blocks) < 2:
        return Response({"error": "No valid subject codes found in the PDF."}, status=400)

    inserted_subjects = []

<<<<<<< HEAD
    for i in range(1, len(subject_blocks), 2):
        subject_code_parsed = subject_blocks[i]
        content = subject_blocks[i + 1] if i + 1 < len(subject_blocks) else ""
        subject_lines = content.strip().splitlines()

        # Use request data if provided, otherwise parse from PDF
        subject_name = subject_name_input or (subject_lines[0].strip() if subject_lines else "Unknown Subject")
        subject_code = subject_code_input or subject_code_parsed
=======
    # Parse and store each subject block
    for i in range(1, len(subject_blocks), 2):
        subject_code = subject_blocks[i]
        content = subject_blocks[i + 1] if i + 1 < len(subject_blocks) else ""

        # Get subject name from first line of the block
        subject_lines = content.strip().splitlines()
        subject_name = subject_lines[0].strip() if subject_lines else "Unknown Subject"
>>>>>>> 477e6f2f638857d639482762735e61bc10f003ac

        db["syllabus_subjects"].insert_one({
            "subject_code": subject_code,
            "subject_name": subject_name,
            "year": year,
            "department": department,
            "syllabus_text": content.strip(),
            "upload_date": now(),
            "filename": file.name
        })

<<<<<<< HEAD
        # === Unit Extraction and Enrichment ===
        units = extract_unit_topics(content)
        for unit in units:
            topics = split_into_topics(unit["topics_text"])
            enriched_topics = []

            for topic_text in topics:
                enriched_topics.append({
                    "topic": topic_text,
                    "context": ""  # Blank context
                })


            db["syllabus_units"].insert_one({
                "subject_name": subject_name,
                "subject_code": subject_code,
                "unit_number": unit["unit_number"],
                "unit_heading": unit["heading"],
                "unit_text": unit["topics_text"],
                "topics": enriched_topics,
                "department": department,
                "year": year,
                "uploaded_at": datetime.now(timezone.utc)
            })

        inserted_subjects.append(f"{subject_code} - {subject_name}")

    return Response({
        "message": f"{len(inserted_subjects)} subjects saved and enriched successfully.",
=======
        inserted_subjects.append(f"{subject_code} - {subject_name}")

    return Response({
        "message": f"{len(inserted_subjects)} subjects saved successfully.",
>>>>>>> 477e6f2f638857d639482762735e61bc10f003ac
        "saved_subjects": inserted_subjects
    })

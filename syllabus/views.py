from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.timezone import now
from PyPDF2 import PdfReader
import re
from utils.db_utils import db

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_syllabus(request):
    file = request.FILES.get("file")
    year = request.POST.get("year")
    department = request.POST.get("department")

    if not file or not year or not department:
        return Response({"error": "File, year and department are required."}, status=400)

    try:
        pdf_reader = PdfReader(file)
        full_text = "\n".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
    except Exception as e:
        return Response({"error": f"PDF extraction failed: {str(e)}"}, status=500)

    # Split by subject code pattern (e.g., 414441)
    subject_blocks = re.split(r'\n(414\d{3})', full_text)
    subject_codes = re.findall(r'414\d{3}', full_text)

    if not subject_codes or len(subject_blocks) < 2:
        return Response({"error": "No valid subject codes found in the PDF."}, status=400)

    inserted_subjects = []

    # Parse and store each subject block
    for i in range(1, len(subject_blocks), 2):
        subject_code = subject_blocks[i]
        content = subject_blocks[i + 1] if i + 1 < len(subject_blocks) else ""

        # Get subject name from first line of the block
        subject_lines = content.strip().splitlines()
        subject_name = subject_lines[0].strip() if subject_lines else "Unknown Subject"

        db["syllabus_subjects"].insert_one({
            "subject_code": subject_code,
            "subject_name": subject_name,
            "year": year,
            "department": department,
            "syllabus_text": content.strip(),
            "upload_date": now(),
            "filename": file.name
        })

        inserted_subjects.append(f"{subject_code} - {subject_name}")

    return Response({
        "message": f"{len(inserted_subjects)} subjects saved successfully.",
        "saved_subjects": inserted_subjects
    })

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from bson import ObjectId
import traceback

from utils.db_utils import db

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_questions(request):
    try:
        questions = request.data.get("questions", [])
        if not questions:
            return Response({"error": "No questions provided"}, status=400)

        updated_count = 0
        for q in questions:
            question_id = q.get("id")
            if not question_id:
                continue

            update_result = db["questions"].update_one(
                {"_id": ObjectId(question_id)},
                {"$set": {
                    "text": q.get("text"),
                    "marks": q.get("marks"),
                    "difficulty": q.get("difficulty"),
                    "cognitive_level": q.get("cognitive_level"),
                    "options": q.get("options"),
                    "answer": q.get("answer"),
                    "is_practical": q.get("is_practical"),
                    "formula_required": q.get("formula_required"),
                    "diagram": q.get("diagram"),
                    "topic": q.get("topic"),
                    "tags": q.get("tags", []),
                }}
            )

            if update_result.modified_count > 0:
                updated_count += 1

        return Response({
            "message": f"{updated_count} question(s) updated successfully"
        }, status=200)

    except Exception as e:
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)

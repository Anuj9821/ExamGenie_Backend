import re
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


def normalize(text):
    """Lowercase, strip, remove punctuation."""
    return re.sub(r"[^\w\s]", "", text.strip().lower())

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_pyq_overlap(request):
    try:
        # ── 0️⃣  Identify the user
        user_id = str(getattr(request.user, "id", None) or getattr(request.user, "_id", ""))
        print(f"User ID: {user_id}")

        # ── 1️⃣  Get latest paper for this user
        latest_paper = db["papers"].find_one(
            {"user_id": user_id},
            sort=[("created_at", -1)]
        )
        print(f"Latest Paper: {latest_paper}")

        if not latest_paper:
            return Response({"detail": "No generated paper found for this user."}, status=404)

        paper_id = latest_paper["_id"]
        print(f"Latest paper ID: {paper_id}")

        # ── 2️⃣  Fetch all questions linked to this paper
        generated_cursor = db["questions"].find({"paper_id": paper_id}, {"text": 1, "_id": 0})
        generated_list = list(generated_cursor)
        print(f"Total generated question docs: {len(generated_list)}")
        print("Generated questions (raw):")
        for doc in generated_list:
            print(doc)

        # Normalize generated questions
        gen_set = {
            normalize(doc["text"])
            for doc in generated_list
            if doc.get("text")
        }
        print(f"\nNormalized Generated Questions ({len(gen_set)}):")
        for q in list(gen_set)[:5]:  # show sample
            print(q)

        # ── 3️⃣  Get all PYQ questions
        pyq_cursor = db["pyq_questions"].find({}, {"question_text": 1, "_id": 0})
        pyq_list = list(pyq_cursor)
        print(f"\nTotal PYQ question docs: {len(pyq_list)}")
        print("PYQ questions (raw):")
        for doc in pyq_list:
            print(doc)

        # Normalize PYQ questions
        pyq_set = {
            normalize(doc["question_text"])
            for doc in pyq_list
            if doc.get("question_text")
        }
        print(f"\nNormalized PYQ Questions ({len(pyq_set)}):")
        for q in list(pyq_set)[:5]:  # show sample
            print(q)

        # ── 4️⃣  Calculate overlap
        repeated = list(gen_set & pyq_set)
        percent = round(len(repeated) / len(gen_set) * 100, 2) if gen_set else 0

        print(f"\nRepeated Questions ({len(repeated)}):")
        for q in repeated:
            print(q)

        print(f"\nRepeated percentage: {percent}%")

        return Response({
            "matched_questions": repeated,
            "repeated_percent": percent,
            "total_generated": len(gen_set),
            "total_matched": len(repeated)
        }, status=200)

    except Exception as e:
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)
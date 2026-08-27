import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://learn-adapt-grow.preview.emergentagent.com").rstrip("/")


def test_login_and_subject_library():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "taylor.reed@example.com", "password": "learning123"}, timeout=20)
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "taylor.reed@example.com"
    subjects = requests.get(f"{BASE_URL}/api/subjects", timeout=20)
    assert subjects.status_code == 200
    assert any(s["id"] == "math" for s in subjects.json())


def test_register_duplicate_is_rejected():
    r = requests.post(f"{BASE_URL}/api/auth/register", json={"name": "Test Duplicate", "email": "taylor.reed@example.com", "password": "learning123", "grade": "Grade 8"}, timeout=20)
    assert r.status_code == 400
    assert "already exists" in r.json()["detail"]


def test_lesson_quiz_and_both_answer_outcomes():
    lesson = requests.get(f"{BASE_URL}/api/lessons/math", timeout=20)
    assert lesson.status_code == 200
    assert lesson.json()["title"] == "Linear equations"
    quiz = requests.post(f"{BASE_URL}/api/quiz", json={"subject": "Mathematics", "topic": lesson.json()["title"], "grade": "Grade 8", "history": []}, timeout=20)
    assert quiz.status_code == 200
    q = quiz.json()
    assert q["correct"] in q["options"]
    for answer, expected in [(q["correct"], True), ("not-an-option", False)]:
        result = requests.post(f"{BASE_URL}/api/explain", json={"subject": "Mathematics", "question": q["question"], "answer": answer, "correct_answer": q["correct"], "grade": "Grade 8"}, timeout=45)
        assert result.status_code == 200
        assert result.json()["correct"] is expected
        assert result.json()["explanation"]


def test_google_demo_login():
    r = requests.post(f"{BASE_URL}/api/auth/google", timeout=20)
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "alex@demo.synapselearn.com"


def test_quiz_has_five_questions_for_math_and_non_math():
    for subject in ("Mathematics", "Science"):
        r = requests.post(f"{BASE_URL}/api/quiz", json={"subject": subject, "topic": "Core concepts", "grade": "Grade 8", "history": []}, timeout=20)
        assert r.status_code == 200
        assert len(r.json()["questions"]) == 5
        assert all(q["explanation"] for q in r.json()["questions"])


def test_history_review_queue_and_progress_insights():
    email = "TEST_history_taylor@example.com"
    payload = {"email": email, "kind": "quiz", "subject": "Mathematics", "topic": "Linear equations", "correct": False, "answer": "3"}
    saved = requests.post(f"{BASE_URL}/api/history", json=payload, timeout=20)
    assert saved.status_code == 200 and saved.json()["saved"] is True
    queue = requests.get(f"{BASE_URL}/api/review-queue/{email}", timeout=20)
    assert queue.status_code == 200 and queue.json()["items"]
    insights = requests.get(f"{BASE_URL}/api/progress-insights/{email}", timeout=20)
    assert insights.status_code == 200 and insights.json()["insights"][0]["score"] == 0
def test_ai_status_endpoint(client):
    """Test the AI status endpoint returns connectivity status."""
    response = client.get("/ai/status")
    assert response.status_code == 200
    data = response.json()
    assert "ollama_available" in data
    assert "configured_model" in data
    assert "status" in data


def test_ai_query_count_grounding(client):
    """Test AI query 'How many students are there?' with grounded records."""
    # Seed 2 students
    client.post("/students", json={
        "name": "Student A",
        "date_of_birth": "2003-01-01",
        "email": "a@school.com",
        "course": "Mathematics"
    })
    client.post("/students", json={
        "name": "Student B",
        "date_of_birth": "2004-02-02",
        "email": "b@school.com",
        "course": "Physics"
    })

    response = client.post("/students/ask", json={
        "question": "How many students are there?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["grounded_records_count"] == 2
    assert "2 student record(s)" in data["answer"]
    assert data["question"] == "How many students are there?"


def test_ai_query_born_after_year(client):
    """Test AI query 'List students born after 2005' filtering grounded records."""
    client.post("/students", json={
        "name": "Elder Student",
        "date_of_birth": "2002-05-10",
        "email": "elder@school.com"
    })
    client.post("/students", json={
        "name": "Younger Student",
        "date_of_birth": "2006-08-15",
        "email": "young@school.com"
    })

    response = client.post("/students/ask", json={
        "question": "List students born after 2005"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Younger Student" in data["answer"]
    assert "Elder Student" not in data["answer"]


def test_ai_query_security_no_sql_injection(client):
    """
    Test that malicious SQL strings sent to the natural language interface
    do not execute or alter the database.
    """
    client.post("/students", json={
        "name": "Target Student",
        "date_of_birth": "2001-01-01",
        "email": "target@school.com"
    })

    # Malicious SQL injection attempt
    malicious_query = "'; DROP TABLE students; --"
    response = client.post("/students/ask", json={"question": malicious_query})
    assert response.status_code == 200

    # Ensure the table and data remain completely intact
    students_res = client.get("/students")
    assert students_res.status_code == 200
    assert len(students_res.json()) == 1
    assert students_res.json()[0]["email"] == "target@school.com"

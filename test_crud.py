from datetime import date, timedelta


def test_root_endpoint(client):
    """Test API root status and navigation endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "endpoints" in data
    assert data["endpoints"]["create_student"] == "POST /students"


def test_health_check_endpoint(client):
    """Test health check verifying SQLite connectivity."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_create_student_success(client):
    """Test successful student creation with valid payload."""
    payload = {
        "name": "Jane Doe",
        "date_of_birth": "2003-05-10",
        "email": "jane.doe@example.com",
        "phone": "+1-555-0101",
        "course": "Computer Science",
        "address": "100 Innovation Blvd",
        "enrollment_date": "2023-09-01"
    }
    response = client.post("/students", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["student_id"] == 1
    assert data["name"] == "Jane Doe"
    assert data["email"] == "jane.doe@example.com"
    assert data["course"] == "Computer Science"
    assert "created_at" in data
    assert "updated_at" in data


def test_create_student_duplicate_email(client):
    """Test that creating a student with an existing email returns 409 Conflict."""
    payload = {
        "name": "First User",
        "date_of_birth": "2002-01-01",
        "email": "unique@example.com",
        "course": "Physics"
    }
    res1 = client.post("/students", json=payload)
    assert res1.status_code == 201

    payload_duplicate = {
        "name": "Second User",
        "date_of_birth": "2003-02-02",
        "email": "unique@example.com",
        "course": "Chemistry"
    }
    res2 = client.post("/students", json=payload_duplicate)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_create_student_invalid_dob(client):
    """Test that a future date of birth fails validation (422)."""
    future_date = (date.today() + timedelta(days=5)).isoformat()
    payload = {
        "name": "Time Traveler",
        "date_of_birth": future_date,
        "email": "timetraveler@example.com"
    }
    response = client.post("/students", json=payload)
    assert response.status_code == 422


def test_create_student_invalid_email(client):
    """Test that an invalid email fails validation (422)."""
    payload = {
        "name": "Bad Email",
        "date_of_birth": "2000-01-01",
        "email": "not-an-email"
    }
    response = client.post("/students", json=payload)
    assert response.status_code == 422


def test_create_student_empty_name(client):
    """Test that an empty or whitespace name fails validation (422)."""
    payload = {
        "name": "   ",
        "date_of_birth": "2000-01-01",
        "email": "valid@example.com"
    }
    response = client.post("/students", json=payload)
    assert response.status_code == 422


def test_get_student_by_id(client):
    """Test retrieving a single student by student_id."""
    # Create a student
    create_res = client.post("/students", json={
        "name": "Bob Marley",
        "date_of_birth": "2001-02-06",
        "email": "bob@example.com",
        "course": "Music Theory"
    })
    student_id = create_res.json()["student_id"]

    # Retrieve by ID
    get_res = client.get(f"/students/{student_id}")
    assert get_res.status_code == 200
    assert get_res.json()["student_id"] == student_id
    assert get_res.json()["name"] == "Bob Marley"


def test_get_nonexistent_student(client):
    """Test retrieving a non-existent student ID returns 404."""
    response = client.get("/students/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_list_and_filter_students(client):
    """Test listing students with course filtering, search, and pagination."""
    # Insert multiple students
    students_data = [
        {"name": "Alice Wonderland", "date_of_birth": "2004-03-10", "email": "alice@wonder.com", "course": "Computer Science"},
        {"name": "Bob Builder", "date_of_birth": "2006-07-15", "email": "bob@build.com", "course": "Civil Engineering"},
        {"name": "Charlie Data", "date_of_birth": "2007-09-20", "email": "charlie@data.com", "course": "Computer Science"},
    ]
    for s in students_data:
        client.post("/students", json=s)

    # 1. List all
    res_all = client.get("/students")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 3
    assert res_all.headers["X-Total-Count"] == "3"

    # 2. Filter by course
    res_course = client.get("/students?course=Computer Science")
    assert res_course.status_code == 200
    assert len(res_course.json()) == 2

    # 3. Filter by search query
    res_search = client.get("/students?search=Builder")
    assert res_search.status_code == 200
    assert len(res_search.json()) == 1
    assert res_search.json()[0]["name"] == "Bob Builder"

    # 4. Filter by dob_after
    res_dob = client.get("/students?dob_after=2005-01-01")
    assert res_dob.status_code == 200
    assert len(res_dob.json()) == 2

    # 5. Pagination: limit=1, skip=1
    res_page = client.get("/students?skip=1&limit=1")
    assert res_page.status_code == 200
    assert len(res_page.json()) == 1


def test_update_student_put(client):
    """Test updating student details with PUT."""
    create_res = client.post("/students", json={
        "name": "Old Name",
        "date_of_birth": "2000-01-01",
        "email": "old@example.com",
        "course": "Art"
    })
    student_id = create_res.json()["student_id"]

    update_payload = {
        "name": "New Name",
        "course": "Design"
    }
    update_res = client.put(f"/students/{student_id}", json=update_payload)
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["name"] == "New Name"
    assert data["course"] == "Design"
    assert data["email"] == "old@example.com"  # preserved


def test_patch_student(client):
    """Test partial update with PATCH."""
    create_res = client.post("/students", json={
        "name": "Patch User",
        "date_of_birth": "2001-01-01",
        "email": "patch@example.com",
        "phone": "12345"
    })
    student_id = create_res.json()["student_id"]

    patch_res = client.patch(f"/students/{student_id}", json={"phone": "99999"})
    assert patch_res.status_code == 200
    assert patch_res.json()["phone"] == "99999"
    assert patch_res.json()["name"] == "Patch User"


def test_delete_student(client):
    """Test deleting an existing student."""
    create_res = client.post("/students", json={
        "name": "To Delete",
        "date_of_birth": "2000-01-01",
        "email": "todelete@example.com"
    })
    student_id = create_res.json()["student_id"]

    # Delete
    del_res = client.delete(f"/students/{student_id}")
    assert del_res.status_code == 200
    assert "successfully deleted" in del_res.json()["message"]

    # Verify not found
    get_res = client.get(f"/students/{student_id}")
    assert get_res.status_code == 404


def test_delete_nonexistent_student(client):
    """Test deleting non-existent student returns 404."""
    del_res = client.delete("/students/8888")
    assert del_res.status_code == 404

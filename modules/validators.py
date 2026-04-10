import re
from datetime import datetime
from modules.database_io import get_connection, get_one

MIN_YEAR = 2000  # Earliest valid enrollment year
MIN_YEAR_LEVEL = 1
MAX_YEAR_LEVEL = 5
ALLOWED_GENDERS = ("Male", "Female", "Other")
ROMAN_NUMERAL_RE = re.compile(
    r"^(?=[MDCLXVI]+$)M{0,4}(CM|CD|D?C{0,3})"
    r"(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$"
)


# ── Helpers ────────────────────────────────────────────────────────────────

def is_blank(value):
    return not str(value).strip()


def _normalize_spaces(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize_name(value):
    text = _normalize_spaces(value)
    if not text:
        return ""
    return " ".join(part[:1].upper() + part[1:] for part in text.split(" "))


def normalize_student_data(student_data):
    course_value = student_data.get("course", student_data.get("program_code", ""))
    return {
        "id": _normalize_spaces(student_data.get("id", "")),
        "firstname": normalize_name(student_data.get("firstname", "")),
        "lastname": normalize_name(student_data.get("lastname", "")),
        "course": _normalize_spaces(course_value),
        "year": _normalize_spaces(student_data.get("year", "")),
        "gender": _normalize_spaces(student_data.get("gender", "")).title(),
    }


def normalize_program_data(program_data):
    college_value = program_data.get("college", program_data.get("college_code", ""))
    return {
        "code": _normalize_spaces(program_data.get("code", "")),
        "name": _normalize_spaces(program_data.get("name", "")),
        "college": _normalize_spaces(college_value),
    }


def normalize_college_data(college_data):
    return {
        "code": _normalize_spaces(college_data.get("code", "")),
        "name": _normalize_spaces(college_data.get("name", "")),
    }

def _name_invalid(value):
    """Returns True if a name contains characters outside what is allowed.
    Permits: alphabetic words, spaces, Roman numerals, and common punctuation
    such as hyphens, apostrophes, commas, and periods.
    Covers names like Juan Dela Cruz II, Maria IV, O'Brien, and Mary-Jane.
    """
    text = str(value).strip()
    if not text:
        return True

    if re.search(r"\d", text):
        return True

    return not re.fullmatch(r"[A-Za-z\s\-\',.]+", text)

def id_already_exists(id_number):
    return get_one("students", id_number) is not None


def student_duplicate_exists(firstname, lastname, course, year, exclude_id=None):
    conn = get_connection()
    try:
        sql = (
            "SELECT id FROM students "
            "WHERE firstname = ? AND lastname = ? AND course = ? AND year = ?"
        )
        params = [firstname, lastname, course, int(year)]
        if exclude_id:
            sql += " AND id != ?"
            params.append(exclude_id)

        row = conn.execute(sql, params).fetchone()
        return row is not None
    finally:
        conn.close()

def program_exists(program_code):
    return get_one("programs", program_code) is not None

def college_exists(college_code):
    return get_one("colleges", college_code) is not None

def program_exists_by_code(code):
    return get_one("programs", code) is not None

def college_exists_by_code(code):
    return get_one("colleges", code) is not None


# ── Student Validator ──────────────────────────────────────────────────────

def validate_student(student_data, skip_id_check=False, skip_duplicate_profile_check=False):
    student_data = normalize_student_data(student_data)
    current_year = datetime.now().year

    sid = student_data["id"]
    firstname = student_data["firstname"]
    lastname = student_data["lastname"]
    program = student_data["course"]
    year = student_data["year"]
    gender = student_data["gender"]

    # 1. ID format: YYYY-NNNN
    if not re.match(r'^\d{4}-\d{4}$', sid):
        return False, "ID must be in YYYY-NNNN format (e.g. 2024-0001)."

    # 2. ID year must be realistic; sequence must not be 0000
    id_year = int(sid.split('-')[0])
    if id_year < MIN_YEAR or id_year > current_year:
        return False, f"ID year must be between {MIN_YEAR} and {current_year}."
    if sid.split('-')[1] == '0000':
        return False, "ID sequence cannot be 0000."

    # 3. First name checks
    if is_blank(firstname):
        return False, "First name cannot be empty."
    if len(firstname) < 2:
        return False, "First name must be at least 2 characters."
    if len(firstname) > 64:
        return False, "First name must be under 64 characters."
    if _name_invalid(firstname):
        return False, "First name can only contain letters, spaces, Roman numerals, hyphens, apostrophes, commas, and periods."

    # 4. Last name checks
    if is_blank(lastname):
        return False, "Last name cannot be empty."
    if len(lastname) < 2:
        return False, "Last name must be at least 2 characters."
    if len(lastname) > 64:
        return False, "Last name must be under 64 characters."
    if _name_invalid(lastname):
        return False, "Last name can only contain letters, spaces, Roman numerals, hyphens, apostrophes, commas, and periods."

    # 5. Year level
    if is_blank(year):
        return False, "Year level cannot be empty."
    try:
        year_int = int(year)
        if not (MIN_YEAR_LEVEL <= year_int <= MAX_YEAR_LEVEL):
            return False, f"Year level must be between {MIN_YEAR_LEVEL} and {MAX_YEAR_LEVEL}."
    except ValueError:
        return False, "Year level must be a number."

    # 6. Gender
    if gender not in ALLOWED_GENDERS:
        return False, "Gender must be Male, Female, or Other."

    # 7. Program code exists
    if is_blank(program):
        return False, "Program code cannot be empty."
    if not program_exists(program):
        return False, f"Program code '{program}' does not exist."

    # 8. Program is not unassigned
    if program.lower() == "unassigned":
        return False, "Please select a valid program."

    # 9. Duplicate ID check
    if not skip_id_check:
        if id_already_exists(sid):
            return False, f"ID '{sid}' already exists."

    # 10. Duplicate student profile check
    if not skip_duplicate_profile_check:
        exclude_id = sid if skip_id_check else None
        if student_duplicate_exists(firstname, lastname, program, year_int, exclude_id=exclude_id):
            return False, "A student with the same name, program, and year already exists."

    return True, "Valid."


# ── Program Validator ──────────────────────────────────────────────────────

def validate_program(program_data, is_edit=False):
    program_data = normalize_program_data(program_data)
    code = program_data["code"]
    name = program_data["name"]
    college = program_data["college"]

    # 1. Code empty
    if is_blank(code):
        return False, "Program code cannot be empty."

    # 2. Code length
    if len(code) > 32:
        return False, "Program code must be under 32 characters."

    # 3. Code format — only letters, numbers, hyphens, spaces
    if not re.match(r'^[a-zA-Z0-9\s\-]+$', code):
        return False, "Program code can only contain letters, numbers, hyphens, and spaces."

    # 4. Name empty
    if is_blank(name):
        return False, "Program name cannot be empty."

    # 5. Name length
    if len(name) < 5:
        return False, "Program name must be at least 5 characters."
    if len(name) > 128:
        return False, "Program name must be under 128 characters."

    # 6. Name must not be numbers only
    if re.match(r'^\d+$', name):
        return False, "Program name cannot be numbers only."

    # 7. College must exist
    if is_blank(college) or college.lower() == "unassigned":
        return False, "Please select a valid college."
    if not college_exists(college):
        return False, f"College '{college}' does not exist."

    # 8. Duplicate code check (skip for edits)
    if not is_edit:
        if program_exists_by_code(code):
            return False, f"Program code '{code}' already exists."

    return True, "Valid."


# ── College Validator ──────────────────────────────────────────────────────

def validate_college(college_data, is_edit=False):
    college_data = normalize_college_data(college_data)
    code = college_data["code"]
    name = college_data["name"]

    # 1. Code empty
    if is_blank(code):
        return False, "College code cannot be empty."

    # 2. Code length
    if len(code) < 2:
        return False, "College code must be at least 2 characters."
    if len(code) > 16:
        return False, "College code must be under 16 characters."

    # 3. Code format — letters only
    if not re.match(r'^[a-zA-Z]+$', code):
        return False, "College code can only contain letters (no spaces or symbols)."

    # 4. Name empty
    if is_blank(name):
        return False, "College name cannot be empty."

    # 5. Name length
    if len(name) < 5:
        return False, "College name must be at least 5 characters."
    if len(name) > 128:
        return False, "College name must be under 128 characters."

    # 6. Name must not be numbers only
    if re.match(r'^\d+$', name):
        return False, "College name cannot be numbers only."

    # 7. Duplicate code check (skip for edits)
    if not is_edit:
        if college_exists_by_code(code):
            return False, f"College code '{code}' already exists."

    return True, "Valid."
    
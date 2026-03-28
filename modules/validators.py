import re
from datetime import datetime
from modules.database_io import get_one

MIN_YEAR = 2000  # Earliest valid enrollment year


# ── Helpers ────────────────────────────────────────────────────────────────

def is_blank(value):
    return not str(value).strip()

def _name_invalid(value):
    """Returns True if a name contains characters outside what is allowed.
    Permits: letters, spaces, hyphens, apostrophes, periods.
    Covers names like O'Brien, De La Cruz, Mary-Jane, Jr.
    """
    return not re.match(r"^[a-zA-Z\s\-\.']+$", str(value).strip())

def id_already_exists(id_number):
    return get_one("students", id_number) is not None

def program_exists(program_code):
    return get_one("programs", program_code) is not None

def college_exists(college_code):
    return get_one("colleges", college_code) is not None

def program_code_exists(code):
    return get_one("programs", code) is not None

def college_code_exists(code):
    return get_one("colleges", code) is not None


# ── Student Validator ──────────────────────────────────────────────────────

def validate_student(student_data, skip_id_check=False):
    current_year = datetime.now().year

    sid       = str(student_data.get('id', '')).strip()
    firstname = str(student_data.get('firstname', '')).strip()
    lastname  = str(student_data.get('lastname', '')).strip()
    program   = str(student_data.get('program_code', '')).strip()
    year      = str(student_data.get('year', '')).strip()
    gender    = str(student_data.get('gender', '')).strip()

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
        return False, "First name can only contain letters, spaces, hyphens, apostrophes, or periods."

    # 4. Last name checks
    if is_blank(lastname):
        return False, "Last name cannot be empty."
    if len(lastname) < 2:
        return False, "Last name must be at least 2 characters."
    if len(lastname) > 64:
        return False, "Last name must be under 64 characters."
    if _name_invalid(lastname):
        return False, "Last name can only contain letters, spaces, hyphens, apostrophes, or periods."

    # 5. Year level
    if is_blank(year):
        return False, "Year level cannot be empty."
    try:
        year_int = int(year)
        if not (1 <= year_int <= 4):
            return False, "Year level must be between 1 and 4."
    except ValueError:
        return False, "Year level must be a number."

    # 6. Gender
    if gender not in ("Male", "Female", "Other"):
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

    return True, "Valid."


# ── Program Validator ──────────────────────────────────────────────────────

def validate_program(program_data, is_edit=False):
    code    = str(program_data.get('code', '')).strip()
    name    = str(program_data.get('name', '')).strip()
    college = str(program_data.get('college_code', '')).strip()

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
        if program_code_exists(code):
            return False, f"Program code '{code}' already exists."

    return True, "Valid."


# ── College Validator ──────────────────────────────────────────────────────

def validate_college(college_data, is_edit=False):
    code = str(college_data.get('code', '')).strip()
    name = str(college_data.get('name', '')).strip()

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
        if college_code_exists(code):
            return False, f"College code '{code}' already exists."

    return True, "Valid."
    
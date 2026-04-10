import sqlite3
import csv
import os
import shutil
import re
import unicodedata
from datetime import datetime

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(MODULE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "sis_database.db")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

ALLOWED_COLUMNS = {
    "students": {"id", "firstname", "lastname", "course", "year", "gender", "college"},
    "programs": {"code", "name", "college"},
    "colleges": {"code", "name"},
}

TABLE_COLUMNS = {
    "students": ["id", "firstname", "lastname", "course", "year", "gender"],
    "programs": ["code", "name", "college"],
    "colleges": ["code", "name"],
}


def _normalize_csv_headers(headers):
    normalized = set()
    for header in headers:
        key = str(header).strip().lower()
        if not key:
            continue
        if key == "program_code":
            key = "course"
        elif key == "college_code":
            key = "college"
        normalized.add(key)
    return normalized


def detect_csv_table(filename):
    with open(filename, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        headers = _normalize_csv_headers(reader.fieldnames or [])

    if not headers:
        raise ValueError("CSV file has no headers.")

    candidates = []
    for table_name, columns in TABLE_COLUMNS.items():
        required = {column.lower() for column in columns}
        if required.issubset(headers):
            candidates.append(table_name)

    if not candidates:
        raise ValueError(
            "Could not detect CSV table type from headers. "
            "Expected students, programs, or colleges format."
        )

    if len(candidates) > 1:
        # Pick the most specific match (most required columns) to avoid ambiguity.
        candidates.sort(key=lambda table: len(TABLE_COLUMNS[table]), reverse=True)
        top_columns = len(TABLE_COLUMNS[candidates[0]])
        top_candidates = [table for table in candidates if len(TABLE_COLUMNS[table]) == top_columns]
        if len(top_candidates) > 1:
            raise ValueError(
                f"Ambiguous CSV headers match multiple tables: {', '.join(sorted(top_candidates))}"
            )
        return top_candidates[0]

    return candidates[0]

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _validate_table(table_name):
    if table_name not in ALLOWED_COLUMNS:
        raise ValueError(f"Invalid table name: {table_name}")


def _build_where_clause(table_name, search_column, search_query):
    if not search_column or not search_query:
        return "", []

    query_param = f"%{search_query}%"

    if table_name == "students" and search_column == "college":
        return (
            " WHERE EXISTS ("
            "SELECT 1 FROM programs p "
            "WHERE p.code = students.course "
            "AND p.college LIKE ?"
            ")",
            [query_param],
        )

    if search_column not in ALLOWED_COLUMNS[table_name]:
        raise ValueError(f"Invalid search column '{search_column}' for table '{table_name}'")

    return f" WHERE {search_column} LIKE ?", [query_param]


def _build_order_clause(table_name, order_by, reverse):
    if not order_by:
        return ""

    if table_name == "students" and order_by == "college":
        order_expr = "(SELECT p.college FROM programs p WHERE p.code = students.course)"
    else:
        if order_by not in ALLOWED_COLUMNS[table_name]:
            raise ValueError(f"Invalid order column '{order_by}' for table '{table_name}'")
        order_expr = order_by

    return f" ORDER BY {order_expr} {'DESC' if reverse else 'ASC'}"

def migration():
    """"read existing csv in case no contents in the database """
    conn = get_connection()
    c = conn.cursor()

        # --- Colleges first (top of hierarchy) ---
    colleges_path = os.path.join(DATA_DIR, "colleges.csv")
    with open(colleges_path, newline="") as f:
        for row in csv.DictReader(f):
            c.execute(
                "INSERT OR IGNORE INTO colleges (code, name) VALUES (?, ?)",
                (row["code"], row["name"])
            )
    print(f"Colleges migrated.")

    # --- Programs second (depends on colleges) ---
    programs_path = os.path.join(DATA_DIR, "programs.csv")
    with open(programs_path, newline="") as f:
        for row in csv.DictReader(f):
            c.execute(
                "INSERT OR IGNORE INTO programs (code, name, college) VALUES (?, ?, ?)",
                (
                    row["code"],
                    row["name"],
                    row["college"],
                )
            )
    print(f"Programs migrated.")

    # --- Students last (depends on programs) ---
    students_path = os.path.join(DATA_DIR, "students.csv")
    with open(students_path, newline="") as f:
        for row in csv.DictReader(f):
            c.execute(
                 "INSERT OR IGNORE INTO students (id, firstname, lastname, course, year, gender) VALUES (?, ?, ?, ?, ?, ?)",
                (row["id"], row["firstname"], row["lastname"],
                row["course"], row["year"], row["gender"])
            )
    print(f"Students migrated.")

    conn.commit()

    # Print summary
    print("\n--- Migration Summary ---")
    for table in ["colleges", "programs", "students"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} records")

    conn.close()
    
def db_initialization():
    conn = get_connection()
    c =conn.cursor()

    # 1. Top Level: Colleges
    c.execute(""" CREATE TABLE IF NOT EXISTS colleges(
              code TEXT PRIMARY KEY CHECK (code IN ('CCS','CED','CHS','COE','CEBA','CASS','CSM')),
              name TEXT NOT NULL,
              UNIQUE(name)
              )""")
    
    # 2. Mid Level: Programs (References Colleges)
    c.execute(""" CREATE TABLE IF NOT EXISTS programs(
              code TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              college TEXT,
              FOREIGN KEY (college) REFERENCES colleges(code)
              ON DELETE SET NULL,
              UNIQUE(name,college)
              )""")

    # 3. Bottom Level: Students (References Programs)
    c.execute(""" CREATE TABLE IF NOT EXISTS students(
              id TEXT PRIMARY KEY,
              firstname TEXT NOT NULL,
              lastname TEXT NOT NULL,
              course TEXT,
              year INTEGER NOT NULL CHECK (year BETWEEN 1 AND 5),
              gender TEXT NOT NULL CHECK (gender IN ('Male','Female','Other')),
              FOREIGN KEY (course) REFERENCES programs(code) ON DELETE SET NULL,
              CHECK (id GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]')
              )""")
    conn.commit()
    conn.close()

    ensure_programs_constraints()
    ensure_students_constraints()


def _get_table_sql(c, table_name):
    row = c.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row[0] if row and row[0] else ""


def ensure_programs_constraints():
    """One-time migration: align programs schema with ON DELETE SET NULL and nullable FK."""
    conn = get_connection()
    c = conn.cursor()

    fk_rows = c.execute("PRAGMA foreign_key_list(programs)").fetchall()
    program_fk = None
    for fk in fk_rows:
        if fk[3] in ("college", "college_code") and fk[2] == "colleges":
            program_fk = fk
            break

    on_delete_action = (program_fk[6] if program_fk else "").upper()
    table_info = c.execute("PRAGMA table_info(programs)").fetchall()
    column_names = {row[1] for row in table_info}
    college_column = next((row for row in table_info if row[1] == "college"), None)
    college_not_null = bool(college_column and college_column[3] == 1)
    table_sql = _get_table_sql(c, "programs").lower()
    has_unique_name_college = "unique(name,college)" in table_sql.replace(" ", "")
    has_legacy_column = "college_code" in column_names

    if on_delete_action == "SET NULL" and not college_not_null and has_unique_name_college and not has_legacy_column:
        conn.close()
        return

    c.execute("PRAGMA foreign_keys = OFF")
    c.execute("BEGIN")
    try:
        c.execute("ALTER TABLE programs RENAME TO programs_old")

        c.execute("""CREATE TABLE programs(
              code TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              college TEXT,
              FOREIGN KEY (college) REFERENCES colleges(code)
              ON DELETE SET NULL,
              UNIQUE(name,college)
              )""")

        old_columns = {row[1] for row in c.execute("PRAGMA table_info(programs_old)").fetchall()}
        source_college_column = "college" if "college" in old_columns else "college_code"

        c.execute(f"""INSERT INTO programs(code, name, college)
               SELECT code, name, {source_college_column}
               FROM programs_old""")

        c.execute("DROP TABLE programs_old")
        c.execute("COMMIT")
    except Exception:
        c.execute("ROLLBACK")
        raise
    finally:
        c.execute("PRAGMA foreign_keys = ON")
        conn.close()


def ensure_students_constraints():
    """One-time migration: align students schema checks and nullable FK with ON DELETE SET NULL."""
    conn = get_connection()
    c = conn.cursor()

    fk_rows = c.execute("PRAGMA foreign_key_list(students)").fetchall()
    student_fk = None
    for fk in fk_rows:
        if fk[3] in ("course", "program_code") and fk[2] == "programs":
            student_fk = fk
            break

    on_delete_action = (student_fk[6] if student_fk else "").upper()
    table_info = c.execute("PRAGMA table_info(students)").fetchall()
    column_names = {row[1] for row in table_info}
    course_column = next((row for row in table_info if row[1] == "course"), None)
    program_column = next((row for row in table_info if row[1] == "program_code"), None)
    target_column = course_column if course_column else program_column
    program_not_null = bool(target_column and target_column[3] == 1)
    table_sql = _get_table_sql(c, "students").lower().replace(" ", "")
    has_year_check = "check(yearbetween1and5)" in table_sql
    has_gender_check = "check(genderin('male','female','other'))" in table_sql
    has_id_check = "check(idglob'[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]')" in table_sql

    has_legacy_column = "program_code" in column_names

    if (
        on_delete_action == "SET NULL"
        and not program_not_null
        and has_year_check
        and has_gender_check
        and has_id_check
        and not has_legacy_column
    ):
        conn.close()
        return

    c.execute("PRAGMA foreign_keys = OFF")
    c.execute("BEGIN")
    try:
        c.execute("ALTER TABLE students RENAME TO students_old")

        c.execute("""CREATE TABLE students(
              id TEXT PRIMARY KEY CHECK (id GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]'),
              firstname TEXT NOT NULL,
              lastname TEXT NOT NULL,
              course TEXT,
              year INTEGER NOT NULL CHECK (year BETWEEN 1 AND 5),
              gender TEXT NOT NULL CHECK (gender IN ('Male','Female','Other')),
              FOREIGN KEY (course) REFERENCES programs(code) ON DELETE SET NULL
              )""")

        old_columns = {row[1] for row in c.execute("PRAGMA table_info(students_old)").fetchall()}
        source_course_column = "course" if "course" in old_columns else "program_code"

        c.execute(f"""INSERT INTO students(id, firstname, lastname, course, year, gender)
                                     SELECT id, firstname, lastname, {source_course_column}, CAST(year AS INTEGER), gender
                                     FROM students_old""")

        c.execute("DROP TABLE students_old")
        c.execute("COMMIT")
    except Exception:
        c.execute("ROLLBACK")
        raise
    finally:
        c.execute("PRAGMA foreign_keys = ON")
        conn.close()

#*********************create***************************************
def add_student(id, fname, lname, p_code, year, gender):
    """Inserts a new student into the database."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""INSERT INTO students(id, firstname, lastname, course, year, gender)
                  VALUES(?,?,?,?,?,?)""",
                  (id,fname,lname,p_code,year,gender))
        conn.commit()
    except sqlite3.IntegrityError:
        print("Error: Program code does not exist or Student ID is a duplicate.")
        raise
    finally:
        conn.close()

def add_program(code, name, college):
    """Inserts a new program into the database."""
    conn = get_connection()
    c = conn.cursor()
    
    try:
        c.execute(""" INSERT INTO programs(code, name, college)
                  VALUES (?,?,?)""",
                  (code,name,college))
        conn.commit()

    except sqlite3.IntegrityError:
        print("Error: Program code does not exist")
        raise
    finally:
        conn.close()


def add_college(code, name):
    """Inserts a new college into the database."""
    conn = get_connection()
    c = conn.cursor()

    try:
        c.execute("""INSERT INTO colleges(code,name)
                  VALUES(?,?)""", (code,name))
        conn.commit()
    except sqlite3.IntegrityError:
        print("Error")
        raise
    finally:
        conn.close()

    
#*********************update***************************************
def update_student(student_id, fname, lname, p_code, year, gender):
    """Updates an existing student record based on their ID."""
    conn = get_connection()
    c = conn.cursor()
    
    try:
        c.execute("""UPDATE students SET firstname=?,
                         lastname=?,
                         course=?,
                                         year = ?, 
                                         gender = ? WHERE id = ?
                  """, (fname,lname,p_code,year,gender, student_id))
        conn.commit()
    except sqlite3.IntegrityError:
        print("Error")
        raise
    finally:
        conn.close()


def update_program(code, name, college):
    """Updates an existing program record based on its code."""
    conn = get_connection()
    c = conn.cursor()

    try:
        c.execute(""" UPDATE programs SET college = ?,
                                          name = ? WHERE code= ?
                  """, (college,name,code))
        conn.commit()
    except sqlite3.IntegrityError:
        print("ERROR!")
        raise

    finally:
        conn.close()

def update_college(code, name):
    """Updates colleges"""
    conn = get_connection()
    c = conn.cursor()

    try:
        c.execute(""" UPDATE colleges SET 
                                          name = ? WHERE code = ?
                  """,(name,code))
        conn.commit()
    except sqlite3.IntegrityError:
        print("ERROR!")
        raise

    finally:
        conn.close()

def get_all(table_name):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_record(table_name, identifier):
    """Removes a row from the specified table using its Primary Key."""
    pk="id" if table_name == "students" else "code"
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(f" DELETE FROM {table_name} WHERE {pk}=?", (identifier,))
        conn.commit()
    except sqlite3.IntegrityError:
        print("ERROR!")
        raise
    finally:
        conn.close()
def get_one(table_name, identifier):
    pk = "id" if table_name == "students" else "code"
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        f"SELECT * FROM {table_name} WHERE {pk}=?", (identifier,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_page(
    table_name,
    page,
    rows_per_page,
    order_by=None,
    reverse=False,
    search_column=None,
    search_query="",
):
    _validate_table(table_name)
    offset = (page - 1) * rows_per_page
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    where_sql, where_params = _build_where_clause(table_name, search_column, search_query)
    order_sql = _build_order_clause(table_name, order_by, reverse)
    sql = f"SELECT * FROM {table_name}{where_sql}{order_sql} LIMIT ? OFFSET ?"
    rows = conn.execute(sql, (*where_params, rows_per_page, offset)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_count(table_name, search_column=None, search_query=""):
    _validate_table(table_name)
    conn = get_connection()
    where_sql, where_params = _build_where_clause(table_name, search_column, search_query)
    sql = f"SELECT COUNT(*) FROM {table_name}{where_sql}"
    count = conn.execute(sql, where_params).fetchone()[0]
    conn.close()
    return count


def _infer_error_field(message):
    msg = str(message).lower()
    if "id" in msg:
        return "id"
    if "first name" in msg:
        return "firstname"
    if "last name" in msg:
        return "lastname"
    if "program code" in msg:
        return "course"
    if "college" in msg:
        return "college"
    if "year" in msg:
        return "year"
    if "gender" in msg:
        return "gender"
    if "code" in msg:
        return "code"
    if "name" in msg:
        return "name"
    return "row"


def _normalize_row_for_table(table_name, row):
    from modules import validators

    if table_name == "students":
        return validators.normalize_student_data(row)
    if table_name == "programs":
        return validators.normalize_program_data(row)
    if table_name == "colleges":
        return validators.normalize_college_data(row)
    return row


def _validate_row_for_table(table_name, row):
    from modules import validators

    if table_name == "students":
        return validators.validate_student(
            row,
            skip_id_check=True,
            skip_duplicate_profile_check=True,
        )
    if table_name == "programs":
        return validators.validate_program(row, is_edit=True)
    if table_name == "colleges":
        return validators.validate_college(row, is_edit=True)
    return False, "Unsupported table."


def validate_csv_rows(table_name, filename):
    _validate_table(table_name)
    columns = TABLE_COLUMNS[table_name]
    errors = []
    normalized_rows = []

    with open(filename, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        normalized_headers = _normalize_csv_headers(reader.fieldnames or [])
        missing_columns = [column for column in columns if column not in normalized_headers]
        if missing_columns:
            errors.append(
                {
                    "row": 1,
                    "field": "header",
                    "message": f"Missing required columns for {table_name}: {', '.join(missing_columns)}",
                }
            )
            return False, errors, normalized_rows

        seen_primary = set()
        seen_student_profiles = set()
        pk_field = "id" if table_name == "students" else "code"

        for row_num, raw_row in enumerate(reader, start=2):
            row = _normalize_row_for_table(table_name, raw_row)
            normalized_rows.append(row)

            is_valid, message = _validate_row_for_table(table_name, row)
            if not is_valid:
                errors.append({"row": row_num, "field": _infer_error_field(message), "message": message})
                continue

            pk_value = str(row.get(pk_field, "")).strip()
            if pk_value in seen_primary:
                errors.append(
                    {
                        "row": row_num,
                        "field": pk_field,
                        "message": f"Duplicate {pk_field} '{pk_value}' found in CSV.",
                    }
                )
            else:
                seen_primary.add(pk_value)

            if table_name == "students":
                profile_key = (
                    row.get("firstname", ""),
                    row.get("lastname", ""),
                    row.get("course", ""),
                    str(row.get("year", "")),
                )
                if profile_key in seen_student_profiles:
                    errors.append(
                        {
                            "row": row_num,
                            "field": "profile",
                            "message": "Duplicate student profile in CSV (firstname, lastname, course, year).",
                        }
                    )
                else:
                    seen_student_profiles.add(profile_key)

    return len(errors) == 0, errors, normalized_rows
    
def export_table(table_name, filename):
    _validate_table(table_name)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        headers = [column[0] for column in cursor.description]

        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(headers)
            csv_writer.writerows(rows)

        return len(rows)
    finally:
        conn.close()


def backup_database(destination_path=None):
    os.makedirs(BACKUP_DIR, exist_ok=True)

    if destination_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination_path = os.path.join(BACKUP_DIR, f"sis_backup_{timestamp}.db")

    source_conn = get_connection()
    backup_conn = sqlite3.connect(destination_path)
    try:
        source_conn.backup(backup_conn)
        backup_conn.commit()
    finally:
        backup_conn.close()
        source_conn.close()

    return destination_path


def restore_database(backup_path):
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    backup_conn = sqlite3.connect(backup_path)
    try:
        integrity = backup_conn.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        backup_conn.close()

    if integrity.lower() != "ok":
        raise ValueError(f"Backup integrity check failed: {integrity}")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    shutil.copy2(backup_path, DB_PATH)

    restored_conn = get_connection()
    try:
        restored_integrity = restored_conn.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        restored_conn.close()

    if restored_integrity.lower() != "ok":
        raise ValueError(f"Restored database integrity check failed: {restored_integrity}")

    return True


def _sanitize_name_for_legacy(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"[^A-Za-z\s\-\',.]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def cleanup_legacy_students(dry_run=True, fallback_program_code=None, max_details=25):
    from modules import validators

    if fallback_program_code is not None and not validators.program_exists(fallback_program_code):
        raise ValueError(f"Fallback program code '{fallback_program_code}' does not exist.")

    conn = get_connection()
    updates = []

    try:
        rows = conn.execute(
            "SELECT id, firstname, lastname, course, year, gender FROM students"
        ).fetchall()

        for row in rows:
            student_id, firstname, lastname, program_code, year, gender = row
            new_firstname = validators.normalize_name(firstname)
            new_lastname = validators.normalize_name(lastname)
            new_program_code = program_code
            reasons = []

            if validators._name_invalid(new_firstname):
                sanitized = _sanitize_name_for_legacy(new_firstname)
                if sanitized:
                    new_firstname = validators.normalize_name(sanitized)
                    reasons.append("firstname_sanitized")

            if validators._name_invalid(new_lastname):
                sanitized = _sanitize_name_for_legacy(new_lastname)
                if sanitized:
                    new_lastname = validators.normalize_name(sanitized)
                    reasons.append("lastname_sanitized")

            if (new_program_code is None or str(new_program_code).strip() == "") and fallback_program_code:
                new_program_code = fallback_program_code
                reasons.append("program_code_filled")

            changed = (
                new_firstname != firstname
                or new_lastname != lastname
                or new_program_code != program_code
            )

            if changed:
                updates.append(
                    {
                        "id": student_id,
                        "firstname_before": firstname,
                        "firstname_after": new_firstname,
                        "lastname_before": lastname,
                        "lastname_after": new_lastname,
                        "program_code_before": program_code,
                        "program_code_after": new_program_code,
                        "year": year,
                        "gender": gender,
                        "reasons": reasons,
                    }
                )

        if not dry_run and updates:
            conn.executemany(
                """UPDATE students
                         SET firstname = ?, lastname = ?, course = ?
                   WHERE id = ?""",
                [
                    (
                        item["firstname_after"],
                        item["lastname_after"],
                        item["program_code_after"],
                        item["id"],
                    )
                    for item in updates
                ],
            )
            conn.commit()

        unresolved_blank_program_code = sum(
            1
            for row in rows
            if row[3] is None or str(row[3]).strip() == ""
        )
        if fallback_program_code:
            unresolved_blank_program_code = 0

        return {
            "dry_run": dry_run,
            "total_students": len(rows),
            "proposed_updates": len(updates),
            "applied_updates": 0 if dry_run else len(updates),
            "unresolved_blank_program_code": unresolved_blank_program_code,
            "details": updates[:max_details],
        }
    finally:
        conn.close()


def _to_compare_key(value):
    if value is None:
        return ""
    return str(value).strip()


def analyze_import_changes(table_name, normalized_rows):
    _validate_table(table_name)

    columns = TABLE_COLUMNS[table_name]
    pk_field = "id" if table_name == "students" else "code"
    compare_columns = [column for column in columns if column != pk_field]

    if not normalized_rows:
        return {
            "total_rows": 0,
            "inserts": 0,
            "updates": 0,
            "unchanged": 0,
            "pk_field": pk_field,
            "update_samples": [],
        }

    existing_by_pk = {}
    pk_values = [str(row.get(pk_field, "")).strip() for row in normalized_rows]

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        chunk_size = 500
        selected_columns = ", ".join(columns)

        for start in range(0, len(pk_values), chunk_size):
            chunk = pk_values[start:start + chunk_size]
            if not chunk:
                continue
            placeholders = ",".join(["?"] * len(chunk))
            rows = cursor.execute(
                f"SELECT {selected_columns} FROM {table_name} "
                f"WHERE {pk_field} IN ({placeholders})",
                chunk,
            ).fetchall()
            for row in rows:
                row_dict = dict(row)
                existing_by_pk[str(row_dict.get(pk_field, "")).strip()] = row_dict
    finally:
        conn.close()

    inserts = 0
    updates = 0
    unchanged = 0
    update_samples = []

    for row in normalized_rows:
        pk_value = str(row.get(pk_field, "")).strip()
        existing = existing_by_pk.get(pk_value)

        if existing is None:
            inserts += 1
            continue

        changed_fields = []
        for column in compare_columns:
            old_value = _to_compare_key(existing.get(column))
            new_value = _to_compare_key(row.get(column))
            if old_value != new_value:
                changed_fields.append(column)

        if changed_fields:
            updates += 1
            if len(update_samples) < 5:
                update_samples.append({
                    "pk": pk_value,
                    "changed_fields": changed_fields,
                })
        else:
            unchanged += 1

    return {
        "total_rows": len(normalized_rows),
        "inserts": inserts,
        "updates": updates,
        "unchanged": unchanged,
        "pk_field": pk_field,
        "update_samples": update_samples,
    }

def import_table(table_name, filename):
    _validate_table(table_name)
    columns = TABLE_COLUMNS[table_name]
    placeholders = ",".join(["?"] * len(columns))
    pk_field = "id" if table_name == "students" else "code"
    updatable_columns = [column for column in columns if column != pk_field]
    if updatable_columns:
        update_clause = ", ".join([f"{column}=excluded.{column}" for column in updatable_columns])
        sql = (
            f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT({pk_field}) DO UPDATE SET {update_clause}"
        )
    else:
        sql = (
            f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT({pk_field}) DO NOTHING"
        )

    is_valid, errors, normalized_rows = validate_csv_rows(table_name, filename)
    if not is_valid:
        preview = "; ".join(
            [f"row {e['row']} ({e['field']}): {e['message']}" for e in errors[:5]]
        )
        extra = "" if len(errors) <= 5 else f" ... and {len(errors) - 5} more"
        raise ValueError(f"CSV validation failed: {preview}{extra}")

    conn = get_connection()
    inserted = 0
    try:
        cursor = conn.cursor()
        for row in normalized_rows:
            values = [row[column] for column in columns]
            cursor.execute(sql, values)
            inserted += 1

        conn.commit()
        return inserted
    finally:
        conn.close()



db_initialization()
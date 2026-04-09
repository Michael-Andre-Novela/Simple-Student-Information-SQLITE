import sqlite3
import csv
import os

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(MODULE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "sis_database.db")

ALLOWED_COLUMNS = {
    "students": {"id", "firstname", "lastname", "program_code", "year", "gender", "college"},
    "programs": {"code", "name", "college_code"},
    "colleges": {"code", "name"},
}

TABLE_COLUMNS = {
    "students": ["id", "firstname", "lastname", "program_code", "year", "gender"],
    "programs": ["code", "name", "college_code"],
    "colleges": ["code", "name"],
}

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
            "WHERE p.code = students.program_code "
            "AND p.college_code LIKE ?"
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
        order_expr = "(SELECT p.college_code FROM programs p WHERE p.code = students.program_code)"
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
                "INSERT OR IGNORE INTO programs (code, name, college_code) VALUES (?, ?, ?)",
                (row["code"], row["name"], row["college_code"])
            )
    print(f"Programs migrated.")

    # --- Students last (depends on programs) ---
    students_path = os.path.join(DATA_DIR, "students.csv")
    with open(students_path, newline="") as f:
        for row in csv.DictReader(f):
            c.execute(
                "INSERT OR IGNORE INTO students (id, firstname, lastname, program_code, year, gender) VALUES (?, ?, ?, ?, ?, ?)",
                (row["id"], row["firstname"], row["lastname"],
                 row["program_code"], row["year"], row["gender"])
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
              college_code TEXT,
              FOREIGN KEY (college_code) REFERENCES colleges(code)
              ON DELETE SET NULL,
              UNIQUE(name,college_code)
              )""")

    # 3. Bottom Level: Students (References Programs)
    c.execute(""" CREATE TABLE IF NOT EXISTS students(
              id TEXT PRIMARY KEY,
              firstname TEXT NOT NULL,
              lastname TEXT NOT NULL,
              program_code TEXT,
              year INTEGER NOT NULL CHECK (year BETWEEN 1 AND 5),
              gender TEXT NOT NULL CHECK (gender IN ('Male','Female','Other')),
              FOREIGN KEY (program_code) REFERENCES programs(code) ON DELETE SET NULL,
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
        if fk[3] == "college_code" and fk[2] == "colleges":
            program_fk = fk
            break

    on_delete_action = (program_fk[6] if program_fk else "").upper()
    table_info = c.execute("PRAGMA table_info(programs)").fetchall()
    college_column = next((row for row in table_info if row[1] == "college_code"), None)
    college_not_null = bool(college_column and college_column[3] == 1)
    table_sql = _get_table_sql(c, "programs").lower()
    has_unique_name_college = "unique(name,college_code)" in table_sql.replace(" ", "")

    if on_delete_action == "SET NULL" and not college_not_null and has_unique_name_college:
        conn.close()
        return

    c.execute("PRAGMA foreign_keys = OFF")
    c.execute("BEGIN")
    try:
        c.execute("ALTER TABLE programs RENAME TO programs_old")

        c.execute("""CREATE TABLE programs(
              code TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              college_code TEXT,
              FOREIGN KEY (college_code) REFERENCES colleges(code)
              ON DELETE SET NULL,
              UNIQUE(name,college_code)
              )""")

        c.execute("""INSERT INTO programs(code, name, college_code)
                     SELECT code, name, college_code
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
        if fk[3] == "program_code" and fk[2] == "programs":
            student_fk = fk
            break

    on_delete_action = (student_fk[6] if student_fk else "").upper()
    table_info = c.execute("PRAGMA table_info(students)").fetchall()
    program_column = next((row for row in table_info if row[1] == "program_code"), None)
    program_not_null = bool(program_column and program_column[3] == 1)
    table_sql = _get_table_sql(c, "students").lower().replace(" ", "")
    has_year_check = "check(yearbetween1and5)" in table_sql
    has_gender_check = "check(genderin('male','female','other'))" in table_sql
    has_id_check = "check(idglob'[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]')" in table_sql

    if (
        on_delete_action == "SET NULL"
        and not program_not_null
        and has_year_check
        and has_gender_check
        and has_id_check
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
              program_code TEXT,
              year INTEGER NOT NULL CHECK (year BETWEEN 1 AND 5),
              gender TEXT NOT NULL CHECK (gender IN ('Male','Female','Other')),
              FOREIGN KEY (program_code) REFERENCES programs(code) ON DELETE SET NULL
              )""")

        c.execute("""INSERT INTO students(id, firstname, lastname, program_code, year, gender)
                     SELECT id, firstname, lastname, program_code, CAST(year AS INTEGER), gender
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
        c.execute("""INSERT INTO students(id, firstname, lastname, program_code, year, gender)
                  VALUES(?,?,?,?,?,?)""",
                  (id,fname,lname,p_code,year,gender))
        conn.commit()
    except sqlite3.IntegrityError:
        print("Error: Program code does not exist or Student ID is a duplicate.")
    finally:
        conn.close()

def add_program(code, name, college_code):
    """Inserts a new program into the database."""
    conn = get_connection()
    c = conn.cursor()
    
    try:
        c.execute(""" INSERT INTO programs(code, name, college_code)
                  VALUES (?,?,?)""",
                  (code,name,college_code))
        conn.commit()

    except sqlite3.IntegrityError:
        print("Error: Program code does not exist")
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
                                         program_code=?,
                                         year = ?, 
                                         gender = ? WHERE id = ?
                  """, (fname,lname,p_code,year,gender, student_id))
        conn.commit()
    except sqlite3.IntegrityError:
        print("Error")
    finally:
        conn.close()


def update_program(code, name, college_code):
    """Updates an existing program record based on its code."""
    conn = get_connection()
    c = conn.cursor()

    try:
        c.execute(""" UPDATE programs SET college_code = ?,
                                          name = ? WHERE code= ?
                  """, (college_code,name,code))
        conn.commit()
    except sqlite3.IntegrityError:
        print("ERROR!")

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
    finally:
        conn.close()
def search(table_name, column, query):
    pk = "id" if table_name == "students" else "code"
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"SELECT * FROM {table_name} WHERE {column} LIKE ?", (f"%{query}%",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def sort(table_name,column, reverse=False):
    order = "DESC" if reverse else "ASC"
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"SELECT * FROM {table_name} ORDER BY {column} {order}"
    ).fetchall()
    conn.close()
    return[dict(r) for r in rows]

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

def import_table(table_name, filename):
    _validate_table(table_name)
    columns = TABLE_COLUMNS[table_name]
    placeholders = ",".join(["?"] * len(columns))
    sql = f"INSERT OR REPLACE INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"

    conn = get_connection()
    inserted = 0
    try:
        cursor = conn.cursor()
        with open(filename, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            missing_columns = [column for column in columns if column not in (reader.fieldnames or [])]
            if missing_columns:
                raise ValueError(f"Missing required columns for {table_name}: {', '.join(missing_columns)}")

            for row in reader:
                values = [row[column] for column in columns]
                cursor.execute(sql, values)
                inserted += 1

        conn.commit()
        return inserted
    finally:
        conn.close()



db_initialization()
import sqlite3

def get_connection():
    conn=sqlite3.connect('sis_database.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def db_initialization():
    conn = get_connection()
    c =conn.cursor()

    # 1. Top Level: Colleges
    c.execute(""" CREATE TABLE IF NOT EXISTS colleges(
              code TEXT PRIMARY KEY,
              name TEXT
              )""")
    
    # 2. Mid Level: Programs (References Colleges)
    c.execute(""" CREATE TABLE IF NOT EXISTS programs(
              code TEXT PRIMARY KEY,
              name TEXT,
              college_code TEXT,
              FOREIGN KEY (college_code) REFERENCES colleges(code)
              ON DELETE CASCADE
              )""")

    # 3. Bottom Level: Students (References Programs)
    c.execute(""" CREATE TABLE IF NOT EXISTS students(
              id TEXT PRIMARY KEY,
              firstname TEXT,
              lastname TEXT,
              program_code TEXT,
              year TEXT,
              gender TEXT,
              FOREIGN KEY (program_code) REFERENCES programs(code)
              ON DELETE SET NULL
              )""")
    conn.commit()
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

def get_page(table_name, page, rows_per_page):
    offset = (page - 1) * rows_per_page
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (rows_per_page, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_count(table_name):
    conn = get_connection()
    count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    conn.close()
    return count

db_initialization()
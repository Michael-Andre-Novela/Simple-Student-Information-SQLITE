"""
import os
import csv
import sqlite3

#So users don't have to worry about file paths, we can set up a base directory for our data files. 
#This way, we can easily read from and write to our CSV files without hardcoding the paths every time.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
data_dir = os.path.join(project_root, 'data')
 
#Maps
#for easy access to the file paths
FILES ={"students": os.path.join(data_dir, 'students.csv'),
        "colleges": os.path.join(data_dir, 'colleges.csv'),
        "programs": os.path.join(data_dir, 'programs.csv')}

#Schema headers for each CSV file, which will be useful when reading and writing data to ensure consistency.
Headers = {"students": ['id', 'firstname', 'lastname', 'program_code', 'year', 'gender'],
           "colleges": ['code', 'name'],
           "programs": ['code', 'name', 'college_code']}


def initialize_storage():
    #if the data directory doesn't exist, create it
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    #for each file in our FILES mapping, check if it exists. If not, create it and write the header row.
    for key, file_path in FILES.items():
        if not os.path.exists(file_path):
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(Headers[key])

#CRUD functions
 
def read_csv(file_key):
    file_path = FILES[file_key]
    data = []
    try:
        with open(file_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    except (FileNotFoundError, OSError):
        pass
    return data

def write_csv(file_key, data):
    file_path = FILES[file_key]
    try:
        with open(file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=Headers[file_key])
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        return True
    except OSError:
        return False


def get_pk(file_key):
    #Return the primary key column name for a given file key.
    return 'id' if file_key == 'students' else 'code'


def add_csv(file_key, row):
    #Append a single new row to a CSV file.
    data = read_csv(file_key)
    data.append(row)
    write_csv(file_key, data)
    return data


def search_csv(file_key, search_query, column=None):
    data = read_csv(file_key)
    search_query = search_query.lower()
    results = []
    for row in data:
        if column:
            if search_query in str(row[column]).lower():
                results.append(row)
        else:
            if any(search_query in str(val).lower() for val in row.values()):
                results.append(row)
    return results

def delete_csv(file_key, id_value, id_column=None):
    if id_column is None:
        id_column = get_pk(file_key)
    data = read_csv(file_key)
    updated_data = [row for row in data if row[id_column] != id_value]
    write_csv(file_key, updated_data)
    return updated_data

def update_csv(file_key, id_value, updated_row, id_column=None):
    if id_column is None:
        id_column = get_pk(file_key)
    data = read_csv(file_key)
    new_list = [updated_row if row[id_column] == id_value else row for row in data]
    write_csv(file_key, new_list)
    return new_list

def sort_csv(file_key, sort_by_column, reverse=False):
    data = read_csv(file_key)
    return sorted(data, key=lambda x: x[sort_by_column].lower(), reverse=reverse)

"""

import sqlite3

def connection():
    return sqlite3.connect('sis_database.db')

c=connection.cursor()

def db_initialization():
    c.execute(""" CREATE TABLE students(
              id TEXT,
              firstname TEXT,
              lastname TEXT,
              program_code TEXT,
              year TEXT,
              gender TEXT
              )
""")
    c.execute(""" CREATE TABLE colleges(
              code TEXT,
              name TEXT
              )""")
    c.execute(""" CREATE TABLE programs(
              code TEXT,
              name TEXT,
              college_code TEXT
              )""")

def add_student(student_id, fname, lname, p_code, year, gender):
    """Inserts a new student into the database."""
    pass

def add_program(code, name, college_code):
    """Inserts a new program into the database."""
    pass

def add_college(code, name):
    """Inserts a new college into the database."""
    pass

def update_student(student_id, fname, lname, p_code, year, gender):
    """Updates an existing student record based on their ID."""
    pass

def update_program(code, name, college_code):
    """Updates an existing program record based on its code."""
    pass

def delete_record(table_name, identifier):
    """Removes a row from the specified table using its Primary Key."""
    pass



import pandas as pd
import psycopg2
import os
import random
from datetime import datetime
from fastapi import FastAPI
from mangum import Mangum

# Database connection details
host = os.environ['DB_HOST']
dbname = os.environ['DB_NAME']
user = os.environ['DB_USER']
password = os.environ['DB_PASSWORD']
port = os.environ['DB_PORT']

def create_model():
    create_departments_table = """
    CREATE TABLE IF NOT EXISTS departments (
        department_id INTEGER PRIMARY KEY,
        department_name VARCHAR(255) NOT NULL
    );
    """

    create_job_titles_table = """
    CREATE TABLE IF NOT EXISTS job_titles (
        job_id INTEGER PRIMARY KEY,
        job_title VARCHAR(255) NOT NULL
    );
    """

    create_employees_table = """
    CREATE TABLE IF NOT EXISTS employees (
        employee_id INTEGER PRIMARY KEY,
        employee_name VARCHAR(255) NOT NULL,
        department_id INTEGER,
        job_id INTEGER,
        hire_date DATE NOT NULL,
        FOREIGN KEY (department_id) REFERENCES departments(department_id),
        FOREIGN KEY (job_id) REFERENCES job_titles(job_id)
    );
    """
    return create_departments_table, create_job_titles_table, create_employees_table

def create_data(num_employees: int = 100):
    path_lambda = "/tmp"
    # Departamentos Data
    departments_data = {
        "department_id":  [1, 2, 3, 4, 5],
        "department_name": ["IT", "Human Resources", "Finance", "Marketing", "Sales"]
    }

    # Puestos de trabajo Data
    job_titles_data = {
        "job_id": [101, 102, 103, 104, 105],
        "job_title": ["Software Developer", "HR Manager", "Financial Analyst", "Marketing Specialist", "Sales Representative"]
    }

    # Empleados Data
    employees_data = {
        "employee_id": [i for i in range(num_employees)],
        "employee_name": [f"Employee {i}" for i in range(num_employees)],
        "department_id": np.random.choice([1, 2, 3, 4, 5], num_employees),
        "job_id": np.random.choice([101, 102, 103, 104, 105], num_employees),
        "hire_date": [datetime(2021, random.randint(1, 12), random.randint(1, 28)).strftime("%Y-%m-%d") for _ in range(num_employees)]
    }

    # Convertir a DataFrame
    departments_df = pd.DataFrame(departments_data)
    job_titles_df = pd.DataFrame(job_titles_data)
    employees_df = pd.DataFrame(employees_data)

    employees_df.to_parquet(f"{path_lambda}/employees.parquet", index=False)
    departments_df.to_parquet(f"{path_lambda}/departments.parquet", index=False)
    job_titles_df.to_parquet(f"{path_lambda}/job_titles.parquet", index=False)

def load_data():

    # Establish connection
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    cur = conn.cursor()

    # Create tables
    create_departments_table, create_job_titles_table, create_employees_table = create_model()
    cur.execute(create_departments_table)
    cur.execute(create_job_titles_table)
    cur.execute(create_employees_table)
    conn.commit()

    # Assuming /tmp is where you've stored your parquet files
    employees_df = pd.read_parquet('/tmp/employees.parquet')
    departments_df = pd.read_parquet('/tmp/departments.parquet')
    job_titles_df = pd.read_parquet('/tmp/job_titles.parquet')

    # Here you can insert the data into your PostgreSQL database
    # Insert departments data
    for _, row in departments_df.iterrows():
        cur.execute("INSERT INTO departments (department_id, department_name) VALUES (%s, %s)", (row['department_id'], row['department_name']))
    
    # Insert job titles data
    for _, row in job_titles_df.iterrows():
        cur.execute("INSERT INTO job_titles (job_id, job_title) VALUES (%s, %s)", (row['job_id'], row['job_title']))
    
    # Insert employees data
    for _, row in employees_df.iterrows():
        cur.execute("INSERT INTO employees (employee_id, employee_name, department_id, job_id, hire_date) VALUES (%s, %s, %s, %s, %s)", (row['employee_id'], row['employee_name'], row['department_id'], row['job_id'], row['hire_date']))
    
    conn.commit()

    # Close connections
    cur.close()
    conn.close()
    
    return {
        'statusCode': 200,
        'body': 'Data batch uploaded successfully'
    }

def create_view ():
    create_view = """
            CREATE OR REPLACE VIEW employee_summary AS
            SELECT
                e.employee_name AS "Employee Name",
                jt.job_title AS "Job Title",
                d.department_name AS "Department",
                e.hire_date AS "Hire Date"
            FROM
                employees e
                JOIN departments d ON e.department_id = d.department_id
                JOIN job_titles jt ON e.job_id = jt.job_id
            ORDER BY
                d.department_name, e.hire_date;
    """
    # create view postgress
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    cur = conn.cursor()
    cur.execute(create_view)
    conn.commit()
    cur.close()
    conn.close()
    return {
        'statusCode': 200,
        'body': 'View created successfully'
    }

app = FastAPI()
handler = Mangum(app)

@app.get("/create_data")
def create_data():
    create_data()
    load_data()
    return {"message": "Data created and loaded successfully"}

@app.get("/create_view")
def create_view():
    create_view()
    return {"message": "View created successfully"}

@app.get("/view_summary")
def view_summary():
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    cur = conn.cursor()
    cur.execute("SELECT * FROM employee_summary")
    data = cur.fetchall()
    cur.close()
    conn.close()
    # return the data as a list of dictionaries
    return FastAPI.Response(content=data, media_type="application/json")

app.get("/")
def read_root():
    return {"message": "Welcome to the Employee Summary API"}

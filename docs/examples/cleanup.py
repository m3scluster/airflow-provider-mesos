import psycopg2
from datetime import datetime
import requests
import json
import argparse

# Postgres Verbindungsdaten
DB_PARAMS = {
    'dbname': 'airflow',
    'user': 'airflow',
    'password': '',
    'host': 'localhost',
    'port': '5432'
}

# Airflow API Einstellungen
AIRFLOW_API_BASE = 'http://localhost:8080/api/v1'
AIRFLOW_USER = 'admin'
AIRFLOW_PASSWORD = ''

def get_null_state_tasks(dag_id):
    try:
        # Verbindung zur Postgres DB herstellen
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()

        # SQL Query für Tasks mit state = null
        query = """
        SELECT task_id
        FROM task_instance
        WHERE dag_id = %s AND state IN ('queued','failed') AND queued_dttm > current_timestamp - interval '24 hours' AND queued_dttm < current_timestamp - interval '90 minutes'
        """

        cursor.execute(query, (dag_id,))
        tasks = cursor.fetchall()

        return [task[0] for task in tasks]

    except Exception as e:
        print(f"Datenbankfehler: {str(e)}")
        return []

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def clear_tasks_via_api(dag_id, task_ids, dry_run=False):
    if not task_ids:
        print("Keine Tasks zum Clearen gefunden.")
        return

    # API Endpoint für das Clearen von Tasks
    endpoint = f"{AIRFLOW_API_BASE}/dags/{dag_id}/clearTaskInstances"

    # Request Body vorbereiten
    data = {
        "dry_run": dry_run,
        "task_ids": task_ids,
        "only_failed": False
    }

    try:
        if dry_run:
            print(f"DRY RUN: Würde folgende Tasks clearen: {task_ids}")
            print(f"DRY RUN: API Request Body wäre: {json.dumps(data, indent=2)}")
            return

        response = requests.post(
            endpoint,
            json=data,
            auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            print(f"Erfolgreich gecleared: {task_ids}")
        else:
            print(f"Fehler beim Clearen. Status Code: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"API-Fehler: {str(e)}")

def main():
    # Argument Parser einrichten
    parser = argparse.ArgumentParser(description='Clear Airflow tasks with null state')
    parser.add_argument('dag_id', help='Die DAG ID')
    parser.add_argument('--dry-run', action='store_true',
                      help='Führt einen Dry-Run durch ohne tatsächliche Änderungen')

    args = parser.parse_args()

    # Tasks mit null state finden
    null_tasks = get_null_state_tasks(args.dag_id)

    if null_tasks:
        print(f"Gefundene Tasks mit null state: {null_tasks}")
        clear_tasks_via_api(args.dag_id, null_tasks, args.dry_run)
    else:
        print("Keine Tasks mit null state gefunden.")

if __name__ == "__main__":
    main()


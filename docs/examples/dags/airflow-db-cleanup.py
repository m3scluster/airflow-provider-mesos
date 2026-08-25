"""
A maintenance workflow that you can deploy into Airflow to periodically clean
out the DagRun, TaskInstance, Log, XCom, Job DB and SlaMiss entries to avoid
having too much data in your Airflow MetaStore.

## Authors

The DAG is a fork of [teamclairvoyant repository.](
https://github.com/teamclairvoyant/airflow-maintenance-dags/tree/master/db-cleanup
)

## Usage

1. Update the global variables (SCHEDULE_INTERVAL, DAG_OWNER_NAME,
  ALERT_EMAIL_ADDRESSES and ENABLE_DELETE) in the DAG with the desired values

2. Modify the DATABASE_OBJECTS list to add/remove objects as needed. Each
   dictionary in the list features the following parameters:
    - airflow_db_model: Model imported from airflow.models corresponding to
      a table in the airflow metadata database
    - age_check_column: Column in the model/table to use for calculating max
      date of data deletion

3. Create and Set the following Variables in the Airflow Web Server
  (Admin -> Variables)
    - airflow_db_cleanup__max_db_entry_age_in_days - integer - Length to
      retain the log files if not already provided in the conf. If this is set
      to 30, the job will remove those files that are 30 days old or older.

4. Put the DAG in your gcs bucket.
"""
from datetime import datetime, timedelta
import logging
import os

import airflow
from airflow import settings
from airflow.models import (
    DAG,
    DagModel,
    DagRun,
    Log,
    TaskInstance,
    Variable,
    XCom,
)
from airflow.operators.python import PythonOperator
from airflow.utils.types import DagRunType
from airflow.utils import timezone
from airflow.version import version as airflow_version

import dateutil.parser
from sqlalchemy import desc, sql, text
from sqlalchemy.exc import ProgrammingError

now = timezone.utcnow

# airflow-db-cleanup
DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
START_DATE = datetime.now(timezone.utc) - timedelta(days=1)
# How often to Run. @daily - Once a day at Midnight (UTC)
SCHEDULE_INTERVAL = "@daily"
# Who is listed as the owner of this DAG in the Airflow Web Server
DAG_OWNER_NAME = "operations"
# List of email address to send email alerts to if this job fails
ALERT_EMAIL_ADDRESSES = []
# Airflow version used by the environment in list form, value stored in
# airflow_version is in format e.g "2.3.4+composer"
AIRFLOW_VERSION = airflow_version[: -len("+composer")].split(".")
# Length to retain the log files if not already provided in the conf. If this
# is set to 30, the job will remove those files that arE 30 days old or older.
DEFAULT_MAX_DB_ENTRY_AGE_IN_DAYS = int(
    Variable.get("airflow_db_cleanup__max_db_entry_age_in_days", 30)
)
# Prints the database entries which will be getting deleted; set to False
# to avoid printing large lists and slowdown process
PRINT_DELETES = True
# Whether the job should delete the db entries or not. Included if you want to
# temporarily avoid deleting the db entries.
ENABLE_DELETE = True
# Mapping dictionary to resolve model and column names to actual classes/columns
# This is needed because Airflow 3.1.6 requires params to be JSON-serializable
MODEL_MAPPING = {
    "DagRun": DagRun,
    "TaskInstance": TaskInstance,
    "Log": Log,
    "DagModel": DagModel,
}
# List of all the objects that will be deleted. Comment out the DB objects you
# want to skip.
# Note: Using string names instead of actual classes for Airflow 3.1.6 compatibility
DATABASE_OBJECTS = [
    {
        "airflow_db_model": "DagRun",
        "age_check_column": "logical_date",
        "keep_last": True,
        "keep_last_filters": None,  # Will be reconstructed in cleanup_function
        "keep_last_group_by": "dag_id",
    },
    {
        "airflow_db_model": "TaskInstance",
        "age_check_column": "start_date",
        "keep_last": False,
        "keep_last_filters": None,
        "keep_last_group_by": None,
    },
    {
        "airflow_db_model": "Log",
        "age_check_column": "dttm",
        "keep_last": False,
        "keep_last_filters": None,
        "keep_last_group_by": None,
    },
    {
        "airflow_db_model": "DagModel",
        "age_check_column": "last_parsed_time",
        "keep_last": False,
        "keep_last_filters": None,
        "keep_last_group_by": None,
    },
]

# Check for TaskReschedule model
try:
    from airflow.models import TaskReschedule
    MODEL_MAPPING["TaskReschedule"] = TaskReschedule

    DATABASE_OBJECTS.append(
        {
            "airflow_db_model": "TaskReschedule",
            "age_check_column": "execution_date" if AIRFLOW_VERSION < ["2", "2", "0"] else "start_date",
            "keep_last": False,
            "keep_last_filters": None,
            "keep_last_group_by": None,
        }
    )

except Exception as e:
    logging.error(e)

try:
    from airflow.jobs.job import Job
    MODEL_MAPPING["Job"] = Job

    DATABASE_OBJECTS.append(
        {
            "airflow_db_model": "Job",
            "age_check_column": "latest_heartbeat",
            "keep_last": False,
            "keep_last_filters": None,
            "keep_last_group_by": None,
        }
    )
except Exception as e:
    logging.error(e)

default_args = {
    "owner": DAG_OWNER_NAME,
    "depends_on_past": False,
    "email": ALERT_EMAIL_ADDRESSES,
    "email_on_failure": True,
    "email_on_retry": False,
    "start_date": START_DATE,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

dag = DAG(
    DAG_ID,
    default_args=default_args,
    schedule=SCHEDULE_INTERVAL,
    start_date=START_DATE,
)
if hasattr(dag, "doc_md"):
    dag.doc_md = __doc__
if hasattr(dag, "catchup"):
    dag.catchup = False


def print_configuration_function(**context):
    logging.info("Loading Configurations...")
    dag_run_conf = context.get("dag_run").conf
    logging.info("dag_run.conf: " + str(dag_run_conf))
    max_db_entry_age_in_days = None
    if dag_run_conf:
        max_db_entry_age_in_days = dag_run_conf.get(
            "maxDBEntryAgeInDays", None
        )
    logging.info("maxDBEntryAgeInDays from dag_run.conf: " + str(dag_run_conf))
    if max_db_entry_age_in_days is None or max_db_entry_age_in_days < 1:
        logging.info(
            "maxDBEntryAgeInDays conf variable isn't included or Variable "
            + "value is less than 1. Using Default '"
            + str(DEFAULT_MAX_DB_ENTRY_AGE_IN_DAYS)
            + "'"
        )
        max_db_entry_age_in_days = DEFAULT_MAX_DB_ENTRY_AGE_IN_DAYS
    max_date = now() + timedelta(-max_db_entry_age_in_days)
    logging.info("Finished Loading Configurations")
    logging.info("")

    logging.info("Configurations:")
    logging.info("max_db_entry_age_in_days: " + str(max_db_entry_age_in_days))
    logging.info("max_date:                 " + str(max_date))
    logging.info("enable_delete:            " + str(ENABLE_DELETE))
    logging.info("")

    logging.info("Setting max_execution_date to XCom for Downstream Processes")
    context["ti"].xcom_push(key="max_date", value=max_date.isoformat())


print_configuration = PythonOperator(
    task_id="print_configuration",
    python_callable=print_configuration_function,
    dag=dag,
)


def build_query(
    session,
    airflow_db_model,
    age_check_column,
    max_date,
    dag_id=None
):
    """
    Build a database query to retrieve and filter Airflow data.

    Args:
        session: SQLAlchemy session object for database interaction.
        airflow_db_model: The Airflow model class to query (e.g., DagRun).
        age_check_column: The column representing the age of the data.
        max_date: The maximum allowed age for the data.
        dag_id (optional): The ID of the DAG to filter by. Defaults to None.

    Returns:
        SQLAlchemy query object: The constructed query.
    """
    query = session.query(airflow_db_model)

    logging.info("INITIAL QUERY : " + str(query))

    if dag_id:
        query = query.filter(airflow_db_model.dag_id == dag_id)

    if airflow_db_model == DagRun:
        # For DaRus we want to leave last DagRun regardless of its age
        newest_dagrun = (
            session
            .query(airflow_db_model)
            .filter(airflow_db_model.dag_id == dag_id)
            .order_by(desc(airflow_db_model.execution_date))
            .first()
        )
        logging.info("Newest dagrun: " + str(newest_dagrun))
        if newest_dagrun is not None:
            query = (
                query
                .filter(DagRun.external_trigger.is_(False))
                .filter(age_check_column <= max_date)
                .filter(airflow_db_model.id != newest_dagrun.id)
            )
        else:
            query = query.filter(sql.false())
    else:
        query = query.filter(age_check_column <= max_date)

    logging.info("FINAL QUERY: " + str(query))

    return query


def print_query(query, airflow_db_model, age_check_column):
    entries_to_delete = query.all()

    logging.info("Query: " + str(query))
    logging.info(
        "Process will be Deleting the following "
        + str(airflow_db_model.__name__)
        + "(s):"
    )
    for entry in entries_to_delete:
        date = str(entry.__dict__[str(age_check_column).split(".")[1]])
        logging.info("\tEntry: " + str(entry) + ", Date: " + date)

    logging.info(
        "Process will be Deleting "
        + str(len(entries_to_delete))
        + " "
        + str(airflow_db_model.__name__)
        + "(s)"
    )


def cleanup_function(**context):
    session = settings.Session()

    logging.info("Retrieving max_execution_date from XCom")
    max_date = context["ti"].xcom_pull(
        task_ids=print_configuration.task_id, key="max_date"
    )
    max_date = dateutil.parser.parse(max_date)  # stored as iso8601 str in xcom

    # Resolve model and column names to actual classes/columns for Airflow 3.1.6 compatibility
    airflow_db_model_name = context["params"].get("airflow_db_model")
    airflow_db_model = MODEL_MAPPING.get(airflow_db_model_name)
    if airflow_db_model is None:
        raise ValueError(f"Unknown model: {airflow_db_model_name}")
    
    age_check_column_name = context["params"].get("age_check_column")
    age_check_column = getattr(airflow_db_model, age_check_column_name)
    
    state = context["params"].get("state")
    keep_last = context["params"].get("keep_last")
    
    # Reconstruct keep_last_filters if needed (for DagRun)
    keep_last_filters = None
    if keep_last and airflow_db_model_name == "DagRun":
        keep_last_filters = [airflow_db_model.run_type == DagRunType.SCHEDULED]
    
    keep_last_group_by_name = context["params"].get("keep_last_group_by")
    keep_last_group_by = None
    if keep_last_group_by_name:
        keep_last_group_by = getattr(airflow_db_model, keep_last_group_by_name)

    logging.info("Configurations:")
    logging.info("max_date:                 " + str(max_date))
    logging.info("enable_delete:            " + str(ENABLE_DELETE))
    logging.info("session:                  " + str(session))
    logging.info("airflow_db_model:         " + str(airflow_db_model))
    logging.info("state:                    " + str(state))
    logging.info("age_check_column:         " + str(age_check_column))
    logging.info("keep_last:                " + str(keep_last))
    logging.info("keep_last_filters:        " + str(keep_last_filters))
    logging.info("keep_last_group_by:       " + str(keep_last_group_by))

    logging.info("")

    logging.info("Running Cleanup Process...")

    try:
        if context["params"].get("do_not_delete_by_dag_id"):
            query = build_query(
                session=session,
                airflow_db_model=airflow_db_model,
                age_check_column=age_check_column,
                max_date=max_date,
            )
            if PRINT_DELETES:
                print_query(query, airflow_db_model, age_check_column)
            if ENABLE_DELETE:
                logging.info("Performing Delete...")
                query.delete(synchronize_session=False)
            session.commit()
        else:
            dags = session.query(airflow_db_model.dag_id).distinct()
            session.commit()

            list_dags = [str(list(dag)[0]) for dag in dags] + [None]
            for dag_id in list_dags:
                query = build_query(
                    session=session,
                    airflow_db_model=airflow_db_model,
                    age_check_column=age_check_column,
                    max_date=max_date,
                    dag_id=dag_id,
                )
                if PRINT_DELETES:
                    print_query(query, airflow_db_model, age_check_column)
                if ENABLE_DELETE:
                    logging.info("Performing Delete...")
                    query.delete(synchronize_session=False)
                session.commit()

        if not ENABLE_DELETE:
            logging.warning(
                "You've opted to skip deleting the db entries. "
                "Set ENABLE_DELETE to True to delete entries!!!"
            )

        logging.info("Finished Running Cleanup Process")

    except ProgrammingError as e:
        logging.error(e)
        logging.error(
            str(airflow_db_model) +
            " is not present in the metadata." +
            "Skipping..."
        )

    finally:
        session.close()


def cleanup_sessions():
    session = settings.Session()

    try:
        logging.info("Deleting sessions...")
        count_statement = (
            "SELECT COUNT(*) AS cnt FROM session " +
            "WHERE expiry < now()::timestamp(0);"
        )
        before = session.execute(text(count_statement)).one_or_none()["cnt"]
        session.execute(
            text(
                "DELETE FROM session WHERE expiry < now()::timestamp(0);"
            )
        )
        after = session.execute(text(count_statement)).one_or_none()["cnt"]
        logging.info("Deleted %s expired sessions.", (before - after))
    except Exception as err:
        logging.exception(err)

    session.commit()
    session.close()


def analyze_db():
    session = settings.Session()
    session.execute("ANALYZE")
    session.commit()
    session.close()


analyze_op = PythonOperator(
    task_id="analyze_query",
    python_callable=analyze_db,
    dag=dag
)

cleanup_session_op = PythonOperator(
    task_id="cleanup_sessions",
    python_callable=cleanup_sessions,
    dag=dag,
)

cleanup_session_op.set_downstream(analyze_op)

for db_object in DATABASE_OBJECTS:
    cleanup_op = PythonOperator(
        task_id="cleanup_" + str(db_object["airflow_db_model"]),
        python_callable=cleanup_function,
        params=db_object,
        dag=dag,
    )

    print_configuration.set_downstream(cleanup_op)
    cleanup_op.set_downstream(analyze_op)

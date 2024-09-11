import datetime

from airflow import DAG
from airflow.operators.bash_operator import BashOperator


my_dag = DAG(
    dag_id="update_latest_data_to_qdrant",
    start_date=datetime.datetime(2024, 9, 1),
    schedule="@hourly",
)
version = "v1"

run_this = BashOperator(
    task_id="update_latest_data_from_postgres_to_qdrant",
    bash_command="cd /Users/tappy/Desktop/llm_agent/llm_agent/src && "
                 "/Users/tappy/Library/Caches/pypoetry/virtualenvs/llm-agent-X4XTy3ta-py3.11/bin/python update_data_to_qdrant.py",
    dag=my_dag
)

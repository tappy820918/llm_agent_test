"""
The purpose of this script is to inject data into the Postgres database.
Steps:
1. Create a connection to the Postgres database.
2. Create a table in the database.
3. Load the data from xlsx file and transform it into a Pydantic Object `Model`.
4. Incrementally insert the data into the Postgres database.

"""
import pandas as pd

from llm_agent.connectors.postgres_connector import PostgresConnector
from llm_agent.src.update_data_to_qdrant import UpdateLatestDataToQdrantV1
from llm_agent.src.utils import Member


def dataframe_update_member_info(data: pd.DataFrame):
    data_to_insert = []
    for index, row in data.iterrows():
        row = row.where(pd.notnull(row), "")
        data_to_insert.append(Member(**row))
    pg_conn = PostgresConnector()
    pg_conn.update_member_info(data_to_insert)


if __name__ == "__main__":
    data_path = "/Users/tappy/Desktop/llm_agent/llm_agent/data/SampleData.xlsx"
    df = pd.read_excel(data_path).query('member_no == member_no')
    dataframe_update_member_info(df)
    print('Data inserted successfully')
    update_latest_data_to_qdrant_v1 = UpdateLatestDataToQdrantV1()
    update_latest_data_to_qdrant_v1.update_latest_data_to_qdrant(False)

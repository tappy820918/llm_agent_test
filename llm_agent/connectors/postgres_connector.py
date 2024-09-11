import json
from typing import List

import psycopg2

from llm_agent.src.utils import Member

PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB_NAME = "postgres"
MEMBER_DATA_TTL = "1 day"
MEMBER_INFO_COLS = [
    "member_no",
    "name",
    "company",
    "title",
    "background",
    "company_url",
    "linkedin_url",
    "summary",
    "created_at",
    "updated_at",
    "versions"
]

CREATE_MEMBER_TABLE_QUERY = """
    CREATE TABLE IF NOT EXISTS member_info (
        member_no INT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        company VARCHAR(255),
        title VARCHAR(255),
        background TEXT,
        company_url TEXT,
        linkedin_url TEXT,
        summary TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        versions JSONB
    );
    """

INSERT_MEMBER_INFO_QUERY = """
         INSERT INTO member_info (member_no, name, company, title, background, company_url, linkedin_url, summary, versions)
         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
         ON CONFLICT (member_no) DO UPDATE
         SET name = EXCLUDED.name,
             company = EXCLUDED.company,
             title = EXCLUDED.title,
             background = EXCLUDED.background,
             company_url = EXCLUDED.company_url,
             linkedin_url = EXCLUDED.linkedin_url,
             summary = EXCLUDED.summary,
             versions = EXCLUDED.versions;
         """

# Database connection details
pg_config = {
    'host': PG_HOST,
    'port': PG_PORT,
    'database': PG_DB_NAME
}


class PostgresConnector:
    def __init__(self, db_config: dict = None):
        if db_config is None:
            db_config = pg_config
        self.db_config = db_config
        self._connect()

    def _connect(self):
        self.conn = psycopg2.connect(**self.db_config)
        self.cursor = self.conn.cursor()


    def create_table(self, query: str = CREATE_MEMBER_TABLE_QUERY):
        self.cursor.execute(query)

    def update_member_info(self, members: List[Member]):
        """ Update member info in the Postgres database
        Args:
            members (List[Member]): List of Member objects to update in the database
        """
        data = [(
            member.member_no,
            member.name,
            member.company,
            member.title,
            member.background,
            member.company_url,
            member.linkedin_url,
            member.summary,
            json.dumps(member.versions)
        ) for member in members]
        if data:
            self.cursor.executemany(INSERT_MEMBER_INFO_QUERY, data)
            self.conn.commit()
        else:
            print("No data to update.")

    def get_member_info_by_id(self, member_no: int, to_member_object: bool = False):
        select_query = """
        SELECT * FROM member_info WHERE member_no = %s;
        """
        self.cursor.execute(select_query, (member_no,))
        member_info = self.cursor.fetchall()
        return self._to_member(member_info) if to_member_object else member_info


    def _to_member(self, data: List[tuple]):
        res_dict = [{k: v for k,v in zip(MEMBER_INFO_COLS, i)} for i in data]
        res_member = [Member(**i) for i in res_dict]
        return res_member


    def get_new_member_info(self, version: str = 'v1', intervals: str = MEMBER_DATA_TTL):
        """ Get new member info from the Postgres database"""
        query = f"""
        SELECT *
        FROM member_info
        WHERE (versions -> '{version}' = 'true')
          AND (
                (created_at = updated_at)
                OR
                (updated_at + INTERVAL '{intervals}' < CURRENT_DATE)
              )
        ORDER BY member_no;
        """
        self.cursor.execute(query)
        member_info = self.cursor.fetchall()
        return self._to_member(member_info)


if __name__ == "__main__":
    pg_conn = PostgresConnector()
    pg_conn.create_table()

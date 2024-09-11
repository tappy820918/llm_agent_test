"""
The purpose of this script is to create a pipeline to update data to qdrant.
Steps:
1. Pull new data from postgres
    - `create_at` == `update_at`
    - `update_at`  - current time > 1 day
3. LLM get enhanced summary data (`data_enhanced.py`)
4. Insert data to qdrant with collection aligned to its version name as the `version` field

"""
import time

from tqdm import tqdm

from llm_agent.src._data_enhance_agent import agent_setup
from llm_agent.connectors.postgres_connector import PostgresConnector, MEMBER_DATA_TTL
from llm_agent.connectors.qdrant_connector import QdrantConnector


class UpdateLatestDataToQdrantFactory:
    def __init__(self,
                 version_: str = "v1",
                 pg_conn: PostgresConnector = None,
                 qdrant_conn: QdrantConnector = None,
                 ttl: str = MEMBER_DATA_TTL):
        if not pg_conn:
            self.pg_conn = PostgresConnector()
        if not qdrant_conn:
            self.qdrant_conn = QdrantConnector()
        self.version = version_
        self.ttl = ttl
        self.new_members = None

    def pg_get_latest_data(self):
        self.new_members = self.pg_conn.get_new_member_info(self.version,
                                                            intervals=self.ttl)

    def _llm_get_enhanced_summary_data(self):
        agent = agent_setup()
        results = []
        for member in tqdm(self.new_members):
            summarized_info = agent.summarized_with_enhanced_data(member)
            results.append(summarized_info)
            time.sleep(30)
        new_members_updated_summary = self.new_members
        for i in range(len(results)):
            new_members_updated_summary[i].summary = results[i]
        self.pg_conn.update_member_info(new_members_updated_summary)
        return new_members_updated_summary

    def update_latest_data_to_qdrant(self):
        pass


class UpdateLatestDataToQdrantV1(UpdateLatestDataToQdrantFactory):

    def __init__(self,
                 version_: str = "v1",
                 pg_conn: PostgresConnector = None,
                 qdrant_conn: QdrantConnector = None,
                 ttl: str = MEMBER_DATA_TTL):
        super().__init__(version_, pg_conn, qdrant_conn, ttl)

    def update_latest_data_to_qdrant(self, enhanced_data: bool = True):
        if self.version != 'v1':
            raise NotImplementedError("Only version v1 is supported")
        # 1. Pull new data from postgres
        self.pg_get_latest_data()
        # 2. LLM get enhanced summary data
        new_members_updated_summary = self._llm_get_enhanced_summary_data() if enhanced_data else self.new_members
        # 3. Update summary field and update it back to postgres
        self.pg_conn.update_member_info(new_members_updated_summary)
        # 4. Insert data to qdrant with collection aligned to its version name as the `version` field
        self.qdrant_conn.insert_members(new_members_updated_summary, version_to_vectorize='v1')

def update_latest_data_to_qdrant(version: str = "v1", enhanced_data: bool = False):
    update_latest_data_to_qdrant_v1 = UpdateLatestDataToQdrantV1(version_=version)
    update_latest_data_to_qdrant_v1.update_latest_data_to_qdrant(enhanced_data)

if __name__ == "__main__":
    update_latest_data_to_qdrant()
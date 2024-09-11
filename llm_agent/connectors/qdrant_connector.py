from typing import List, Optional, Dict, Union

from qdrant_client import QdrantClient
from qdrant_client.http.models import QueryResponse
from qdrant_client.models import VectorParams, Distance

from llm_agent.connectors.redis_connector import redis_member_ver_cache
from llm_agent.src.utils import Member

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
VECTOR_SIZE = 100
RETURN_TOP_K = 5
MEMBER_COLLECTION_PREFIX = "member_enhanced"

# Qdrant connection details
qdrant_config = {
    'host': QDRANT_HOST,
    'port': QDRANT_PORT
}



class QdrantConnector:
    """Qdrant connector class to insert and search members"""
    def __init__(self,
                 db_config: dict = None,
                 collection_prefix: str = MEMBER_COLLECTION_PREFIX):
        if not db_config:
            db_config = qdrant_config
        self.db_config = qdrant_config
        self.collection_prefix = collection_prefix
        self.client = QdrantClient(**db_config)

    def _create_collection(self,
                           collection_name: str,
                           vector_size: int = VECTOR_SIZE,
                           distance: Distance = Distance.COSINE):
        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance)
            )
            print(f"Collection {collection_name} created successfully")

    def _insert(self, collection: str,member_str: List[str], member_no: List[int]) -> None:
        # self._create_collection(collection_name=collection)
        self.client.add(
            collection_name=collection,
            documents=member_str,
            ids=member_no
        )

    def _search(self, member_str: str, version: str, return_top_k: int = RETURN_TOP_K) -> List[QueryResponse]:
        search_results = self.client.query(
            collection_name=self.collection_prefix + "_" + version,
            query_text=member_str,
            limit=return_top_k
        )
        return search_results

    def insert_members(self, members: List[Member], version_to_vectorize: Optional[str] = None) -> None:
        """Insert members into Qdrant

        Update different versions by `member.versions` flags (and validate the version flag is True).
        If `version_to_vectorize` is provided, only vectorize the specified version,
        otherwise, vectorize all versions.

        Args:
            members (List[Member]): List of members to insert
            version_to_vectorize (Optional[str], optional): Version to vectorize. Defaults to None.
        """
        # Update by members
        for member in members:
            member_str = member.summary
            if not member_str:
                member_str = f"Member info: {member.name} {member.company} {member.title} {member.background}"


            if version_to_vectorize:
                if member.versions.get(version_to_vectorize, False):
                    self._insert(self.collection_prefix + "_" + version_to_vectorize,
                                [member_str],
                                [member.member_no])
            else:
                for version, is_using in member.versions.items():
                    if is_using:
                        self._insert(self.collection_prefix + "_" + version,
                                    [member_str],
                                    [member.member_no])
        print(f"{len(members)} Members inserted successfully")

    @redis_member_ver_cache()
    def search_member(self, member: Member, version: str) -> List[QueryResponse]:
        member_str = member.summary
        if not member_str:
            member_str = f"{member.name} {member.company} {member.title} {member.background}"
        search_results = self._search(member_str, version=version)
        return search_results


    def search_members(self, members: List[Member], version_to_search: Optional[str] = None) -> Union[Dict[str, List[QueryResponse]], List]:
        search_results = []
        for member in members:
            if not version_to_search:
                versions = [version for version, is_using in member.versions.items() if is_using]
            else:
                versions = [version_to_search] if member.versions.get(version_to_search, False) else []
            res = {version: self.search_member(member, version) for version in versions} if versions else {}
            search_results.append(res)
        return search_results

    def delete_collection(self, collection_name: str):
        self.client.delete_collection(collection_name)
        print(f"Collection {collection_name} deleted successfully")

    def list_collections(self):
        res = self.client.get_collections().model_dump()['collections']
        res = [i['name'] for i in res]
        for i in res:
            print(i)
        return res


if __name__ == "__main__":
    data = Member(member_no=10,
                  name="ROBERT CANTRELL",
                  company="Strategy Innovators LLC",
                  title="Founder",
                  background="Well-studied in principles of inventing and technology evolution from which to account both for where the state-of-the-art is and where it will likely be. Teach innovation sciences across many technology disciplines. Bring added business perspective from an MBA and experience in direct sales and business development.",
                  company_url="https://www.strategyinnovators.com",
                  linkedin_url="https://www.linkedin.com/in/robert-cantrell-47675/",
                  versions={"v1": True, "v2": False},
                  summary="")

    qdrant_conn = QdrantConnector()
    # qdrant_conn.insert_members([data])
    toy_search_results = qdrant_conn.search_member(data, "v1")
    print(toy_search_results)

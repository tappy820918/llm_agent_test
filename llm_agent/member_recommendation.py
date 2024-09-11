"""Recommendation for members based on LLMagent data"""
from typing import List

from llm_agent.connectors.postgres_connector import PostgresConnector
from llm_agent.src.rerank import reranker_setup
from llm_agent.src.update_data_to_qdrant import UpdateLatestDataToQdrantV1
from llm_agent.src.utils import Member

def _format_result_pairs(member_no: int, results: dict):
    """Format the result"""
    res_dict = {"member_no": member_no,
                "matched_member_no": results['member_no'],
                "reason": results['reason'],
                "version": results['version']}
    return res_dict


def recommend_member_by_id(member_no: int,
                           version_to_search: str,
                           format_columns: bool = True):
    """Recommend members based on the given member_no"""
    pg_conn = PostgresConnector()
    member_data = pg_conn.get_member_info_by_id(member_no, to_member_object=True)
    print(member_data)
    reranker = reranker_setup()
    result = reranker.recommend(member_data[0], version_to_search)
    return _format_result_pairs(member_no, result) if format_columns else result


def create_member_rec_pairs(members: List[Member],
                            version_to_search: str,
                            format_columns: bool = True):
    """Recommend members based on the given member"""
    reranker = reranker_setup()
    results = []
    for member in members:
        result = reranker.recommend(member, version_to_search)
        results.append(result)
    if format_columns:
        results = [_format_result_pairs(i.member_no, j) for i,j in zip(members, results)]
    return results



if __name__ == "__main__":
    update_latest_data_to_qdrant_v1 = UpdateLatestDataToQdrantV1()
    update_latest_data_to_qdrant_v1.pg_get_latest_data()
    all_members = update_latest_data_to_qdrant_v1.new_members
    print(len(all_members))
    res = create_member_rec_pairs(all_members, "v1")
    print(res)
"""Reranker class for the LLM agent."""

import os
from typing import Dict

from langchain.output_parsers.json import SimpleJsonOutputParser
from langchain_core.prompts import PromptTemplate
from qdrant_client.http.models import QueryResponse

from llm_agent.connectors.qdrant_connector import QdrantConnector
from llm_agent.connectors.redis_connector import redis_member_ver_cache, redis_cache_pkl
from llm_agent.src.utils import Member, LlmType, load_prompt_template, ModelSetup

GEMINI_MODEL = "gemini-1.5-pro"
GEMINI_EMBEDDINGS_MODEL = "models/embedding-001"
DEFAULT_TEMPERATURE = 0
DEFAULT_GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", default=GOOGLE_API_KEY)

DEFAULT_PROMPT_VERSION = "1.0.0"
DEFAULT_PROMPT_PATH = "../llm_agent/prompts"

RERANK_PROMPT = load_prompt_template(filename="rerank_and_compare.yaml",
                                     path=DEFAULT_PROMPT_PATH,
                                     version=DEFAULT_PROMPT_VERSION)

DEFAULT_LLM = LlmType.GEMINI


def parse_message_to_dict(func):
    def json_parser(self, *args, **kwargs):
        parser = SimpleJsonOutputParser()
        result = func(self, *args, **kwargs)
        return parser.invoke(result)

    return json_parser


class LlmReranker:
    def __init__(self, chat_model, prompt: str = None):
        self.chat_model = chat_model
        if not prompt:
            prompt = RERANK_PROMPT
        self.rerank_prompt = prompt
        self.qdrant_conn = QdrantConnector()


    @parse_message_to_dict
    def rerank(self, similar_items: Dict[str, QueryResponse], target: Member, version: str = 'v1'):
        if not similar_items or not similar_items.get(version):
            print("No similar items found")
            return
        # Memberinfo
        target_dict = target.model_dump()
        target_list = [f'{k}: {v}' for k, v in target_dict.items() if (v and k != 'versions' and k != 'summary')]
        memberinfo_str = "## Member information\n" + '\t\n'.join(target_list)

        # Company websearch info
        candidate_info_str, candidate_nums = "", 1
        for similar_item in similar_items.get(version):
            member_no = similar_item.id
            summary = similar_item.document
            if member_no == target.member_no:
                continue
            candidate_info_str += (
                f"## Candidate {candidate_nums}: \n\t"
                f"- `member_no`: {member_no}\n\t"
                f"- `member_summary`: {summary}\n\n"
            )
            candidate_nums += 1

        recommendation_prompt = PromptTemplate(
            input_variables=["candidate_nums", "memberinfo_str", "candidate_info_str"],
            template=RERANK_PROMPT
        ).format(candidate_nums=candidate_nums,
                 memberinfo_str=memberinfo_str,
                 candidate_info_str=candidate_info_str)
        result = self.chat_model.invoke(recommendation_prompt)
        return result

    @redis_member_ver_cache()
    def recommend(self, target: Member, version: str):
        similar_items = self.qdrant_conn.search_members([target])
        result = self.rerank(similar_items[0], target, version)
        return {**result, **{'version': version}}

def reranker_setup():
    chat_model = ModelSetup(llm_type=LlmType.GEMINI,
                            model_params={"model": GEMINI_MODEL,
                                          "google_api_key": DEFAULT_GEMINI_API_KEY,
                                          "temperature": DEFAULT_TEMPERATURE})()
    return LlmReranker(chat_model)


if __name__ == "__main__":
    member_10 = Member(member_no=10,
                       name="ROBERT CANTRELL",
                       company="Strategy Innovators LLC",
                       title="Founder",
                       background="Well-studied in principles of inventing and technology evolution from which to account both for where the state-of-the-art is and where it will likely be. Teach innovation sciences across many technology disciplines. Bring added business perspective from an MBA and experience in direct sales and business development.",
                       company_url="https://www.strategyinnovators.com",
                       linkedin_url="https://www.linkedin.com/in/robert-cantrell-47675/",
                       versions={"v1": True, "v2": False},
                       summary="")
    reranker = reranker_setup()
    res = reranker.recommend(member_10, 'v1')
    print(res)

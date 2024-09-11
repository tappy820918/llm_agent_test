"""Create a API call(agent) for augmenting member information with web search data.
"""

import operator
import os
from typing import List, TypedDict, Annotated

from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.messages import ToolMessage, AnyMessage
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph

from llm_agent.src.utils import Member, LlmType, load_prompt_template, ModelSetup

GEMINI_MODEL = "gemini-1.5-pro"
GEMINI_EMBEDDINGS_MODEL = "models/embedding-001"
DEFAULT_TEMPERATURE = 0
DEFAULT_GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", default=GOOGLE_API_KEY)

DEFAULT_PROMPT_VERSION = "1.0.0"
DEFAULT_PROMPT_PATH = "../llm_agent/prompts"

DATA_ENHANCE_PROMPT = load_prompt_template(filename="data_enhance.yaml",
                                           path=DEFAULT_PROMPT_PATH,
                                           version=DEFAULT_PROMPT_VERSION)

DEFAULT_LLM = LlmType.GEMINI


class MemberInfoAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    memberinfo: Member
    system_message: str
    company_expand: bool
    linkedin_expand: bool


class MemberInfoEnhanceAgent:
    def __init__(self, chat_model, emb_model, search_tool):
        self.chat_model = chat_model
        self.emb_model = emb_model
        self.search_tool = search_tool
        self._build_graph()

    def _build_graph(self):
        graph = StateGraph(MemberInfoAgentState)
        graph.add_node("company_search", self._company_websearch)
        graph.add_node("linkedin_search", self._linkedin_websearch)
        graph.add_node("summarize", self._summarize)
        graph.add_edge("company_search", "linkedin_search")
        graph.add_edge("linkedin_search", "summarize")
        graph.set_entry_point("company_search")
        graph.set_finish_point("summarize")
        self.graph = graph.compile()  # Compile the graph

    def _company_websearch(self, state: MemberInfoAgentState):
        if state.get('company_expand') == False:
            return {'messages': [ToolMessage(content='', name='skip_tool', tool_call_id='company_websearch')]}
        memberinfo = state['memberinfo']
        query = f"Search for company information for company {memberinfo.company} with URL {memberinfo.company_url}."
        search_results = self.search_tool.invoke(
            {"args": {"query": query, "max_result": 5}, "id": "company_websearch", "name": self.search_tool.name,
             "type": "tool_call"})
        return {'messages': [search_results]}

    def _linkedin_websearch(self, state: MemberInfoAgentState):
        if state.get('company_expand') == False:
            return {'messages': [ToolMessage(content='', name='skip_tool', tool_call_id='linkedin_websearch')]}
        memberinfo = state.get('memberinfo')
        query = f"Search for linkedin profile for {memberinfo.name} with link {memberinfo.linkedin_url}"
        search_results = self.search_tool.invoke(
            {"args": {"query": query, "max_result": 5}, "id": "linkedin_websearch", "name": self.search_tool.name,
             "type": "tool_call"})
        return {'messages': [search_results]}

    def _summarize(self, state: MemberInfoAgentState):
        messages = state['messages']

        # Memberinfo
        memberinfo_str = "## Member information" + \
                         '\t\n'.join([f'{k}: {v}' for k, v in state['memberinfo'].model_dump().items() if v])

        # Company websearch info
        company_websearch_str = ""
        try:
            if state['messages'][0].content and state.get('company_expand'):
                company_websearch_str = "## Company url searched from the web:\n" + \
                                        str(state['messages'][0].content) + "\n"
        except:
            company_websearch_str = ""

        # Linkin websearch info
        linkedin_websearch_str = ""
        try:
            if state['messages'][1].content and state.get('linkedin_expand'):
                linkedin_websearch_str = "## Linkedin url searched from the web:\n" + \
                                         str(state['messages'][0].content) + \
                                         "\n"
        except:
            linkedin_websearch_str = ""

        summarized_prompt = PromptTemplate(
            input_variables=["memberinfo", "company_expand", "linkedin_expand"],
            template=state['system_message'],
        ).format(memberinfo=memberinfo_str, company_expand=company_websearch_str,
                 linkedin_expand=linkedin_websearch_str)

        result = self.chat_model.invoke(summarized_prompt)
        return {'messages': [summarized_prompt, result]}

    def summarized_with_enhanced_data(self,
                                      member: Member,
                                      default_prompt: str = DATA_ENHANCE_PROMPT,
                                      web_expand_company: bool = True,
                                      web_expand_linkedin: bool = True) -> str:
        """summarized_with_enhanced_data Enhance data information for searching the web using Duckduckgo search API
            1. Search for company Info given `company` & `company_url`
            2. Search for member linkedin profile given `linkedin_url`
            3. LLM summarize member info and company info
            4. Return the result

        Args:
            member (Member): member information
            default_prompt (str, optional): Prompt template. Defaults to PROMPT.
            web_expand_company (bool, optional): Expand company information. Defaults to True.
            web_expand_linkedin (bool, optional): Expand linkedin information. Defaults to True.

        Returns:
            str: summarized information
        """

        initial_state = {"messages": [],
                         "memberinfo": member,
                         "system_message": default_prompt,
                         "company_expand": web_expand_company,
                         "linkedin_expand": web_expand_linkedin}
        result = self.graph.invoke(initial_state)
        return result['messages'][-1].content

    def get_embedding(self, text: str) -> List[float]:
        """get_embedding Get the embedding of the text

        Args:
            text (str): text to be embedded

        Returns:
            List[float]: embedding of text
        """
        return self.emb_model.invoke(text)


def agent_setup():
    chat_model = ModelSetup(llm_type=LlmType.GEMINI,
                            model_params={"model": GEMINI_MODEL,
                                          "google_api_key": DEFAULT_GEMINI_API_KEY,
                                          "temperature": DEFAULT_TEMPERATURE})()
    emb_model = ModelSetup(llm_type=LlmType.GEMINI_EMBEDDINGS,
                           model_params={"model": GEMINI_EMBEDDINGS_MODEL,
                                         "google_api_key": DEFAULT_GEMINI_API_KEY})()

    search_tool = DuckDuckGoSearchResults()

    return MemberInfoEnhanceAgent(chat_model, emb_model, search_tool)


if __name__ == "__main__":
    from pathlib import Path
    current_working_directory = Path.cwd()
    print(current_working_directory)

    member_10 = Member(member_no=10,
                       name="ROBERT CANTRELL",
                       company="Strategy Innovators LLC",
                       title="Founder",
                       background="Well-studied in principles of inventing and technology evolution from which to account both for where the state-of-the-art is and where it will likely be. Teach innovation sciences across many technology disciplines. Bring added business perspective from an MBA and experience in direct sales and business development.",
                       company_url="https://www.strategyinnovators.com",
                       linkedin_url="https://www.linkedin.com/in/robert-cantrell-47675/",
                       versions={"v1": True, "v2": False},
                       summary="")

    initial_state = {"messages": [],
                     "memberinfo": member_10,
                     "system_message": DATA_ENHANCE_PROMPT,
                     "company_expand": True,
                     "linkedin_expand": False}

    agent = agent_setup()
    summarized_info = agent.summarized_with_enhanced_data(member_10, web_expand_company=True, web_expand_linkedin=False)
    print(summarized_info)

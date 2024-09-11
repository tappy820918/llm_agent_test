import os
from enum import Enum
from pathlib import Path
from typing import Optional, Dict

import yaml
from google import generativeai
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from pydantic import BaseModel, Field

PROMPT_PATH = "./llm_agent/prompts"
DEFAULT_GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", default=GOOGLE_API_KEY)


def load_prompt_template(filename: str,
                         path: str = PROMPT_PATH,
                         version: str = "1.0.0"):
    file_path = Path(path).joinpath(filename)
    with open(file_path, 'r') as f:
        prompt = yaml.safe_load(f)
    return prompt[version][0]['prompt']


class Member(BaseModel):
    member_no: int = Field(..., title="Member number")
    name: str = Field(..., title="Member name")
    company: str = Field("", title="Company name")
    title: str = Field("", title="Title")
    background: str = Field("", title="Background")
    company_url: str = Field("", title="Company URL")
    linkedin_url: str = Field("", title="Linkedin URL")
    versions: Dict[str, bool] = Field({"v1": True, "v2": False}, title="Versions used to store in Vector DB.")
    summary: Optional[str] = Field("", title="LLM Summary for the member with the enhanced information")


class LlmType(Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    GEMINI_EMBEDDINGS = "gemini_embeddings"


class ModelSetup:
    def __init__(self, llm_type: LlmType, model_params: dict):
        self.llm_type = llm_type
        self.model_params = model_params

    def create_model(self):
        if self.llm_type == LlmType.OPENAI:
            raise NotImplementedError

        if self.llm_type == LlmType.GEMINI:
            generativeai.configure(api_key=self.model_params.get("api_key", DEFAULT_GEMINI_API_KEY))
            return ChatGoogleGenerativeAI(**self.model_params)

        if self.llm_type == LlmType.GEMINI_EMBEDDINGS:
            generativeai.configure(api_key=self.model_params.get("api_key", DEFAULT_GEMINI_API_KEY))
            return GoogleGenerativeAIEmbeddings(**self.model_params)

    def __call__(self, *args, **kwargs):
        return self.create_model()

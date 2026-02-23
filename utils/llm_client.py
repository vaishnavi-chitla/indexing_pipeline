from langchain_openai import AzureChatOpenAI
import os
from dotenv import load_dotenv
load_dotenv()

llm = AzureChatOpenAI(
    deployment_name=os.getenv("AZURE_LLM_DEPLOYMENT"),
    model=os.getenv("AZURE_LLM_DEPLOYMENT"),
    openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    openai_api_version=os.getenv("OPENAI_API_VERSION"),
    temperature=0.2,
)


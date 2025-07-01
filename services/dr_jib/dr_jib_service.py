from shared.rag import RAG
from .tools import Tools
import openai
from openai.types.chat import ChatCompletion
import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_random_exponential
import logging
import re
import json
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(override=True)

class Config:
    # Use GPT-4.1-mini configuration like web agent
    API_KEY = os.getenv('GPT_MINI_API_KEY')
    ENDPOINT = os.getenv('GPT_MINI_ENDPOINT')
    API_VERSION = '2025-01-01-preview'
    MODEL = "gpt-4.1-mini"
    TOKENS_LIMIT = 4096

class DrJib:
    def __init__(self, global_storage):
        self.client = openai.AsyncAzureOpenAI(
            api_version=Config.API_VERSION,
            azure_endpoint=Config.ENDPOINT,
            api_key=Config.API_KEY,
        )
        self.rag = RAG(global_storage=global_storage)

        self._load_prompt_templates()
        self.tools = Tools()
        self.rag = RAG(global_storage=global_storage)

    def _load_prompt_templates(self):
        self.dr_jib_prompt = self._read_prompt_file('shared/rag/prompts/jib_prompt.txt')
    
    def _read_prompt_file(self, file_path: str) -> str:
        """
        Read the content of a prompt file.
        
        Args:
            file_path: Path to the prompt file
            
        Returns:
            Content of the file as a string
        """
        try:
            with open(file_path, 'r') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading prompt file {file_path}: {e}")
            return ""
        
    @retry(
        wait=wait_random_exponential(min=1, max=2),
        stop=stop_after_attempt(3),
    )
    async def tell_gpt(self, *args, **kwargs) -> ChatCompletion:
        return await self.client.chat.completions.create(*args, **kwargs)

    def extract_xml(self, text_resp, tag):
        """Extract content from XML-like tags in text."""
        pattern = f"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, text_resp, re.DOTALL)
        return match.group(1).strip() if match else None
    
    async def forward(self, chats, room_id):
        chats.insert(0, {"role": "system", "content": self.dr_jib_prompt})
        logger.info("Dr.Jib is thinking...")
        
        dr_jib_response = await self.tell_gpt(
            model=Config.MODEL,
            messages=chats,
            temperature=0.0,
            max_tokens=Config.TOKENS_LIMIT,
            n=1,
            tools=[self.tools.retrieval]
        )

        chat_resp = dr_jib_response.model_dump()
        print(chat_resp["choices"][0]["finish_reason"])
        print(chat_resp["choices"][0]["message"]['tool_calls'])
        response = chat_resp["choices"][0]["message"]["content"]

        if chat_resp["choices"][0]["finish_reason"] == "tool_calls":
            logger.info("Dr.Jib is calling tools...")
            tools_block = chat_resp["choices"][0]["message"]
            tool_calls = chat_resp["choices"][0]["message"]["tool_calls"]
            
            # Handle all tool calls
            tool_responses = []
            for tool_call in tool_calls:
                logger.info(f"Handling tool call {tool_call['id']}...")
                context = await self._handle_retrieval_single(tool_call)
                tool_responses.append({
                    "role": "tool",
                    "content": context,
                    "tool_call_id": tool_call['id']
                })
            
            # Add the assistant's message with tool calls
            chats.append(tools_block)
            # Add all tool responses
            chats.extend(tool_responses)
            
            return await self.forward(chats, room_id)

        else:
            logger.info("Dr.Jib is providing response...")
            logger.info(response)
            if "<think>" not in response or "</think>" not in response:
                return response
            response_text = self.extract_xml(response, "response")
            if response_text:
                return response_text
            else:
                logger.info("Dr.Jib is fixing response...")
                fixed_response = await self.tell_gpt(
                    model=Config.MODEL,
                    messages=[
                        {"role": "user", "content": response},
                        {"role": "system", "content": """ 
You are a helpful assistant that will get a response from LLM with or without XML tags of <thought> and <response>.
If the response is not in the XML tags, please extract the response from the LLM response and return it. includes all the response if it's abiguous which part is the thought and which part is the response and always include the disclaimer message at the end that delimet with ---.
If the response is in the XML tags, please return the response inside the <response> tags.
                     
Do not return any other text than the response, just the response.
"""}
                    ],
                    temperature=0.0,
                    max_tokens=Config.TOKENS_LIMIT,
                    n=1,
                )
                return fixed_response.model_dump()["choices"][0]["message"]["content"]

    # New helper method to handle single tool call
    async def _handle_retrieval_single(self, tool_call):
        logger.info("Dr.Jib is retrieving information...")
        arguments = json.loads(tool_call['function']['arguments'])
        context = self.rag._get_package_url(
            query=arguments['query'], 
            preferred_area=arguments['preferred_area'],
            radius=10,  # Default radius
            category_tag=arguments['category_tag']
        )
        return context
        
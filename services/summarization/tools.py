import json

from openai.types.chat import (
    ChatCompletion,
    ChatCompletionToolParam,
)

def build_package_query_function() -> list[ChatCompletionToolParam]:
    return [
        {
            "type": "function",
            "function": {
                "name": "language_detector",
                "description": """
                    This function is triggered to find out what language the user's query is in.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "language": {
                            "description": """
                            Language used by the user based on the message.
                            """,
                        }
                    },              
                },
            },
        }
    ]

def is_language_detector(chat_completion: ChatCompletion):
    response_message = chat_completion.choices[0].message
    if response_message.tool_calls:
        for tool in response_message.tool_calls:
            if tool.type == "function" and tool.function.name == "language_detector":
                return True
    return False

def extract_language(chat_completion: ChatCompletion):
    response_message = chat_completion.choices[0].message
    language = None

    if response_message.tool_calls:
        for tool in response_message.tool_calls:
            if tool.type != "function":
                continue
            function = tool.function
            if function.name == "language_detector":
                arg = json.loads(function.arguments)
                language = arg.get("language")

    return language

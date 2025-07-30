from typing import Any, Union, Dict, List

from pydantic import BaseModel


class TextContent(BaseModel):
    type: str
    text: str


class ImageUrl(BaseModel):
    url: str
    detail: str = "auto"


class ImageContent(BaseModel):
    type: str
    image_url: ImageUrl


class ImageSource(BaseModel):
    type: str  # "url" or "base64"
    url: Union[str, None] = None  # for URL type only
    media_type: Union[str, None] = None  # for base64 type only
    data: Union[str, None] = None  # for base64 type only
    
    class Config:
        # Exclude None values when serializing to avoid sending unwanted fields to Claude
        exclude_none = True


class ClaudeImageContent(BaseModel):
    type: str
    source: ImageSource


class Message(BaseModel):
    role: str = "user"
    content: Union[str, List[Union[TextContent, ImageContent, ClaudeImageContent, Dict[str, Any]]]]


class ChatRequest(BaseModel):
    messages: List[Message]
    context: Dict = {}
    room_id: str
    device: str  

class ThoughtStep(BaseModel):
    title: str
    description: Any
    props: Dict = {}

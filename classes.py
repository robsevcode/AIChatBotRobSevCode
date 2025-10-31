from pydantic import BaseModel

# ------------------------
# Classes
# ------------------------

class Metadata(BaseModel):
    character_name: str
    system_prompt: str
    avatar_path: str
    last_updated: str

class LastChat(BaseModel):
    character_name: str
    
class Message(BaseModel):
    role: str
    content: object

class Chat(BaseModel):
    history: list[Message] = []
    timestamp: str = ""
    timestamp: str = ""

class Payload(BaseModel):
    messages: list[Message] = []
    model: str
    stream: bool = True

class MessageContentMedia(BaseModel):
    type: str
    path: object
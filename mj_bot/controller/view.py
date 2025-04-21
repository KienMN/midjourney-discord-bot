from pydantic import BaseModel, ConfigDict, model_validator


class DiscordChannelAction(BaseModel):
    channel_url: str


class DiscordBotCommandAction(BaseModel):
    command: str
    chat_message_placeholder: str


class DiscordMidjourneyPromptAction(BaseModel):
    prompt: str


class DiscordMidjourneyImageOutput(BaseModel):
    prompt: str
    sequence_number: int
    output_dir: str

class WaitAction(BaseModel):
    seconds: int
    range_: int = 10


class NoParamsAction(BaseModel):
    """
    Accepts absolutely anything in the incoming data
    and discards it, so the final parsed model is empty.
    """

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    def ignore_all_inputs(cls, values):
        # No matter what the user sends, discard it and return empty.
        return {}

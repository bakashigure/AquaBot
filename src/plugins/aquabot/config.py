from pydantic import BaseSettings

class Config(BaseSettings):
    plugin_settings:str ="default"

    class Config:
        extra = "ignore"
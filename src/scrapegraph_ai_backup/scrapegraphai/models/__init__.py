"""
This module contains the model definitions used in the ScrapeGraphAI application.
"""

from .deepseek import DeepSeek
from .oneapi import OneApi
from .openai_itt import OpenAIImageToText
from .openai_tts import OpenAITextToSpeech

__all__ = [
    "DeepSeek",
    "OneApi",
    "OpenAIImageToText",
    "OpenAITextToSpeech",
]

# xtts_patch.py
import torch
from TTS.tts.configs.xtts_config import XttsConfig

def safe_load():
    torch.serialization.add_safe_globals([XttsConfig])
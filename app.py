# # app.py
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from whisper_wrapper import WhisperWrapper
# import os
#
# app = FastAPI()
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["GET", "POST"],
#     allow_headers=["*"],
#     allow_credentials=True,
#     expose_headers=["Content-Disposition"],
# )
#
# # Initialize whisper wrapper
# whisper = WhisperWrapper(model_size='base')
#
# @app.post('/transcribe')
# async def transcriptions(audio_filename):
#     try:
#         upload_name = os.path.abspath(audio_filename)
#         return whisper.transcribe_with_timestamps(upload_name)
#     except Exception as e:
#         print(f"Transcription error: {str(e)}")
#         raise
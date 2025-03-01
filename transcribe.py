# import whisper
# from tqdm_decorator import with_tqdm
# import json
#
# @with_tqdm
# def transcribe_audio(filename):
#     model = whisper.load_model("tiny").to("cuda")
#     result = model.transcribe(f"{filename}")
#     result_text_file_name = f"{filename.split('/')[-2]}/transcript"
#     with open(f"./data/youtube/{result_text_file_name}.txt", "w", encoding="utf-8") as file:
#         file.write(result["text"]+"\n")
#
#     segments_list = []
#     for segment in result['segments']:
#         id = segment["id"]
#         start = segment["start"]
#         end = segment["end"]
#         text = segment["text"]
#         segments_list.append(
#             {
#                 "id": id,
#                 "start": start,
#                 "end": end,
#                 "text": text
#             }
#         )
#     with open(f"./data/youtube/{result_text_file_name}.json", "w") as file:
#         json.dump(segments_list, file, indent=4)
#
#     return f"./data/youtube/{result_text_file_name}"
#
# if __name__ == "__main__":
#     from youtube import Youtube
#
#     url = input("enter yt url to transcribe:")
#     yt = Youtube()
#     filename, length = yt.download_audio_from_url(url)
#     result_text_file_name = transcribe_audio(filename)
#     print(result_text_file_name)
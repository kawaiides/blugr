import requests
import json


def test_video_processing():
    url = "http://54.234.20.80:8000/process-video"
    payload = {
        "url": "https://www.youtube.com/watch?v=nf6UIJk1NOI"
    }

    response = requests.post(url, json=payload)
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    test_video_processing()
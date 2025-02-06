from io import StringIO, BytesIO
import json
import requests
from langchain.chains.base import Chain
from pydantic import BaseModel, Field
from PIL import Image
import base64
import pandas as pd
import streamlit as st

class HuggingFaceAPIChain(Chain, BaseModel):
    api_url: str = Field(...)
    api_headers: dict = Field(...)

    def _call(self, inputs: dict) -> dict:
        prompt = inputs["input"]
        payload = {"inputs": prompt}
        response = requests.post(self.api_url, headers=self.api_headers, json=payload, stream=True)

        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "image" in content_type:
                return {"output": response.content}
            else:
                json_response = response.json()[0]
                generated_text = json_response.get("generated_text")
                summary_text = json_response.get("summary_text")
                if generated_text:
                    return {"output": generated_text}
                elif summary_text:
                    return {"output": summary_text}
        else:
            raise Exception(f"Ошибка API Hugging Face: {response.status_code}")

    @property
    def input_keys(self):
        return ["input"]

    @property
    def output_keys(self):
        return ["output"]
    
# Обработка image файлов
def resize_image(image_bytes, target_height):
    image = Image.open(BytesIO(image_bytes))
    aspect_ratio = image.width / image.height
    new_width = int(target_height * aspect_ratio)
    return image.resize((new_width, target_height))

def bytes_to_base64(image_bytes):
    encoded_string=  base64.b64encode(image_bytes).decode("utf-8")
    return "data:image/jpeg;base64," + encoded_string

def base64_to_bytes(base64_string):
    if base64_string.startswith("data:image/jpeg;base64,"):
        base64_string = base64_string[len("data:image/jpeg;base64,"):]
    image_bytes = base64.b64decode(base64_string)
    return image_bytes

# Обработка других типов файлов полученных из json
@st.cache_data
def download_file(file_url):
    response = requests.get(file_url)
    response.raise_for_status()
    return response.content

@st.cache_data
def process_csv(content):
    df = pd.read_csv(StringIO(content.decode('utf-8')))
    return df

def process_file_from_json(file_data):
    file_type = file_data["type"]
    file_name = file_data["name"]
    file_url = file_data["file_url"]

    try:
        file_content = download_file(file_url)

        if file_type == "txt":
            buffer = BytesIO(file_content)
            buffer.seek(0)

            st.download_button(
                label="Скачать TXT",
                data=buffer,
                file_name=file_name,
                mime="text/plain"
            )

        elif file_type == "docx":
            buffer = BytesIO(file_content)
            buffer.seek(0)

            st.download_button(
                label="Скачать DOCX",
                data=buffer,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        elif file_type == "pdf":
            buffer = BytesIO(file_content)
            buffer.seek(0)

            st.download_button(
                label="Скачать PDF",
                data=buffer,
                file_name=file_name,
                mime="application/pdf"
            )

        elif file_type == "csv":
            st.dataframe(process_csv(file_content) )

        elif file_type == "json":
            json_data = json.loads(file_content)
            st.json(json_data)
            
            buffer = BytesIO(file_content)
            buffer.seek(0)

            st.download_button(
                label="Скачать JSON",
                data=buffer,
                file_name=file_name,
                mime="application/json"
            )

        elif file_type == "xlsx":
            buffer = BytesIO(file_content)
            buffer.seek(0)

            st.download_button(
                label="Скачать XLSX",
                data=buffer,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка при скачивании файла: {e}")
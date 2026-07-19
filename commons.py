import streamlit as st
from PIL import Image
from io import BytesIO
import base64
import re
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Clientes de API
client_openrouter = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)
client_deepseek = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

def resize_image_for_api(img: Image.Image, max_width=512):
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def normalizar_clave(texto):
    texto = texto.lower()
    texto = re.sub(r'\(.*?\)', '', texto)
    texto = re.sub(r'[^a-záéíóúñü]+', '_', texto)
    texto = re.sub(r'_+', '_', texto)
    return texto.strip('_')

def copy_button(text):
    escaped = text.replace("`", "\\`").replace("$", "\\$")
    html = f"""
    <button onclick="
        var txt = `{escaped}`;
        if (navigator.clipboard) {{
            navigator.clipboard.writeText(txt).then(function() {{
                this.innerHTML = '✅ Copiado';
                setTimeout(()=>{{ this.innerHTML = '📋 Copiar'; }}, 2000);
            }}.bind(this));
        }} else {{
            var el = document.createElement('textarea');
            el.value = txt;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            this.innerHTML = '✅ Copiado';
            setTimeout(()=>{{ this.innerHTML = '📋 Copiar'; }}, 2000);
        }}
    " style="
        background: linear-gradient(135deg, #FF6B6B, #FF8E8E);
        color: white; border: none; padding: 5px 15px;
        border-radius: 20px; cursor: pointer; font-size: 13px;
        font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: all 0.2s;
    ">📋 Copiar</button>
    """
    st.components.v1.html(html, height=40)

import json
import streamlit as st
from commons import client_openrouter, client_deepseek, resize_image_for_api

ESPEJO_SYSTEM_PROMPT = """Eres 'El Espejo', el estilista digital de Gym Social. Analizas el perfil de un usuario (capturas de Instagram o Tinder) y generas un diagnóstico claro, útil y motivador para mejorar su primera impresión.

## LO QUE RECIBIRÁS
- Una o varias descripciones de imágenes del perfil (bio, fotos, destacadas).

## FORMATO DE SALIDA (JSON)
{
  "puntuacion_general": 75,
  "analisis_fotos": [
    "Foto 1: descripción y qué transmite (positivo/negativo)",
    "Foto 2: ..."
  ],
  "evaluacion_bio": "¿Es genérica? ¿Tiene gancho? ¿Invita a conversar?",
  "consejos_estilo": "Paleta de colores, tipo de fotos, orden de la cuadrícula.",
  "mision_diaria": "UNA sola acción concreta para hoy, personalizada y motivadora. Máximo 2 frases."
}

## REGLAS
- Sé honesto pero amable. Tu objetivo es que el usuario mejore, no que se sienta mal.
- La misión diaria debe ser específica, realizable en 5 minutos y adaptada a lo que viste en las imágenes.
- Usa español latino neutro.
- Devuelve SOLO el JSON, sin markdown."""

def analizar_imagen_perfil(image):
    """Obtiene una descripción textual de una imagen del perfil usando Qwen3-VL."""
    image_data = resize_image_for_api(image)
    prompt = "Describe brevemente qué ves en esta imagen de perfil de Instagram/Tinder: tipo de foto (selfie, paisaje, con amigos), qué transmite, colores dominantes y texto visible (bio, nombre, etc.). Sé conciso."

    response = client_openrouter.chat.completions.create(
        model="qwen/qwen3-vl-32b-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
            ]
        }],
        temperature=0,
        max_tokens=300
    )
    return response.choices[0].message.content.strip()


def generar_auditoria(descripciones, contexto=""):
    """Envía las descripciones de las imágenes a DeepSeek y obtiene el informe JSON."""
    texto_descripciones = "\n".join([f"Imagen {i+1}: {desc}" for i, desc in enumerate(descripciones)])
    mensaje_usuario = f"Descripciones del perfil:\n{texto_descripciones}"
    if contexto:
        mensaje_usuario += f"\n\nContexto adicional del usuario: {contexto}"

    for intento in range(2):
        response = client_deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": ESPEJO_SYSTEM_PROMPT},
                {"role": "user", "content": mensaje_usuario}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        resultado = response.choices[0].message.content.strip()
        if resultado.startswith("```json"): resultado = resultado[7:]
        elif resultado.startswith("```"): resultado = resultado[3:]
        if resultado.endswith("```"): resultado = resultado[:-3]

        try:
            return json.loads(resultado)
        except json.JSONDecodeError:
            ultimo_cierre = resultado.rfind('}')
            if ultimo_cierre != -1:
                try:
                    return json.loads(resultado[:ultimo_cierre+1])
                except json.JSONDecodeError:
                    pass
            if intento == 1:
                st.error("❌ El Espejo recibió un formato inválido dos veces. Por favor, inténtalo de nuevo.")
                return None
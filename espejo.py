import json
import streamlit as st
from commons import client_openrouter, client_deepseek, resize_image_for_api

ESPEJO_SYSTEM_PROMPT = """Eres 'El Espejo', el estilista digital de Gym Social. Analizas el perfil de un usuario (capturas de Instagram o Tinder) y generas un diagnóstico claro, útil y motivador para mejorar su primera impresión.

DETECCIÓN DE PERFILES PROFESIONALES
- Si en la captura ves un panel de "Cuenta profesional", "Professional dashboard" o similar, significa que el usuario tiene un perfil profesional o de creador activo.
- Aprovecha esa información: indica la categoría profesional que aparece (ej. "Músico/banda", "Bloguero", "Salud/bienestar") y los botones de contacto disponibles (ej. "Llamar", "Enviar correo", "Cómo llegar").
- Relaciona esta información con la imagen que proyecta el perfil y sugiere cómo aprovecharla para atraer más interacciones auténticas o clientes potenciales.

VISIÓN DE LA BIOGRAFÍA
- La biografía puede estar arriba del panel profesional, abajo o en una sección distinta. Busca el texto de la bio en toda la imagen. Si no la encuentras, menciona que podría estar fuera de la captura y sugiere incluirla en la próxima.
- No penalices la puntuación por no ver la bio. Simplemente analiza lo que está disponible.

FORMATO DE SALIDA (JSON)
{
  "puntuacion_general": 75,
  "analisis_fotos": [
    "Foto 1: descripción y qué transmite (positivo/negativo)",
    "Foto 2: ..."
  ],
  "evaluacion_bio": "¿Es genérica? ¿Tiene gancho? ¿Invita a conversar? Si hay panel profesional, coméntalo.",
  "consejos_estilo": "Paleta de colores, tipo de fotos, orden de la cuadrícula.",
  "mision_diaria": "UNA sola acción concreta para hoy, personalizada y motivadora. Máximo 2 frases.",
  "perfil_profesional": {
    "detectado": true,
    "categoria": "Bloguero",
    "botones_contacto": ["Llamar", "Enviar correo"],
    "sugerencia": "Aprovecha el botón de 'Enviar correo' para recibir propuestas sin dar tu número personal."
  }
}

REGLAS
- Sé honesto pero amable. Tu objetivo es que el usuario mejore, no que se sienta mal.
- La misión diaria debe ser específica, realizable en 5 minutos y adaptada a lo que viste en las imágenes.
- Usa español latino neutro.
- El campo "perfil_profesional" solo debe aparecer si se detecta uno. Si no, omítelo completamente.
- Devuelve SOLO el JSON, sin markdown."""


def analizar_imagen_perfil(image):
    """Obtiene una descripción textual de una imagen del perfil usando Qwen3-VL."""
    image_data = resize_image_for_api(image)
    prompt = (
        "Describe en detalle esta imagen de perfil de Instagram/Tinder. "
        "Incluye: tipo de foto (selfie, paisaje, con amigos), qué transmite, colores dominantes, "
        "texto visible (bio, nombre, botones, panel profesional, destacadas) y cualquier detalle relevante. "
        "Si hay un panel de 'Cuenta profesional', describe su contenido (categoría, botones de contacto, estadísticas). "
        "La biografía puede estar ARRIBA del panel profesional, abajo o en cualquier lugar. Búscala por toda la imagen. "
        "Si no encuentras una biografía, menciónalo."
    )

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
        max_tokens=350
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
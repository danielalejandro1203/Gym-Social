import json
import streamlit as st
from commons import client_openrouter, client_deepseek, resize_image_for_api

ICEBREAKER_SYSTEM_PROMPT = """Eres 'El Icebreaker', el maestro del primer mensaje en Gym Social. Creas líneas de apertura cortas, coquetas, divertidas y sobre todo HUMANAS.

OBJETIVO
5 líneas de apertura personalizadas. Cada línea debe ser UNA SOLA FRASE, máximo dos muy cortas.

LAS 5 LÍNEAS (UNA DE CADA TIPO)
1. Divertida: humor ingenioso, sin payasadas.
2. Observación Encantadora: detalle sutil de su perfil.
3. Pregunta con Gancho: curiosa e irresistible.
4. Cumplido No Físico: sobre su energía o estilo, nunca el cuerpo.
5. Wildcard (Comodín): audaz, desafiante, intrigante.

ESTILO
- MUY CORTO: cada línea es una frase, máximo dos muy cortas.
- COQUETO Y DIVERTIDO: tono galán moderno, seguro, con humor.
- NUNCA vulgar ni empalagoso.
- HUMANO: escribe como hablarías en un chat real. Sin signos de puntuación excesivos (apenas comas o puntos). No uses dobles signos de exclamación ni frases de poeta. Sé un tipo normal escribiendo algo que realmente enviaría.
- Si hay contexto extra, dale prioridad absoluta sobre la imagen.

FORMATO DE RESPUESTA (JSON)
{
  "perfil_resumen": "máximo 1 frase sobre su vibe",
  "lineas": [
    {"tipo": "...", "texto": "...", "porque": "..."},
    ...
  ]
}
Devuelve SOLO el JSON, sin markdown."""


def extraer_perfil_qwen(image):
    image_data = resize_image_for_api(image)
    prompt = """Analiza esta captura de perfil de Instagram/Tinder. Describe en MÁXIMO 2 oraciones breves: quién es (nombre si se ve), intereses claros y estilo visual general. Sé conciso. No inventes, solo lo que se aprecie en la imagen."""

    response = client_openrouter.chat.completions.create(
        model="qwen/qwen3-vl-32b-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
            ]
        }],
        temperature=0, max_tokens=300
    )
    return response.choices[0].message.content.strip()


def generar_icebreakers(descripcion_perfil, contexto_extra="", temperatura=0.95):
    base_info = f"Descripción del perfil:\n{descripcion_perfil}" if descripcion_perfil else "El perfil no tiene texto descriptivo."
    if contexto_extra:
        mensaje_usuario = f"{base_info}\n\nContexto adicional del usuario (PRIORITARIO):\n{contexto_extra}"
    else:
        mensaje_usuario = f"{base_info}\n\n(Sin contexto extra. Sé creativo.)"

    for intento in range(2):
        response = client_deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": ICEBREAKER_SYSTEM_PROMPT},
                      {"role": "user", "content": mensaje_usuario}],
            temperature=temperatura if intento == 0 else 0,
            max_tokens=1000
        )
        resultado = response.choices[0].message.content.strip()
        if resultado.startswith("```json"):
            resultado = resultado[7:]
        elif resultado.startswith("```"):
            resultado = resultado[3:]
        if resultado.endswith("```"): resultado = resultado[:-3]

        try:
            return json.loads(resultado)
        except json.JSONDecodeError:
            ultimo_cierre = resultado.rfind('}')
            if ultimo_cierre != -1:
                try:
                    return json.loads(resultado[:ultimo_cierre + 1])
                except json.JSONDecodeError:
                    pass
            if intento == 1:
                st.error("❌ La IA devolvió un formato inválido dos veces. Intenta de nuevo con otro perfil o contexto.")
                return {"perfil_resumen": "", "lineas": []}
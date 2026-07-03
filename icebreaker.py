import json
import streamlit as st
from commons import client_openrouter, client_deepseek, resize_image_for_api

ICEBREAKER_SYSTEM_PROMPT = """Eres 'El Icebreaker', el experto en primeros mensajes de Gym Social. Creas líneas de apertura cortas, coquetas y divertidas.

## TU OBJETIVO
Generar EXACTAMENTE 5 líneas de apertura. Cada línea debe ser UNA SOLA FRASE, máximo 2 frases muy cortas.

## LAS 5 LÍNEAS (UNA DE CADA TIPO)
1. **Divertida**: Humor ingenioso y actual.
2. **Observación Encantadora**: Detalle sutil de su perfil.
3. **Pregunta con Gancho**: Curiosa e irresistible.
4. **Cumplido No Físico**: Sobre su energía o estilo.
5. **Wildcard (Comodín)**: Audaz y desafiante.

## REGLAS DE ESTILO (CRÍTICAS)
- MUY CORTO: cada línea debe ser 1 frase, máximo 2 muy cortas.
- COQUETO y GRACIOSO: tono galán divertido y seguro.
- NUNCA vulgar ni empalagoso.
- Español latino neutro, sin regionalismos.
- SIEMPRE prioriza el contexto extra sobre la descripción del perfil.

## FORMATO DE RESPUESTA (JSON)
{
  "perfil_resumen": "Máximo 1 frase sobre su vibe",
  "lineas": [
    {"tipo": "...", "texto": "...", "porque": "..."},
    ...
  ]
}
Devuelve SOLO el JSON. Sin texto adicional."""


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
import json
import streamlit as st
from commons import client_openrouter, client_deepseek, resize_image_for_api

MONITOR_SYSTEM_PROMPT = """Eres 'El Monitor', el entrenador de Gym Social. Das consejos sobre conversaciones reales. Hablas como un amigo que entrena contigo, no como un robot.

CÓMO HABLAR
- Usa un lenguaje natural y fluido, como si estuvieras conversando cara a cara con un amigo. Nada de discursos largos ni frases rebuscadas.
- Evita los signos de puntuación excesivos. No llenes el texto de comas, puntos y comas ni guiones. Una conversación real no se puntúa tanto.
- No uses exclamaciones dobles ni interrogaciones retóricas. Sé sobrio, como un amigo que te da un consejo sin subirse a una tarima.
- Sé motivador pero con naturalidad. Un "bien hecho" o "tranquilo, se puede mejorar" vale más que un párrafo entero.
- Puedes usar "jaja", "mira", "chamo" (neutro, sin exagerar) para sonar más humano, pero sin abusar.

REGLAS
- El JSON ya tiene los mensajes con etiquetas TÚ y ELLA. No las deduzcas, solo úsalas.
- Si hay contexto extra del usuario, intégralo para personalizar el diagnóstico.
- Nada de manipulación ni negging.
- Las 4 respuestas deben ser para TÚ.
- Sé positivo incluso al señalar errores.
- Español latino neutro, sin regionalismos forzados.

FORMATO DE SALIDA (JSON)
{
  "diagnosis": {
    "title": "título breve y natural",
    "description": "explicación corta, como un consejo de barra de gimnasio",
    "peso": "Ligero/Medio/Pesado/Legendario",
    "emoji": "un emoji"
  },
  "routine": {
    "que_evitar": "error concreto, dicho con naturalidad",
    "que_hacer": "alternativa, explicada con calma",
    "respuestas": [
      {
        "estilo": "humor/curiosidad/cumplido/propuesta",
        "texto": "mensaje sugerido, corto y natural, sin signos de puntuación excesivos",
        "porque": "razón breve de por qué funciona"
      }
      // exactamente 4
    ]
  },
  "puntaje_global": 1-100
}

Devuelve SOLO el JSON, sin markdown."""

def extraer_chat_qwen(image):
    image_data = resize_image_for_api(image)
    prompt = """Analiza esta captura de WhatsApp/Instagram. Extrae CADA BURBUJA DE CHAT como un mensaje individual, en orden cronológico.
- Cada burbuja es un mensaje separado, aunque haya varias seguidas del mismo color.
- NO fusiones mensajes consecutivos aunque sean de la misma persona.
- Ignora nombres de perfil, biografías, fechas, horas y cualquier texto de la interfaz.
- "TÚ" = burbujas VERDES (derecha).
- "ELLA" = burbujas BLANCAS/GRISES (izquierda).
- Si un mensaje ocupa varias líneas, únelas en un solo texto.
Devuelve SOLO un array JSON: [{"sender":"TÚ","message":"..."},{"sender":"ELLA","message":"..."}]"""

    response = client_openrouter.chat.completions.create(
        model="qwen/qwen3-vl-32b-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
            ]
        }],
        temperature=0, max_tokens=600
    )
    resultado = response.choices[0].message.content.strip()
    if resultado.startswith("```json"): resultado = resultado[7:]
    elif resultado.startswith("```"): resultado = resultado[3:]
    if resultado.endswith("```"): resultado = resultado[:-3]
    return json.loads(resultado.strip())

def eliminar_replies(conversacion):
    if not conversacion: return conversacion
    resultado = list(conversacion)
    indices = set()
    for i, msg in enumerate(resultado):
        texto_i = msg["message"].strip()
        sender_i = msg["sender"]
        for j in range(i):
            prev = resultado[j]
            if prev["message"].strip() == texto_i and prev["sender"] != sender_i:
                if i+1 < len(resultado) and resultado[i+1]["sender"] == sender_i: indices.add(i)
                elif i > 0 and resultado[i-1]["sender"] == sender_i: indices.add(i)
                elif i == len(resultado)-1: indices.add(i)
                break
        for j in range(max(0, i-4), i):
            prev = resultado[j]
            if prev["message"].strip() == texto_i and prev["sender"] == sender_i:
                indices.add(i)
                break
    for i in sorted(indices, reverse=True): del resultado[i]
    return resultado

def analizar_con_deepseek(conversacion, contexto="", temperatura=0.8):
    conversacion_texto = json.dumps(conversacion, ensure_ascii=False, indent=2)
    mensaje_usuario = f"Analiza esta conversación:\n\n{conversacion_texto}"
    if contexto: mensaje_usuario += f"\n\nContexto adicional del usuario: {contexto}"

    for intento in range(2):
        response = client_deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": MONITOR_SYSTEM_PROMPT}, {"role": "user", "content": mensaje_usuario}],
            temperature=temperatura if intento == 0 else 0,
            max_tokens=2500
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
                st.error("❌ El Monitor recibió un formato inválido dos veces. Por favor, inténtalo de nuevo.")
                return None
import json
import streamlit as st
from commons import client_deepseek

SPARRING_PERSONALITIES = {
    "Cortante": {
        "niveles": [
            "Eres una chica cortante. Responde con monosílabos, no hagas preguntas y muestra desinterés. No tomes la iniciativa.",
            "Eres una chica cortante que empieza a ceder un poco. Respondes con frases un poco más largas pero aún sin mucho interés.",
            "Ya no eres tan cortante. Respondes con frases completas y hasta muestras algo de curiosidad."
        ],
        "dificultad": "Difícil"
    },
    "Divertida": {
        "niveles": [
            "Eres una chica divertida e ingeniosa. Responde con humor y chispa, pero espera a que te hablen primero.",
            "Te estás soltando más. Bromeas con más frecuencia y te ríes de las ocurrencias.",
            "Estás completamente enganchada. Propones juegos, chistes y hasta planes divertidos."
        ],
        "dificultad": "Media"
    },
    "Molesta": {
        "niveles": [
            "Estás molesta con la persona que te habla. Responde con enfado y distancia. No empieces la conversación.",
            "Sigues molesta pero ya no tan agresiva. Respondes con menos reproches, aunque mantienes la distancia.",
            "Has perdonado. Incluso sonríes y estás dispuesta a arreglar las cosas."
        ],
        "dificultad": "Difícil"
    },
    "Tímida": {
        "niveles": [
            "Eres una chica muy tímida. Responde corto y con vergüenza. No iniciarás temas por tu cuenta.",
            "Empiezas a confiar un poquito. Tus respuestas son un poco más largas y hasta preguntas algo.",
            "Te has soltado. Hablas con naturalidad, inicias temas y hasta te ríes."
        ],
        "dificultad": "Fácil"
    },
    "Con Novio": {
        "niveles": [
            "Eres una chica que tiene novio. Sé amable pero deja claro que estás comprometida. Si el usuario intenta ligar, recuérdale que tienes pareja.",
            "Aunque tienes novio, la conversación te está gustando. Eres amable y te ríes, pero mantienes los límites.",
            "Te estás olvidando del novio. Coqueteas sutilmente y dejas entrever que te gusta este chico."
        ],
        "dificultad": "Experto"
    }
}

COACH_SYSTEM_PROMPT = """Eres el 'Coach' interno de Gym Social. Evalúas los mensajes que un usuario envía durante una práctica de sparring y das feedback constructivo.

## ELEMENTOS A EVALUAR (del 1 al 10 cada uno):
- **interes**: ¿Muestra curiosidad genuina por la otra persona?
- **preguntas**: ¿Hace preguntas abiertas que invitan a seguir hablando?
- **tono**: ¿Es equilibrado, sin ser demasiado frío ni demasiado intenso?
- **creatividad**: ¿Tiene chispa o es genérico?

## FORMATO DE SALIDA (JSON):
{
  "puntuacion": 7,
  "consejo": "Consejo breve y en tono de entrenador. Ej: 'Buena pregunta, pero podrías añadir un toque de humor.'"
}

Sé motivador y evita ser demasiado crítico. No des sugerencias de mensajes alternativos, solo feedback sobre lo que ya se hizo."""


def evaluar_mensaje(historial, mensaje_usuario):
    context = "\n".join(
        [f"{'TÚ' if m['role'] == 'user' else 'IA'}: {m['content']}" for m in historial if m['role'] in ['user', 'ia']][
            -5:])
    response = client_deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": COACH_SYSTEM_PROMPT},
            {"role": "user",
             "content": f"Historial reciente:\n{context}\n\nMensaje del usuario a evaluar: {mensaje_usuario}"}
        ],
        temperature=0.5,
        max_tokens=200
    )
    resultado = response.choices[0].message.content.strip()
    if resultado.startswith("```json"):
        resultado = resultado[7:]
    elif resultado.startswith("```"):
        resultado = resultado[3:]
    if resultado.endswith("```"): resultado = resultado[:-3]
    return json.loads(resultado)


def responder_ia(historial, personalidad, nivel, temperatura=0.8):
    descripcion = SPARRING_PERSONALITIES[personalidad]["niveles"][nivel]
    system_msg = f"Eres una chica con la siguiente personalidad: {descripcion}. Responde en español latino neutro, como en un chat real."
    messages = [{"role": "system", "content": system_msg}]
    for m in historial:
        if m['role'] == 'user':
            messages.append({"role": "user", "content": m['content']})
        elif m['role'] == 'ia':
            messages.append({"role": "assistant", "content": m['content']})

    response = client_deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=temperatura,
        max_tokens=300
    )
    return response.choices[0].message.content.strip()


def resumen_final(historial, puntuaciones):
    dialogo = "\n".join(
        [f"{'TÚ' if m['role'] == 'user' else 'IA'}: {m['content']}" for m in historial if m['role'] in ['user', 'ia']])
    avg_score = sum(puntuaciones) / len(puntuaciones) if puntuaciones else 0

    prompt = f"""Analiza esta conversación de práctica y proporciona un resumen breve pero MUY ÚTIL. Sé directo y cercano.

Incluye EXACTAMENTE:
1. Dos cosas que hiciste bien (con ejemplos de la conversación).
2. Dos aspectos concretos a mejorar, y para cada uno da un ejemplo de cómo podrías haberlo hecho mejor (con una frase alternativa que podrías haber usado).
3. Un consejo final para tu próxima conversación real.

Ejemplo de cómo dar un aspecto a mejorar: "Hiciste preguntas cerradas. Para mejorarlo, en vez de preguntar '¿Te gusta tu trabajo?' podrías haber preguntado '¿Qué es lo más curioso que te ha pasado en el trabajo?'."

Máximo 8 frases en total.

Conversación:
{dialogo}

Puntuación media: {avg_score:.1f}/10"""
    response = client_deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system",
                   "content": "Eres un entrenador de Gym Social. Sé práctico, da ejemplos reales extraídos de la conversación."},
                  {"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()
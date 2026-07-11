import streamlit as st
from PIL import Image
import re

# Módulos propios
from commons import copy_button, normalizar_clave
from monitor import extraer_chat_qwen, eliminar_replies, analizar_con_deepseek
from icebreaker import extraer_perfil_qwen, generar_icebreakers
from sparring import (SPARRING_PERSONALITIES, evaluar_mensaje, responder_ia, resumen_final)
from espejo import analizar_imagen_perfil, generar_auditoria
from salvavidas import extraer_contexto_salvavidas, generar_respuesta_salvavidas

# ------------------------------------------------------------
# INTERFAZ PRINCIPAL
# ------------------------------------------------------------
st.set_page_config(page_title="Gym Social", page_icon="🏋️", layout="wide")

st.markdown("""
<style>
    @media (max-width: 600px) {
        .stImage img { max-width: 280px !important; margin: 0 auto; }
    }
    .icebreaker-card {
        border: 1px solid #eee; border-radius: 15px; padding: 15px;
        margin-bottom: 10px; background-color: #fafafa;
    }
    .user-msg {
        background-color: #DCF8C6; padding: 10px; border-radius: 10px;
        margin: 5px 0; text-align: right;
    }
    .ia-msg {
        background-color: #E8E8E8; padding: 10px; border-radius: 10px;
        margin: 5px 0; text-align: left;
    }
    .coach-msg {
        background-color: #FFF3CD; border-left: 4px solid #FFC107;
        padding: 8px; margin: 5px 0; font-size: 0.9em; color: #856404; border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("🏋️ Gym Social")

pilares_disponibles = {
    "Pilar 1: El Monitor": ["📊 Monitor de Chats", "🧊 Icebreaker"],
    "Pilar 2: El Sparring": ["🥊 Entrenamiento"],
    "Pilar 3: El Espejo": ["🔭 Auditoría de Perfil"],
    "Pilar 4: La Arena": ["⛑️ Salva Vidas", "🚧 Modo Alas (próximamente)"]
}

pilar_seleccionado = st.sidebar.selectbox("Selecciona un pilar:", list(pilares_disponibles.keys()))
herramientas = pilares_disponibles[pilar_seleccionado]

if len(herramientas) > 1 or herramientas[0] != "🚧 Próximamente":
    herramienta_seleccionada = st.sidebar.selectbox("Herramienta:", herramientas)
else:
    herramienta_seleccionada = None

if herramienta_seleccionada is None or herramienta_seleccionada == "🚧 Próximamente":
    st.title(f"🏋️ Gym Social – {pilar_seleccionado}")
    st.info("🚧 Este pilar estará disponible próximamente. ¡Estamos trabajando para ti!")
    st.stop()

# ================================================================
# PILAR 1: MONITOR DE CHATS (CON HASTA 2 CAPTURAS)
# ================================================================
if herramienta_seleccionada == "📊 Monitor de Chats":
    st.title("🏋️ Gym Social – El Monitor")
    st.caption("Sube 1 o 2 capturas de la conversación (en orden)")

    if 'conv_monitor' not in st.session_state:
        st.session_state.conv_monitor = None
    if 'extraccion_monitor' not in st.session_state:
        st.session_state.extraccion_monitor = False
    if 'diagnostico_actual' not in st.session_state:
        st.session_state.diagnostico_actual = None
    if 'temp_actual' not in st.session_state:
        st.session_state.temp_actual = 0.9
    if 'contexto_monitor' not in st.session_state:
        st.session_state.contexto_monitor = ""

    uploaded_files = st.file_uploader(
        "Selecciona 1 o 2 capturas de WhatsApp/Instagram/Tinder",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="monitor_upload"
    )

    if uploaded_files:
        cols = st.columns(len(uploaded_files))
        for i, (file, col) in enumerate(zip(uploaded_files, cols)):
            col.image(Image.open(file), caption=f"Captura {i + 1}", width=250)

        if st.button("🔍 Analizar conversación"):
            if len(uploaded_files) > 2:
                st.warning("⚠️ Máximo 2 capturas permitidas. Se analizarán solo las dos primeras.")
                uploaded_files = uploaded_files[:2]

            all_messages = []
            progress_bar = st.progress(0)

            for i, file in enumerate(uploaded_files):
                image = Image.open(file)
                with st.spinner(f"Extrayendo mensajes de captura {i + 1}..."):
                    crudos = extraer_chat_qwen(image)
                    all_messages.extend(crudos)
                progress_bar.progress((i + 1) / len(uploaded_files))

            conversacion = eliminar_replies(all_messages)
            st.session_state.conv_monitor = conversacion
            st.session_state.extraccion_monitor = True
            st.session_state.diagnostico_actual = None
            st.session_state.temp_actual = 0.9
            st.session_state.contexto_monitor = ""
            st.rerun()

        if st.session_state.extraccion_monitor:
            conv = st.session_state.conv_monitor
            st.success(f"✅ {len(conv)} mensajes extraídos")
            st.subheader("📋 Conversación detectada")
            for msg in conv:
                quien = "TÚ" if msg['sender'] == 'TÚ' else "ELLA"
                st.write(f"**{quien}:** {msg['message']}")

            if st.checkbox("¿La extracción es correcta?"):
                st.text_area("Contexto extra (opcional)", placeholder="Ej: quiero invitarla a salir...",
                             key="contexto_texto")
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("💾 Guardar contexto"):
                        st.session_state.contexto_monitor = st.session_state.contexto_texto
                        st.success("✅ Contexto guardado")
                if st.session_state.contexto_monitor:
                    st.info(f"📝 Contexto: {st.session_state.contexto_monitor}")

                boton_texto = "🔄 Otro diagnóstico" if st.session_state.diagnostico_actual else "🧠 Ejecutar diagnóstico"
                if st.button(boton_texto):
                    if st.session_state.diagnostico_actual:
                        st.session_state.temp_actual = min(st.session_state.temp_actual + 0.05, 1.2)
                    with st.spinner("Analizando..."):
                        analisis = analizar_con_deepseek(conv, st.session_state.contexto_monitor,
                                                         temperatura=st.session_state.temp_actual)
                        if analisis is None:
                            st.warning("No se pudo generar el diagnóstico.")
                        else:
                            st.session_state.diagnostico_actual = analisis

                if st.session_state.diagnostico_actual:
                    analisis = st.session_state.diagnostico_actual
                    st.subheader(f"🎯 {analisis['diagnosis']['title']}")
                    st.metric("Puntaje Global", f"{analisis['puntaje_global']}/100")
                    pesos_iconos = {"Ligero": "🪶", "Medio": "🏋️", "Pesado": "🏋️‍♂️", "Legendario": "🏆"}
                    peso = analisis['diagnosis'].get('peso', 'Medio')
                    icono = pesos_iconos.get(peso, "🏋️")
                    st.markdown(f"**{icono} Peso del caso:** {peso} {analisis['diagnosis'].get('emoji', '')}")
                    st.write(analisis['diagnosis']['description'])

                    routine = analisis.get('routine', {})
                    if routine:
                        st.subheader("🏋️ Rutina de entrenamiento")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.error(f"❌ Evita: {routine.get('que_evitar', '')}")
                        with col2:
                            st.success(f"✅ Haz: {routine.get('que_hacer', '')}")
                        st.subheader("💬 Opciones de respuesta")
                        emojis_monitor = {"humor": "😂", "curiosidad": "❓", "cumplido": "🎯", "propuesta": "🧲",
                                          "general": "💬"}
                        for i, r in enumerate(routine.get('respuestas', []), 1):
                            estilo = r.get('estilo', 'General')
                            clave = normalizar_clave(estilo)
                            emoji = emojis_monitor.get(clave, "💬")
                            with st.expander(f"{i}. {emoji} [{estilo}] {r.get('texto', '')}"):
                                st.write(f"💡 {r.get('porque', '')}")
                                copy_button(r.get('texto', ''))
            else:
                st.warning("Corrige la extracción antes de continuar.")

# ================================================================
# PILAR 1: ICEBREAKER (CON HASTA 2 CAPTURAS)
# ================================================================
elif herramienta_seleccionada == "🧊 Icebreaker":
    st.title("🧊 Gym Social – El Icebreaker")
    st.caption("Sube 1 o 2 capturas del perfil (bio, destacadas, fotos…)")

    if 'descripcion_perfil' not in st.session_state:
        st.session_state.descripcion_perfil = None
        st.session_state.perfil_analizado = False
    if 'contexto_icebreaker' not in st.session_state:
        st.session_state.contexto_icebreaker = ""

    uploaded_files = st.file_uploader(
        "Selecciona 1 o 2 capturas de perfil (Instagram, Tinder…)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="icebreaker_upload"
    )

    if uploaded_files:
        cols = st.columns(len(uploaded_files))
        for i, (file, col) in enumerate(zip(uploaded_files, cols)):
            col.image(Image.open(file), caption=f"Captura {i + 1}", width=250)

        if st.button("👁️ Analizar perfil"):
            if len(uploaded_files) > 2:
                st.warning("⚠️ Máximo 2 capturas permitidas. Se analizarán solo las dos primeras.")
                uploaded_files = uploaded_files[:2]

            descripciones = []
            progress_bar = st.progress(0)
            for i, file in enumerate(uploaded_files):
                image = Image.open(file)
                with st.spinner(f"Analizando captura {i + 1}..."):
                    desc = extraer_perfil_qwen(image)
                    descripciones.append(desc)
                progress_bar.progress((i + 1) / len(uploaded_files))

            st.session_state.descripcion_perfil = "\n\n".join(descripciones)
            st.session_state.perfil_analizado = True
            st.session_state.contexto_icebreaker = ""
            st.rerun()

        if st.session_state.perfil_analizado:
            st.success("✅ Perfil analizado")
            st.subheader("📄 Descripción extraída")
            st.info(st.session_state.descripcion_perfil)

            st.text_area("Datos extra (opcional, pero muy importantes)",
                         placeholder="¿Hobbies, trabajo, algo que sepas de ella? Esto pesa más que la imagen.",
                         key="contexto_ice_texto")
            if st.button("💾 Guardar contexto", key="guardar_ice"):
                st.session_state.contexto_icebreaker = st.session_state.contexto_ice_texto
                st.success("✅ Contexto guardado")
            if st.session_state.contexto_icebreaker:
                st.info(f"📝 Contexto: {st.session_state.contexto_icebreaker}")

            temp = st.slider("Creatividad", 0.7, 1.5, 0.95, 0.05)
            if st.button("🧊 Generar líneas de apertura"):
                with st.spinner("Generando icebreakers..."):
                    ice = generar_icebreakers(st.session_state.descripcion_perfil, st.session_state.contexto_icebreaker,
                                              temp)

                st.subheader(f"👤 {ice.get('perfil_resumen', '')}")
                emojis = {
                    "divertida": "😂", "observacion_encantadora": "✨", "observacion encantadora": "✨",
                    "observación encantadora": "✨", "pregunta_con_gancho": "❓", "pregunta con gancho": "❓",
                    "cumplido_no_fisico": "💘", "cumplido no físico": "💘", "cumplido no fisico": "💘",
                    "wildcard": "🃏", "wildcard comodín": "🃏", "wildcard comodin": "🃏",
                    "comodin": "🃏", "comodín": "🃏"
                }

                for i, linea in enumerate(ice.get('lineas', []), 1):
                    tipo_original = linea.get('tipo', '').strip()
                    clave_normalizada = tipo_original.lower()
                    clave_normalizada = re.sub(r'[^a-záéíóúñü ]', ' ', clave_normalizada)
                    clave_normalizada = re.sub(r'\s+', ' ', clave_normalizada).strip()
                    emoji = emojis.get(clave_normalizada, "💬")
                    with st.container():
                        st.markdown(f"""
                        <div class="icebreaker-card">
                            <h4>{emoji} {tipo_original.replace('_', ' ').title()}</h4>
                            <p style="font-size:16px;">"{linea['texto']}"</p>
                            <p style="color:#666; font-size:13px;">💡 {linea['porque']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        copy_button(linea['texto'])

# ================================================================
# PILAR 2: SPARRING (SIN CAMBIOS)
# ================================================================
elif herramienta_seleccionada == "🥊 Entrenamiento":
    st.title("🥊 Gym Social – El Sparring")
    st.caption("Practica tus habilidades con una IA que evoluciona según tus respuestas")

    if 'historial' not in st.session_state:
        st.session_state.historial = []
    if 'puntuaciones' not in st.session_state:
        st.session_state.puntuaciones = []
    if 'sparring_activo' not in st.session_state:
        st.session_state.sparring_activo = False
    if 'nivel' not in st.session_state:
        st.session_state.nivel = 0
    if 'contador_mensajes' not in st.session_state:
        st.session_state.contador_mensajes = 0

    col1, col2 = st.columns([2, 1])
    with col1:
        personalidad = st.selectbox("Elige una personalidad para practicar:", list(SPARRING_PERSONALITIES.keys()))
    with col2:
        dificultad = st.radio("Dificultad", ["Fácil", "Medio", "Difícil"], index=1)
        temp_map = {"Fácil": 0.9, "Medio": 0.7, "Difícil": 0.5}
        temperatura = temp_map[dificultad]

    if st.button("Iniciar práctica"):
        st.session_state.historial = []
        st.session_state.puntuaciones = []
        st.session_state.sparring_activo = True
        st.session_state.nivel = 0
        st.session_state.contador_mensajes = 0
        st.rerun()

    if st.session_state.sparring_activo:
        nivel_actual = st.session_state.nivel + 1
        st.markdown(f"**Nivel actual de {personalidad}:** {nivel_actual}/3")
        st.progress((st.session_state.contador_mensajes % 4) / 4,
                    text=f"Progreso: {st.session_state.contador_mensajes % 4}/4")

        for m in st.session_state.historial:
            if m['role'] == 'user':
                st.markdown(f"<div class='user-msg'>TÚ<br>{m['content']}</div>", unsafe_allow_html=True)
            elif m['role'] == 'ia':
                st.markdown(f"<div class='ia-msg'>IA ({personalidad})<br>{m['content']}</div>", unsafe_allow_html=True)
            elif m['role'] == 'coach':
                st.markdown(f"<div class='coach-msg'>🧑‍🏫 Coach: {m['content']}</div>", unsafe_allow_html=True)

        if st.session_state.contador_mensajes >= 12:
            st.warning("🏁 Has alcanzado el límite de 12 mensajes. La práctica ha terminado.")
            if st.session_state.puntuaciones:
                promedio = sum(st.session_state.puntuaciones) / len(st.session_state.puntuaciones)
                st.success(f"🏁 Práctica terminada. Puntuación promedio: {promedio:.1f}/10")
                with st.spinner("Generando resumen..."):
                    resumen = resumen_final(st.session_state.historial, st.session_state.puntuaciones)
                st.subheader("📋 Resumen de la sesión")
                st.write(resumen)
                txt_resumen = f"Resumen de práctica - Gym Social\n\nPersonalidad: {personalidad}\nPuntuación media: {promedio:.1f}/10\n\n{resumen}"
                st.download_button("📥 Descargar informe (TXT)", data=txt_resumen, file_name="resumen_practica.txt",
                                   mime="text/plain")
                st.balloons()
            st.session_state.sparring_activo = False
        else:
            with st.form("sparring_form", clear_on_submit=True):
                user_input = st.text_area("Tu mensaje:", key="sparring_input")
                if st.form_submit_button("Enviar"):
                    if user_input:
                        with st.spinner("Coach evaluando..."):
                            evaluacion = evaluar_mensaje(st.session_state.historial, user_input)
                            punt = evaluacion['puntuacion']
                            consejo = evaluacion['consejo']
                            st.session_state.puntuaciones.append(punt)

                        st.session_state.historial.append({"role": "user", "content": user_input})
                        st.session_state.contador_mensajes += 1

                        with st.spinner(f"{personalidad} está escribiendo..."):
                            respuesta = responder_ia(st.session_state.historial, personalidad, st.session_state.nivel,
                                                     temperatura=temperatura)
                            st.session_state.historial.append({"role": "ia", "content": respuesta})

                        st.session_state.historial.append(
                            {"role": "coach", "content": f"{consejo} (Puntuación: {punt}/10)"})

                        if st.session_state.contador_mensajes % 4 == 0 and st.session_state.contador_mensajes > 0:
                            ultimas_punt = st.session_state.puntuaciones[-4:]
                            promedio = sum(ultimas_punt) / len(ultimas_punt)
                            if promedio >= 7 and st.session_state.nivel < 2:
                                st.session_state.nivel += 1
                                st.success(
                                    f"🌟 ¡Subiste de nivel! Ahora {personalidad} está en nivel {st.session_state.nivel + 1}/3")
                            elif promedio < 4 and st.session_state.nivel > 0:
                                st.session_state.nivel -= 1
                                st.warning(
                                    f"📉 Bajaste de nivel. {personalidad} ahora está en nivel {st.session_state.nivel + 1}/3")

                        st.rerun()

        if st.button("Terminar práctica antes de tiempo"):
            if st.session_state.puntuaciones:
                promedio = sum(st.session_state.puntuaciones) / len(st.session_state.puntuaciones)
                st.success(f"🏁 Práctica terminada. Puntuación promedio: {promedio:.1f}/10")
                with st.spinner("Generando resumen..."):
                    resumen = resumen_final(st.session_state.historial, st.session_state.puntuaciones)
                st.subheader("📋 Resumen de la sesión")
                st.write(resumen)
                txt_resumen = f"Resumen de práctica - Gym Social\n\nPersonalidad: {personalidad}\nPuntuación media: {promedio:.1f}/10\n\n{resumen}"
                st.download_button("📥 Descargar informe (TXT)", data=txt_resumen, file_name="resumen_practica.txt",
                                   mime="text/plain")
                st.balloons()
            st.session_state.sparring_activo = False

# ================================================================
# PILAR 3: EL ESPEJO (SIN CAMBIOS, YA ACEPTA HASTA 3 IMÁGENES)
# ================================================================
elif herramienta_seleccionada == "🔭 Auditoría de Perfil":
    st.title("🔭 Gym Social – El Espejo")
    st.caption("Sube capturas de tu perfil y descubre cómo mejorarlo")

    uploaded_files = st.file_uploader(
        "Sube de 1 a 3 capturas de tu perfil (bio, fotos, destacadas…)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="espejo_upload"
    )

    if uploaded_files:
        images = [Image.open(f) for f in uploaded_files]
        cols = st.columns(len(images))
        for i, (img, col) in enumerate(zip(images, cols)):
            col.image(img, caption=f"Captura {i + 1}", width=200)

        if st.button("🪞 Analizar mi perfil"):
            if len(images) > 3:
                st.warning("⚠️ Máximo 3 capturas permitidas. Se analizarán solo las tres primeras.")
                images = images[:3]

            descripciones = []
            progress_bar = st.progress(0)
            for i, img in enumerate(images):
                with st.spinner(f"Analizando captura {i + 1}..."):
                    desc = analizar_imagen_perfil(img)
                    descripciones.append(desc)
                progress_bar.progress((i + 1) / len(images))

            st.success("✅ Perfil analizado")
            with st.spinner("Generando informe personalizado..."):
                auditoria = generar_auditoria(descripciones)

            if auditoria:
                st.subheader(f"🎯 Puntuación general: {auditoria['puntuacion_general']}/100")

                with st.expander("📸 Análisis de tus fotos"):
                    for linea in auditoria.get('analisis_fotos', []):
                        st.write(f"- {linea}")

                with st.expander("📝 Tu bio"):
                    st.write(auditoria.get('evaluacion_bio', ''))

                with st.expander("🎨 Consejos de estilo"):
                    st.write(auditoria.get('consejos_estilo', ''))

                st.info(f"🎯 **Misión de hoy:** {auditoria.get('mision_diaria', '')}")

# ================================================================
# PILAR 4: LA ARENA - SALVA VIDAS
# ================================================================
elif herramienta_seleccionada == "⛑️ Salva Vidas":
    st.title("🚨 Gym Social – Salva Vidas")
    st.caption("¿Atascado en una conversación? Sube la captura y recibe una respuesta al instante")

    if 'mensajes_salvavidas' not in st.session_state:
        st.session_state.mensajes_salvavidas = None
    if 'extraccion_salvavidas' not in st.session_state:
        st.session_state.extraccion_salvavidas = False
    if 'respuesta_salvavidas' not in st.session_state:
        st.session_state.respuesta_salvavidas = None

    uploaded_file = st.file_uploader("Sube la captura del momento crítico", type=["png","jpg","jpeg"], key="salvavidas_upload")
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Captura", width=300)

        tono = st.selectbox(
            "¿Qué tono buscas?",
            ["Divertido", "Gracioso", "Provocativo", "Empático"],
            index=0
        )

        if st.button("👁️ Extraer contexto"):
            with st.spinner("Analizando la conversación..."):
                mensajes = extraer_contexto_salvavidas(image)
                st.session_state.mensajes_salvavidas = mensajes
                st.session_state.extraccion_salvavidas = True
                st.session_state.respuesta_salvavidas = None  # Reset respuesta anterior

        if st.session_state.extraccion_salvavidas:
            mensajes = st.session_state.mensajes_salvavidas
            st.subheader("📋 Conversación detectada")
            if mensajes:
                for msg in mensajes:
                    quien = "TÚ" if msg['sender'] == 'TÚ' else "ELLA"
                    st.write(f"**{quien}:** {msg['message']}")
            else:
                st.warning("No se encontraron mensajes claros. Intenta con otra captura.")

            if st.checkbox("¿La extracción es correcta?"):
                creatividad = st.slider("Creatividad", 0.7, 1.5, 0.95, 0.05)

                if st.button("🚨 ¡Sácame de este apuro!"):
                    with st.spinner("Generando respuesta de rescate..."):
                        respuesta = generar_respuesta_salvavidas(mensajes, tono.lower(), temperatura=creatividad)
                        st.session_state.respuesta_salvavidas = respuesta

                if st.session_state.respuesta_salvavidas:
                    st.success("✅ Respuesta lista:")
                    st.code(st.session_state.respuesta_salvavidas, language=None)
                    copy_button(st.session_state.respuesta_salvavidas)
            else:
                st.warning("Corrige la extracción antes de continuar.")
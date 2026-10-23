import os
import re
import json
import uuid
import sqlite3
import pytz
import requests
import logging
import base64
# Recolección de basura en memoria RAM
import gc  
import time
import psutil
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image  
from ddgs import DDGS
from pydub import AudioSegment
import yt_dlp
from googleapiclient.discovery import build

import telebot
from telebot.types import (
    BotCommand, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, ReactionTypeEmoji
)
from config import *

# Desactivamos el nivel DEBUG para evitar que el log llene el disco del sistema
telebot.logger.setLevel(logging.INFO)

# Configuración de la API de Google Custom Search
API_KEY = "ID_de_Google_Cloud_Console_Aqui"  # ID de Google Cloud Console
SEARCH_ENGINE_ID = "ID_De_Custom_Search_Aqui"  # ID de Custom Search
SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

# URL RAW del Gist de GitHub
_ENCODED_GIST = "aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS9wcm9ncmFtYWRvcjAyNC84MjNiZjA4ZjM0OGZhNGY0ZWMzODc5NDYxMjNiMTE3Zi9yYXcvYXBwc19jb25maWcuanNvbg=="

def obtener_config_apps():
    try:
        # Decodificar el base64 a texto plano
        gist_apps_url = base64.b64decode(_ENCODED_GIST).decode('utf-8')

        response = requests.get(gist_apps_url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error cargando JSON remoto desde Gist Cifrado: {e}")
        return {}

# Agregar tiempo
telebot.apihelper.CONNECT_TIMEOUT = 30
telebot.apihelper.READ_TIMEOUT = 180
# Instanciar el bot en Telegram
bot = telebot.TeleBot(TELEGRAM_TOKEN)


# FUNCIÓN PARA MOSTRAR BANNER EN CONSOLA CON COLOR PRO
def mostrar_banner():
    # Limpiar consola (compatible con Windows y Linux/Termux)
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Códigos de color ANSI para la terminal
    CYAN = "\033[1;36m"
    MAGENTA = "\033[1;35m"
    GREEN = "\033[1;32m"
    RESET = "\033[0m"
    
    banner = f"""
{CYAN}======================================================================{RESET}
{MAGENTA}  _   _                       ____  _         ____        _     {RESET}
{MAGENTA} | \\ | | ___ _ __ ___   ___  / ___|(_) ___   | __ )  ___ | |_   {RESET}
{MAGENTA} |  \\| |/ _ \\ '_ ` _ \\ / _ \\ \\___ \\| |/ __|  |  _ \\ / _ \\| __|  {RESET}
{MAGENTA} | |\\  |  __/ | | | | |  __/  ___) | | (__   | |_) | (_) | |_   {RESET}
{MAGENTA} |_| \\_|\\___|_| |_| |_|\\___| |____/|_|\\___|  |____/ \\___/ \\__|  {RESET}
{CYAN}======================================================================{RESET}
{GREEN}       NEMESICBOT V1  --  BY SICARIOOFC (TELEGRAM BOT){RESET}
{CYAN}======================================================================{RESET}
"""
    print(banner)

# MENSAJE DE CONEXIÓN PRO
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
RESET = "\033[0m"

conectado = f"""
{CYAN}======================================================================{RESET}
{GREEN}          🤖 NemeSicBot Conectado con Éxito a Telegram                {RESET}
{CYAN}======================================================================{RESET}
"""    


# Función auxiliar para borrar archivos locales de forma segura
def borrar_archivo_seguro(filepath):
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"Error al eliminar {filepath}: {e}")

# Conectar con la base de datos SQLite
conn = sqlite3.connect("usuarios.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER UNIQUE,
    username TEXT,
    nombre_completo TEXT,
    fecha_nacimiento TEXT,
    rol TEXT,
    pais TEXT,
    foto TEXT
)''')

cursor.execute(''' CREATE TABLE IF NOT EXISTS calificaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER UNIQUE,
    calificacion INTEGER
 )''')

conn.commit()
conn.close()
print("Base de datos creada/verificada correctamente.")

user_data = {}
esperando_imagen = {}


# Diccionario global de zonas horarias
ZONAS_HORARIAS_MUNDIAL = {
    "Argentina": "America/Argentina/Buenos_Aires",
    "México": "America/Mexico_City",
    "Colombia": "America/Bogota",
    "España": "Europe/Madrid",
    "Chile": "America/Santiago",
    "Perú": "America/Lima",
    "Venezuela": "America/Caracas",
    "Alemania": "Europe/Berlin",
    "Bolivia": "America/La_Paz",
    "Brasil": "America/Sao_Paulo",
    "Canadá": "America/Toronto",
    "Cuba": "America/Havana",
    "Ecuador": "America/Guayaquil",
    "El Salvador": "America/El_Salvador",
    "Estados Unidos": "America/New_York",
    "Guatemala": "America/Guatemala",
    "Honduras": "America/Tegucigalpa",
    "Japón": "Asia/Tokyo",
    "Nicaragua": "America/Managua",
    "Panamá": "America/Panama",
    "Paraguay": "America/Asuncion",
    "República Dominicana": "America/Santo_Domingo",
    "Rusia": "Europe/Moscow",
    "Uruguay": "America/Montevideo"
}

def obtener_hora_local(pais):
    zona_horaria = ZONAS_HORARIAS_MUNDIAL.get(pais, "Etc/UTC")
    try:
        zona = pytz.timezone(zona_horaria)
        ahora = datetime.now(zona)
        fecha_str = ahora.strftime("%d/%m/%Y %H:%M:%S")
        return f"{fecha_str[:10]}🕔{fecha_str[11:]}"
    except pytz.UnknownTimeZoneError:
        return "Error en la zona horaria"

SUSCRIPTORES_FILE = "suscriptores.json"

def cargar_suscriptores():
    try:
        with open(SUSCRIPTORES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def guardar_suscriptores(suscriptores):
    with open(SUSCRIPTORES_FILE, "w") as f:
        json.dump(suscriptores, f)

suscriptores = cargar_suscriptores()

# Configuración de Comandos
bot.set_my_commands([
    BotCommand("start", "Inicia el bot"),
    BotCommand("menu", "Lista de comandos y ayuda"),
    BotCommand("creador", "Información del creador"),
    BotCommand("repo", "Clonar el bot"),
    BotCommand("ping", "Velocidad del bot"),
    BotCommand("status", "Estado del bot"),
    BotCommand("registro", "Registrarte con el bot"),
    BotCommand("perfil", "Ver tu perfil registrado"),
    BotCommand("editarperfil", "Editar tu perfil"),
    BotCommand("deleteusuario", "Eliminar tu perfil registrado"),
    BotCommand("appsyextra", "Apps y extras del bot"),
    BotCommand("canteleg", "Canal de Telegram"),
    BotCommand("canyoutub", "Canal de YouTube"),
    BotCommand("paginaweb", "Página web del creador"),
    BotCommand("paypalme", "Apoyo donación"),
    BotCommand("mtmanag", "Apk editar strings/codigo mods"),
    BotCommand("mtmanagbet", "Apk mtmanag mas avanzada"),
    BotCommand("apkeditorpro", "Apk editar codigo/diseño mods"),
    BotCommand("apktoolm", "Apk cambiar nombre/codigo mods"),
    BotCommand("pixellab", "Edición y personalizar texto e imagen"),
    BotCommand("telegprem", "Telegram con función premium desbloqueada"),
    BotCommand("teamzetpriv", "Apk movil de paginaweb"),
    BotCommand("base64pro", "Codificar/decodificar a base64"),
    BotCommand("imagen", "Comando /imagen + Nombre"),
    BotCommand("musica", "Comando /musica + Nombre"),
    BotCommand("video", "Comando /video + Nombre"),
    BotCommand("aibuscar", "Comando /aibuscar + Texto"),
    BotCommand("aisticker", "Crear sticker"),
])

button1 = KeyboardButton("🙍‍♂️ Cuenta")
button2 = KeyboardButton("⚙️ Ayuda")
button3 = KeyboardButton("🛠️ Soporte")
button4 = KeyboardButton("📝 Calificar")
button5 = KeyboardButton("📊 Ver Calificaciones")
button6 = KeyboardButton("💸 Donación")
keyboard1 = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
keyboard1.row(button1, button2)
keyboard1.row(button3, button4)
keyboard1.row(button5, button6)

btn_subs = InlineKeyboardButton("✅ Suscribirse", callback_data="suscribirse")
btn_unsubs = InlineKeyboardButton("❌ Desuscribirse", callback_data="desuscribirse")
notificacion1 = InlineKeyboardMarkup()
notificacion1.row(btn_subs, btn_unsubs)

@bot.message_handler(commands=["start"])
def cmd_start(message):
    username = message.from_user.username or "usuario"
    sent_message = bot.reply_to(
        message, f"Hola @{username}, soy NemeSicBot, tu asistente virtual. ¿En qué te puedo ayudar?\n\n Ejecuta /menu para ver los comandos.", reply_markup=keyboard1)
    try:
        bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("⭐")])
    except Exception:
        pass

def obtener_conexion():
    return sqlite3.connect("usuarios.db", check_same_thread=False)

@bot.message_handler(commands=["menu"])
def cmd_menu(message):
    username = message.from_user.username or "usuario"
    chat_id = message.chat.id
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pais FROM usuarios WHERE chat_id = ?", (chat_id,))
        resultado = cursor.fetchone()
    pais = resultado[0] if resultado else "UTC"
    fecha_hora = obtener_hora_local(pais)

    # Detectar modo privado/grupo
    tipo_chat = message.chat.type
    if tipo_chat == 'private':
       modo_actual = "Privado"
    else:
        modo_actual = "Grupo"

    menu_text = f"""
╭───◈ NEMESIC - TG ◈─────╮    
│ 🤖 Bot: NemeSicBot V1
│ 👑 Creador: SicarioOfc
│📅{fecha_hora}🌎{pais}
│ 🌎 Modo: {modo_actual}
│ 👤 User: @{username}
╰───────────────────╯    
『 PRINCIPAL 』
├ • /start - Inicia el bot
├ • /menu - Ver menú principal
├ • /creador - Info del creador
├ • /repo - Clonar el bot
├ • /ping - Velocidad del bot
└ • /status - Estado de bot
『 REGISTRO 🔐 』
├ • /registro - Registrarte
├ • /perfil - Ver tu perfil
├ • /editarperfil - Editar tu perfil
└ • /deleteusuario - Eliminar perfil
『 EXTRAS & REDES 🚀 』
├ • /appsyextra - Menu APKs e IA[🔒]
├ • /canteleg - Canal de Telegram
├ • /canyoutub - Canal de YouTube
├ • /paginaweb - Página web
└ • /paypalme - Apoyo donación
    """
    keyboard = InlineKeyboardMarkup()
    boton_canal = InlineKeyboardButton("📢 VER CANAL", url="https://t.me/mds_inmunes2")
    keyboard.add(boton_canal)

    img_path = "imagenes/nemesicbot_menu.jpg"
    if os.path.exists(img_path):
        with open(img_path, "rb") as photo:
            sent_message = bot.send_photo(chat_id, photo, caption=menu_text, parse_mode='HTML', reply_markup=keyboard)
            try:
                bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("⭐")])
            except Exception:
                pass
    else:
        bot.send_message(chat_id, menu_text, parse_mode='HTML', reply_markup=keyboard)

@bot.message_handler(commands=["appsyextra"])
def cmd_appsyextra(message):
    username = message.from_user.username or "usuario"
    chat_id = message.chat.id
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pais FROM usuarios WHERE chat_id = ?", (chat_id,))
        resultado = cursor.fetchone()
    pais = resultado[0] if resultado else "UTC"
    fecha_hora = obtener_hora_local(pais)

    # Detectar modo privado/grupo
    tipo_chat = message.chat.type
    if tipo_chat == 'private':
        modo_actual = "Privado"
    else:
        modo_actual = "Grupo"

    menu_text2 = f"""
╭──◈NEMESIC - APKS e IA◈────╮    
│ 🤖 Bot: NemeSicBot V1
│ 👑 Creador: SicarioOfc
│📅{fecha_hora}🌎{pais}
│ 🌎 Modo: {modo_actual}
│ 👤 User: @{username}
╰───────────────────╯
Hola @{username} para poder desbloquear dichas funciones,\ndebes de estar registrado o registrarte con el comando /registro   
『 🕹️ Apps Premium 』
├ • /mtmanag - Edit strings/códigos
├ • /mtmanagbet - mt premium
├ • /apkeditorpro - Edit códe/diseño
├ • /apktoolm - Camb name/icon
├ • /pixellab - Edic person text/imagen
├ • /telegprem - Func premium
├ • /teamzetpriv - Página movil
└ • /base64pro - Cod/decod
『 🎬Multimedia e IA🤖 』
├ • /imagen + Nombre
├ • /musica + Nombre
├ • /video + Nombre
├ • /aibuscar + Texto
└ • /aisticker - Crear sticker 
    """

    keyboard = InlineKeyboardMarkup()
    boton_canal = InlineKeyboardButton("📢 VER CANAL", url="https://t.me/mds_inmunes2")
    keyboard.add(boton_canal)

    img_path = "imagenes/nemesicbot_menu2.jpg"
    if os.path.exists(img_path):
        with open(img_path, "rb") as photo:
            sent_message = bot.send_photo(chat_id, photo, caption=menu_text2, parse_mode='HTML', reply_markup=keyboard)
            try:
                bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("👍")])
            except Exception:
                pass
    else:
        bot.send_message(chat_id, menu_text2, parse_mode='HTML', reply_markup=keyboard)

@bot.message_handler(func=lambda message: any(cmd in message.text for cmd in ["Cuenta", "Ayuda", "Soporte", "Calificar", "Ver Calificaciones", "Donación"]))
def cmd_kb_answer(message):
    if "Cuenta" in message.text:
        bot.reply_to(message, "Digita los siguientes comandos:\n\n/registro - Registrarte\n/perfil - Ver tu perfil\n/editarperfil - Editar tu perfil\n/deleteusuario - Eliminar perfil")
    elif "Ayuda" in message.text:
        bot.reply_to(message, "Para el uso del bot, usa:\n\n/start - Iniciar el bot\n/menu - Ver el menu completo\n/creador - Información del creador")
    elif "Soporte" in message.text:
        bot.reply_to(message, 'Contacta a soporte:\n<a href="mailto:teamzetasprivatev1@gmail.com">teamzetasprivatev1@gmail.com</a>', parse_mode='HTML')
    elif "Calificar" in message.text and "Ver" not in message.text:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        botones = [KeyboardButton(str(i)) for i in range(1, 11)]
        markup.row(*botones[:5])
        markup.row(*botones[5:])
        markup.row(KeyboardButton("❌ Cancelar"))
        bot.reply_to(message, "Por favor, califica el bot del 1 al 10:", reply_markup=markup)
    elif "Ver Calificaciones" in message.text:
        with sqlite3.connect("usuarios.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT AVG(calificacion) FROM calificaciones")
            resultado = cursor.fetchone()
            promedio = resultado[0] if resultado[0] else 0
        bot.reply_to(message, f"📊 El bot tiene una calificación promedio de: {promedio:.1f}/10 ⭐")
    elif "Donación" in message.text:
        bot.reply_to(message, "¡Gracias por tu apoyo! Puedes donar en PayPal:\nhttps://www.paypal.com/donate/?hosted_button_id=AXWABFZNYU8L6")

@bot.message_handler(func=lambda message: message.text.isdigit() and 1 <= int(message.text) <= 10)
def guardar_calificacion(message):
    chat_id = message.chat.id
    calificacion = int(message.text)
    with sqlite3.connect("usuarios.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO calificaciones (chat_id, calificacion) VALUES (?, ?)", (chat_id, calificacion))
        conn.commit()
    bot.reply_to(message, f"¡Gracias por calificar con {calificacion}/10! ⭐", reply_markup=ReplyKeyboardRemove())
    mostrar_menu_principal(chat_id)

@bot.message_handler(func=lambda message: message.text == "❌ Cancelar")
def cancelar_calificacion(message):
    chat_id = message.chat.id
    bot.reply_to(message, "Calificación cancelada.", reply_markup=ReplyKeyboardRemove())
    mostrar_menu_principal(chat_id)

def mostrar_menu_principal(chat_id):
    bot.send_message(chat_id, "Menú principal:", reply_markup=keyboard1)

@bot.message_handler(commands=["creador"])
def cmd_creador(message):
    texto = (
        "╭── 〔👑*Acerca Del Creador*〕 ──╮\n"
        "│\n"
        "│ 🤖 Bot: NemeSicBot V1\n"
        "│ 👤 Creador: SicarioOfc\n"
        "│\n"
        "├───── *Redes Sociales* ─────\n"
        "│\n"
        "│ 📢 /canteleg - Canal de Telegram\n"
        "│ 🎥 /canyoutub - Canal de YouTube\n"
        "│ 🌐 /paginaweb - Sitio Web Oficial\n"
        "│\n"
        "├───── *Apoya El Proyecto* ─────\n"
        "│\n"
        "│ ☕ /payapalme - Donación PayPal\n"
        "│\n"
        "╰──────────────────────╯"
    )
    sent_message = bot.reply_to(message, texto, parse_mode="Markdown", reply_markup=keyboard1)
    try:
        bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("❤️")])
    except Exception:
        pass
    
    
# Comando solo para quien clone el bot (admin - en chat privado)
@bot.message_handler(commands=["avisar"])
def cmd_avisar(message):
    # Verificamos si el usuario que ejecuta el comando es el administrador autorizado
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "⚠️ No tienes permisos para usar este comando.")
        return

    # Extraer el texto de la actualización después de /avisar
    texto_aviso = message.text.replace("/avisar", "").strip()
    if not texto_aviso:
        bot.reply_to(message, "❌ Escribe el mensaje de actualización después de /avisar. Ejemplo:\n/avisar ¡Nuevas funciones añadidas!")
        return

    suscriptores = cargar_suscriptores()
    if not suscriptores:
        bot.reply_to(message, "⚠️ No hay suscriptores registrados todavía en el archivo `suscriptores.json`.")
        return

    msg_progreso = bot.send_message(message.chat.id, f"📢 Iniciando difusión a {len(suscriptores)} suscriptores...")
    
    enviados = 0
    errores = 0

    for chat_id in suscriptores:
        try:
            bot.send_message(
                chat_id, 
                f"🚨 *¡AVISO DE ACTUALIZACIÓN!*\n\n{texto_aviso}\n\n_NemeSicBot V1_ 🤖", 
                parse_mode="Markdown"
            )
            enviados += 1
            time.sleep(0.3)  # Pausa breve para evitar bloqueos por flood de Telegram
        except Exception as e:
            print(f"No se pudo enviar al chat {chat_id}: {e}")
            errores += 1

    # Actualizar mensaje con el resumen final
    try:
        bot.edit_message_text(
            f"✅ *Difusión completada con éxito.*\n\n"
            f"📨 Enviados: {enviados}\n"
            f"❌ Fallidos: {errores}",
            message.chat.id,
            msg_progreso.message_id,
            parse_mode="Markdown"
        )
    except Exception:
        bot.send_message(message.chat.id, f"✅ Difusión completada. Enviados: {enviados}, Fallidos: {errores}")
    

@bot.message_handler(commands=["repo"])
def cmd_repo(message):
    sent_message = bot.reply_to(message, "📦 *REPOSITORIO DEL BOT*\n\nClona este bot y ejecútalo en tu propio servidor o dispositivo:\n🔗git clone https://github.com/programador024/NemeSicBot-TG.git", reply_markup=keyboard1)
    try:
        bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("❤️")])
    except Exception:
        pass        

# Calcular el uptime
start_time = datetime.now()

@bot.message_handler(commands=["ping"])
def cmd_ping(message):
    start_time = time.time()
    try:
        # 1. Enviar mensaje temporal de carga
        sent_message = bot.reply_to(message, "🏓 Calculando ping...")
        # 2. Calcular la latencia real
        end_time = time.time()
        latency = (end_time - start_time) * 1000
        # 3. Eliminar el mensaje temporal para evitar bloqueos de edición de Telegram
        bot.delete_message(message.chat.id, sent_message.message_id)
        # 4. Enviar el mensaje final con el resultado limpio y el teclado
        final_msg = bot.send_message(
            message.chat.id,
            f"🏓 *¡PONG!*\n\n⚡ *Velocidad:* {latency:.2f} ms\n✅ *Bot activo y respondiendo.*",
            parse_mode="Markdown",
            reply_markup=keyboard1
        )
        
        bot.set_message_reaction(message.chat.id, final_msg.message_id, [ReactionTypeEmoji("🔥")])
    except Exception as e:
        print(f"Error en el comando ping: {e}")

@bot.message_handler(commands=["status", "estado"])
def cmd_status(message):
    uptime = datetime.now() - start_time
    horas, resto = divmod(int(uptime.total_seconds()), 3600)
    minutos, segundos = divmod(resto, 60)

    # Información del sistema
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    texto = (
        f"╭───◈ ESTADO DEL BOT ◈───╮\n"
        f"│\n"
        f"│ 🤖 Bot: NemeSicBot V1\n"
        f"│ 🌐 Estado: En línea✅\n"
        f"│ ⏱️ Tiempo activo: {horas}h {minutos}m {segundos}s\n"
        f"│ 💻 CPU: {cpu}%\n"
        f"│ 🧠 RAM: {ram}%\n"
        f"│ 📅 Inicio: {start_time.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        f"_Todo funcionando correctamente._"
    )
    sent_message = bot.reply_to(message, texto, parse_mode="Markdown", reply_markup=keyboard1)
    try:
        bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("🔥")])
    except Exception:
        pass

@bot.message_handler(commands=["canteleg"])
def cmd_canteleg(message):
    sent_message = bot.reply_to(message, "Mi Telegram es: https://t.me/mds_inmunes2", reply_markup=keyboard1)
    try:
        bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("🔥")])
    except Exception:
        pass

@bot.message_handler(commands=["canyoutub"])
def cmd_canyoutub(message):
    sent_message = bot.reply_to(message, "Mi YouTube es: https://www.youtube.com/@nms_sicario023", reply_markup=keyboard1)
    try:
        bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("👍")])
    except Exception:
        pass

@bot.message_handler(commands=["paginaweb"])
def cmd_paginaweb(message):
    sent_message = bot.reply_to(message, "Mi Página Web es: https://teamzetasprivate.com/", reply_markup=keyboard1)
    try:
        bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("❤️")])
    except Exception:
        pass

@bot.message_handler(commands=["paypalme"])
def cmd_paypalme(message):
    sent_message = bot.reply_to(message, "Apoyame con una donación para un cafe,\npara mejorar el bot:\nhttps://www.paypal.com/paypalme/SicariOfc025", reply_markup=keyboard1)
    try:
        bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("❤️")])
    except Exception:
        pass

@bot.message_handler(commands=["registro"])
def cmd_registro(message):
    chat_id = message.chat.id
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE chat_id = ?", (chat_id,))
        if cursor.fetchone():
            sent_message = bot.send_message(chat_id, "Ya estás registrado. Usa /perfil para ver tus datos.")
            try:
                bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("❤️")])
            except Exception:
                pass
            return

    bot.send_message(chat_id, "¿Cuál es tu nombre completo?")
    bot.register_next_step_handler(message, obtener_nombre)

def obtener_nombre(message):
    chat_id = message.chat.id
    username = message.from_user.username or "usuario"
    nombre_completo = message.text
    bot.send_message(chat_id, "¿Cuál es tu fecha de nacimiento? (Formato: DD/MM/AAAA)")
    bot.register_next_step_handler(message, obtener_fecha, username, nombre_completo)

def obtener_fecha(message, username, nombre_completo):
    chat_id = message.chat.id
    try:
        fecha_nacimiento = datetime.strptime(message.text, "%d/%m/%Y").strftime("%Y-%m-%d")
        bot.send_message(chat_id, "¿Cuál es tu rol o hobby?")
        bot.register_next_step_handler(message, obtener_rol, username, nombre_completo, fecha_nacimiento)
    except ValueError:
        bot.send_message(chat_id, "Formato incorrecto. Usa DD/MM/AAAA.")
        bot.register_next_step_handler(message, obtener_fecha, username, nombre_completo)

def obtener_rol(message, username, nombre_completo, fecha_nacimiento):
    chat_id = message.chat.id
    rol = message.text
    bot.send_message(chat_id, "¿En qué país vives?")
    bot.register_next_step_handler(message, obtener_pais, username, nombre_completo, fecha_nacimiento, rol)

def obtener_pais(message, username, nombre_completo, fecha_nacimiento, rol):
    chat_id = message.chat.id
    pais = message.text
    bot.send_message(chat_id, "Envíame una foto para tu perfil (o envía un mensaje si prefieres omitir).")
    bot.register_next_step_handler(message, obtener_imagen, username, nombre_completo, fecha_nacimiento, rol, pais)

def obtener_imagen(message, username, nombre_completo, fecha_nacimiento, rol, pais):
    chat_id = message.chat.id
    foto = message.photo[-1].file_id if message.content_type == "photo" else None

    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (chat_id, username, nombre_completo, fecha_nacimiento, rol, pais, foto) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (chat_id, username, nombre_completo, fecha_nacimiento, rol, pais, foto))
        conn.commit()

    sent_message = bot.send_message(chat_id, "✅ Registro completado. Usa /perfil para ver tus datos.")
    try:
        bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("✍️")])
    except Exception:
        pass

def escape_markdown_v2(text):
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(r"([" + re.escape(escape_chars) + r"])", r"\\\1", text)

@bot.message_handler(commands=["perfil"])
def cmd_perfil(message):
    chat_id = message.chat.id
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE chat_id = ?", (chat_id,))
        user = cursor.fetchone()

    if user:
        id, chat_id, username, nombre_completo, fecha_nacimiento, rol, pais, foto = user
        edad = calcular_edad(fecha_nacimiento)

        perfil = (
            f"✅ *Perfil Registrado*:\n"
            f"\\- *Nombre:* {escape_markdown_v2(nombre_completo)} \\(\\@{escape_markdown_v2(username)}\\)\n"
            f"\\- *Edad:* {escape_markdown_v2(str(edad))} años\n"
            f"\\- *Rol o Hobby:* {escape_markdown_v2(rol)}\n"
            f"\\- *País:* {escape_markdown_v2(pais)}"
        )

        # Se incluye reply_markup=notificacion1 tanto si hay foto como si no la hay
        if foto:
            bot.send_photo(chat_id, foto, caption=perfil, parse_mode="MarkdownV2", reply_markup=notificacion1)
        else:
            bot.send_message(chat_id, f"⚠️ No tienes foto de perfil.\n\n{perfil}", parse_mode="MarkdownV2", reply_markup=notificacion1)
    else:
        sent_message = bot.send_message(chat_id, "No estás registrado❌. Usa /registro para comenzar.")
        try:
            bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("✍️")])
        except Exception:
            pass

def calcular_edad(fecha_nacimiento):
    fecha_nac = datetime.strptime(fecha_nacimiento, "%Y-%m-%d")
    hoy = datetime.today()
    return hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))

@bot.callback_query_handler(func=lambda call: call.data in ["suscribirse", "desuscribirse"])
def manejar_suscripcion(call):
    chat_id = call.message.chat.id
    username = call.from_user.username or "Usuario"
    suscriptores = cargar_suscriptores()

    if call.data == "suscribirse":
        if chat_id not in suscriptores:
            suscriptores.append(chat_id)
            guardar_suscriptores(suscriptores)
            bot.answer_callback_query(call.id, "✅ Te has suscrito.")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
            bot.send_message(chat_id, f"🎉 @{username}, ahora recibirás notificaciones.")
        else:
            bot.answer_callback_query(call.id, "Ya estás suscrito.")

    elif call.data == "desuscribirse":
        if chat_id in suscriptores:
            suscriptores.remove(chat_id)
            guardar_suscriptores(suscriptores)
            bot.answer_callback_query(call.id, "❌ Te has desuscrito.")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
            bot.send_message(chat_id, f"🔕 @{username}, has cancelado tu suscripción.")
        else:
            bot.answer_callback_query(call.id, "No estabas suscrito.")

def usuario_registrado(chat_id):
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE chat_id = ?", (chat_id,))
        return cursor.fetchone() is not None

def acceso_restringido(func):
    def wrapper(message):
        if usuario_registrado(message.chat.id):
            return func(message)
        else:
            sent_message = bot.send_message(
                message.chat.id, "⚠️ Debes registrarte con /registro para usar este comando.", reply_markup=keyboard1)
            try:
                bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("✍️")])
            except Exception:
                pass
    return wrapper

# --- COMANDOS APKS ---

def enviar_info_app(message, key_app):
    apps_data = obtener_config_apps()
    app_info = apps_data.get(key_app)
    if app_info:
        msg = f"📱 <b>{app_info['nombre']}</b>\n\n{app_info['descripcion']}\n\n📥 <b>Enlace de descarga:</b>\n{app_info['url']}"
        sent_message = bot.reply_to(message, msg, parse_mode="HTML", reply_markup=keyboard1)
        try:
            bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("👍")])
        except Exception:
            pass
    else:
        bot.reply_to(message, "❌ No se pudo obtener el enlace de la aplicación.")

@bot.message_handler(commands=["mtmanag"])
@acceso_restringido
def cmd_mtmanag(message):
    enviar_info_app(message, "mtmanager")

@bot.message_handler(commands=["mtmanagbet"])
@acceso_restringido
def cmd_mtmanagbet(message):
    enviar_info_app(message, "mtmanagerbeta")

@bot.message_handler(commands=["apkeditorpro"])
@acceso_restringido
def cmd_apkeditorpro(message):
    enviar_info_app(message, "apkeditorpro")

@bot.message_handler(commands=["apktoolm"])
@acceso_restringido
def cmd_apktoolm(message):
    enviar_info_app(message, "apktoolm")

@bot.message_handler(commands=["pixellab"])
@acceso_restringido
def cmd_pixellab(message):
    enviar_info_app(message, "pixellab")

@bot.message_handler(commands=["telegprem"])
@acceso_restringido
def cmd_telegprem(message):
    enviar_info_app(message, "telegrampremium")

@bot.message_handler(commands=["teamzetpriv"])
@acceso_restringido
def cmd_teamzetpriv(message):
    enviar_info_app(message, "teamzetasprivate")

@bot.message_handler(commands=["base64pro"])
@acceso_restringido
def cmd_base64pro(message):
    enviar_info_app(message, "base64pro")

# FUNCIONES BÚSQUEDA Y MULTIMEDIA

def buscar_imagen(query):
    # 1. Intentar con la API de Google Custom Search primero
    try:
        params = {
            "q": query,
            "cx": SEARCH_ENGINE_ID,
            "key": API_KEY,
            "searchType": "image",
            "num": 3
        }
        response = requests.get(SEARCH_URL, params=params, timeout=10)
        results = response.json()
        
        if "items" in results and len(results["items"]) > 0:
            return results["items"][0]["link"]
    except Exception as e:
        print(f"Error en buscar_imagen con Google API: {e}")
    
    # 2. Respaldo secundario con DDGS
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=3))
            if results:
                return results[0]['image']
    except Exception as e:
        print(f"Error en buscar_imagen respaldo DuckDuckGo: {e}")
        
    return None

def buscar_en_google(query):
    # 1. Intentar con Google Custom Search API
    try:
        params = {
            "q": query, 
            "cx": SEARCH_ENGINE_ID, 
            "key": API_KEY,
            "num": 5
        }
        response = requests.get(SEARCH_URL, params=params, timeout=10)
        results = response.json()
        
        if "items" in results and len(results["items"]) > 0:
            enlaces = "\n\n".join([f"🔹 <b>{item['title']}</b>\n{item['link']}" for item in results["items"][:5]])
            return enlaces
    except Exception as e:
        print(f"Error en la búsqueda con Google API: {e}")

    # 2. Respaldo con DuckDuckGo (DDGS) si Google no entrega resultados
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if results:
                enlaces = "\n\n".join([f"🔹 <b>{res['title']}</b>\n{res['href']}" for res in results])
                return enlaces
    except Exception as e:
        print(f"Error en la búsqueda con DDGS: {e}")

    return "No se encontraron resultados para la búsqueda."

def convertir_a_sticker(image_path):
    try:
        sticker_path = image_path.rsplit('.', 1)[0] + ".webp"
        with Image.open(image_path) as img:
            # Redimensionar manteniendo la relación de aspecto (máximo 512x512)
            img.thumbnail((512, 512))
            img.save(sticker_path, "WEBP")
        return sticker_path
    except Exception as e:
        print(f"Error al convertir imagen a sticker: {e}")
        return None
    

@bot.message_handler(commands=["imagen"])
@acceso_restringido
def cmd_imagen(message):
    chat_id = message.chat.id
    query = message.text.replace("/imagen", "").strip()
    
    if not query:
        bot.reply_to(message, "❌ Debes escribir lo que deseas buscar. Ejemplo: /imagen perro cafe")
        return

    msg_espera = bot.send_message(chat_id, f"🔍 Buscando imagen para: <b>{query}</b>...", parse_mode="HTML")
    imagen_url = buscar_imagen(query)
    
    if imagen_url:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        temp_img = f"img_{chat_id}_{uuid.uuid4().hex[:5]}.jpg"
        try:
            sent_message = bot.send_photo(
                chat_id, 
                imagen_url, 
                caption=f"🖼️ Resultado para: <b>{query}</b>", 
                parse_mode="HTML"
            )
            try:
                bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("⭐")])
            except Exception:
                pass
        except Exception:
            # Respaldo con descarga e inmediatamente borrado del archivo temporal
            try:
                response = requests.get(imagen_url, headers=headers, timeout=12)
                if response.status_code == 200:
                    with open(temp_img, "wb") as f:
                        f.write(response.content)
                    with open(temp_img, "rb") as photo:
                        bot.send_photo(chat_id, photo, caption=f"🖼️ Resultado para: <b>{query}</b>", parse_mode="HTML")
                else:
                    bot.send_message(chat_id, "❌ La imagen fue bloqueada por el servidor de origen.")
            except Exception as download_err:
                bot.send_message(chat_id, "❌ No se pudo descargar ni enviar la imagen.")
            finally:
                borrar_archivo_seguro(temp_img)
    else:
        bot.send_message(chat_id, "❌ No encontré imágenes para esa búsqueda.")
    
    # Limpiar mensaje flotante
    try:
        bot.delete_message(chat_id, msg_espera.message_id)
    except Exception:
        pass

@bot.message_handler(commands=["musica"])
@acceso_restringido
def cmd_musica(message):
    chat_id = message.chat.id
    query = message.text.replace("/musica", "").strip()

    if not query:
        bot.reply_to(message, "❌ Debes escribir el nombre de la canción después de /musica")
        return

    msg_espera = bot.send_message(chat_id, f"🔍 Buscando y descargando: <b>{query}</b>...", parse_mode="HTML")

    unique_id = f"audio_{chat_id}_{uuid.uuid4().hex[:8]}"
    output_template = f"{unique_id}.%(ext)s"
    expected_file = f"{unique_id}.mp3"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "nocachedir": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=True)
            if "entries" in info and len(info["entries"]) > 0:
                video_info = info["entries"][0]
            else:
                bot.send_message(chat_id, "❌ No se encontró ninguna canción con ese nombre.")
                return

            video_title = video_info.get("title", "Música")
            video_url = video_info.get("webpage_url", "N/A")
            thumbnail_url = video_info.get("thumbnail", None)
            
            # Formatear duración (segundos a MM:SS)
            duracion_seg = video_info.get("duration", 0)
            minutos = int(duracion_seg // 60)
            segundos = int(duracion_seg % 60)
            duracion_str = f"{minutos}:{segundos:02d}"

            # Formatear fecha de subida (YYYYMMDD a DD/MM/YYYY)
            upload_date_raw = video_info.get("upload_date", "")
            if len(upload_date_raw) == 8:
                anio = upload_date_raw[:4]
                mes = upload_date_raw[4:6]
                dia = upload_date_raw[6:]
                fecha_subida = f"{dia}/{mes}/{anio}"
            else:
                fecha_subida = "Desconocida"

            # Vistas
            vistas = video_info.get("view_count", 0)
            vistas_str = f"{vistas:,}" if vistas else "Desconocido"

        # 1. Enviar el mensaje con los datos de información de la canción antes de enviar el audio
        info_texto = (
            f"🎵 *INFORMACIÓN DE LA CANCIÓN* 🎵\n\n"
            f"📌 *Título:* {video_title}\n"
            f"📅 *Fecha de subida:* {fecha_subida}\n"
            f"⏱️ *Duración:* {duracion_str}\n"
            f"👁️ *Vistas:* {vistas_str}\n"
            f"🔗 *URL:* {video_url}\n\n"
            f"_Enviando archivo de audio, por favor espera..._"
        )

        if thumbnail_url:
            try:
                bot.send_photo(chat_id, thumbnail_url, caption=info_texto, parse_mode="Markdown")
            except Exception:
                bot.send_message(chat_id, info_texto, parse_mode="Markdown", disable_web_page_preview=False)
        else:
            bot.send_message(chat_id, info_texto, parse_mode="Markdown", disable_web_page_preview=False)

        # 2. Enviar el archivo de audio descargado
        if os.path.exists(expected_file):
            with open(expected_file, "rb") as audio:
                bot.send_audio(chat_id, audio, caption=f"🎵 Aquí tienes tu música: <b>{video_title}</b>", parse_mode="HTML", timeout=180)
        else:
            bot.send_message(chat_id, "❌ Error: No se pudo procesar el archivo descargado.")

    except Exception as e:
        bot.send_message(chat_id, f"❌ Ocurrió un error: {e}")
    finally:
        # Garantizamos la limpieza de cualquier derivado de audio
        borrar_archivo_seguro(expected_file)
        borrar_archivo_seguro(f"{unique_id}.webm")
        borrar_archivo_seguro(f"{unique_id}.m4a")
        try:
            bot.delete_message(chat_id, msg_espera.message_id)
        except Exception:
            pass
        gc.collect()
        

@bot.message_handler(commands=["video"])
@acceso_restringido
def cmd_video(message):
    chat_id = message.chat.id
    query = message.text.replace("/video", "").strip()

    if not query:
        bot.reply_to(message, "❌ Debes escribir el nombre del video después de /video.")
        return

    msg_espera = bot.send_message(chat_id, f"🔍 Buscando y descargando el video: <b>{query}</b>...", parse_mode="HTML")

    unique_id = f"video_{chat_id}_{uuid.uuid4().hex[:8]}"
    output_template = f"{unique_id}.%(ext)s"
    expected_file = f"{unique_id}.mp4"

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "nocachedir": True,
        "quiet": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            if "entries" in info and len(info["entries"]) > 0:
                video_info = info["entries"][0]
            else:
                bot.send_message(chat_id, "❌ No se encontró ningún video con ese nombre.")
                return

            video_title = video_info.get("title", "Video")
            video_url = video_info.get("webpage_url", "N/A")
            thumbnail_url = video_info.get("thumbnail", None)

            # Formatear duración (segundos a MM:SS)
            duracion_seg = video_info.get("duration", 0)
            minutos = int(duracion_seg // 60)
            segundos = int(duracion_seg % 60)
            duracion_str = f"{minutos}:{segundos:02d}"

            # Formatear fecha de subida (YYYYMMDD a DD/MM/YYYY)
            upload_date_raw = video_info.get("upload_date", "")
            if len(upload_date_raw) == 8:
                anio = upload_date_raw[:4]
                mes = upload_date_raw[4:6]
                dia = upload_date_raw[6:]
                fecha_subida = f"{dia}/{mes}/{anio}"
            else:
                fecha_subida = "Desconocida"

            # Vistas
            vistas = video_info.get("view_count", 0)
            vistas_str = f"{vistas:,}" if vistas else "Desconocido"

        # 1. Enviar tarjeta informativa con la miniatura antes de enviar el archivo de video
        info_texto = (
            f"🎬 *INFORMACIÓN DEL VIDEO* 🎬\n\n"
            f"📌 *Título:* {video_title}\n"
            f"📅 *Fecha de subida:* {fecha_subida}\n"
            f"⏱️ *Duración:* {duracion_str}\n"
            f"👁️ *Vistas:* {vistas_str}\n"
            f"🔗 *URL:* {video_url}\n\n"
            f"_Enviando archivo de video, por favor espera..._"
        )

        if thumbnail_url:
            try:
                bot.send_photo(chat_id, thumbnail_url, caption=info_texto, parse_mode="Markdown")
            except Exception:
                bot.send_message(chat_id, info_texto, parse_mode="Markdown", disable_web_page_preview=False)
        else:
            bot.send_message(chat_id, info_texto, parse_mode="Markdown", disable_web_page_preview=False)

        # 2. Enviar el archivo de video procesado
        if os.path.exists(expected_file):
            with open(expected_file, "rb") as video:
                bot.send_video(
                    chat_id, 
                    video, 
                    caption=f"🎥 Aquí tienes tu video: <b>{video_title}</b>", 
                    parse_mode="HTML",
                    timeout=300
                )
        else:
            bot.send_message(chat_id, "❌ Error: No se pudo procesar el archivo de video descargado.")

    except Exception as e:
        bot.send_message(chat_id, f"❌ Ocurrió un error al descargar el video: {e}")
    finally:
        # Eliminación rigurosa de fragmentos temporales creados por yt-dlp al procesar videos
        borrar_archivo_seguro(expected_file)
        borrar_archivo_seguro(f"{unique_id}.f137.mp4")
        borrar_archivo_seguro(f"{unique_id}.f140.m4a")
        borrar_archivo_seguro(f"{unique_id}.temp.mp4")
        try:
            bot.delete_message(chat_id, msg_espera.message_id)
        except Exception:
            pass
        gc.collect()

@bot.message_handler(commands=["aibuscar"])
@acceso_restringido
def cmd_aibuscar(message):
    query = message.text.replace("/aibuscar", "").strip()
    if not query:
        bot.reply_to(message, "❌ Debes escribir un texto después de /aibuscar. Ejemplo: /aibuscar CKan")
        return

    msg_espera = bot.send_message(message.chat.id, f"🔍 Buscando información sobre: <b>{query}</b>...", parse_mode="HTML")
    resultado = buscar_en_google(query)
    
    sent_message = bot.send_message(message.chat.id, resultado, parse_mode="HTML", disable_web_page_preview=True)
    try:
        bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("👍")])
    except Exception:
        pass
        
    try:
        bot.delete_message(message.chat.id, msg_espera.message_id)
    except Exception:
        pass

@bot.message_handler(commands=["aisticker"])
@acceso_restringido
def cmd_aisticker(message):
    chat_id = message.chat.id
    esperando_imagen[chat_id] = True
    sent_message = bot.send_message(chat_id, "Envíame una imagen y la convertiré en un sticker.")
    try:
        bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("❤️")])
    except Exception:
        pass


@bot.message_handler(content_types=["photo"])
def recibir_imagen(message):
    chat_id = message.chat.id

    if chat_id in esperando_imagen and esperando_imagen[chat_id]:
        esperando_imagen[chat_id] = False

        unique_str = uuid.uuid4().hex[:5]
        image_path = f"temp_{chat_id}_{unique_str}.jpg"
        sticker_path = None

        try:
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            with open(image_path, "wb") as f:
                f.write(downloaded_file)

            sticker_path = convertir_a_sticker(image_path)

            if sticker_path and os.path.exists(sticker_path):
                with open(sticker_path, "rb") as st:
                    sent_message = bot.send_sticker(chat_id, st)
                try:
                    bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("⭐")])
                except Exception:
                    pass
            else:
                bot.send_message(chat_id, "❌ Ocurrió un error al crear el sticker.")

        except Exception as e:
            bot.send_message(chat_id, f"❌ Error al procesar imagen: {e}")
        finally:
            borrar_archivo_seguro(image_path)
            borrar_archivo_seguro(sticker_path)
            gc.collect()
    else:
        bot.send_message(chat_id, "Envíame primero el comando /aisticker para crear un sticker.")

# Respuestas automáticas a ciertas palabras clave con saludo dinámico según país y hora
@bot.message_handler(func=lambda message: message.text.lower() in ["Hola", "hola", "ola", "Ola", "Hello", "hello", "Gracias", "gracias", "Thank", "thank", "Adiós", "adiós", "Adios", "adios", "Goodbye", "goodbye", "Bye", "bye"])
def respuestas_automaticas(message):
    username = message.from_user.username or "usuario"
    chat_id = message.chat.id
    texto = message.text.lower()

    # Obtener el país del usuario desde la base de datos SQLite
    pais = "UTC"
    try:
        with obtener_conexion() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pais FROM usuarios WHERE chat_id = ?", (chat_id,))
            resultado = cursor.fetchone()
            if resultado and resultado[0]:
                pais = resultado[0]
    except Exception as e:
        print(f"Error consultando país para saludo: {e}")

    # Extraer la zona horaria correspondiente al país usando el diccionario global
    zona_horaria = ZONAS_HORARIAS_MUNDIAL.get(pais, "Etc/UTC")
    
    # Determinar la hora actual exacta en la zona del usuario
    try:
        zona = pytz.timezone(zona_horaria)
        hora_actual = datetime.now(zona).hour
    except Exception:
        hora_actual = datetime.now().hour

    # Definir el saludo y la despedida según la hora actual
    if 5 <= hora_actual < 12:
        saludo_tiempo = "Buenos días"
        saludo_despedida = "un gran día"
    elif 12 <= hora_actual < 19:
        saludo_tiempo = "Buenas tardes"
        saludo_despedida = "una gran tarde"
    else:
        saludo_tiempo = "Buenas noches"   
        saludo_despedida = "una gran noche"                                                     

    respuestas = {
        "Hola": f"¡{saludo_tiempo} @{username}!, soy NemeSicBot🤖, tu asistente virtual.\n¿En qué te puedo ayudar?\nEjecuta /menu para ver los comandos.",
        "hola": f"¡{saludo_tiempo} @{username}!, soy NemeSicBot🤖, tu asistente virtual.\n¿En qué te puedo ayudar?\nEjecuta /menu para ver los comandos.",
        "ola": f"¡{saludo_tiempo} @{username}!, soy NemeSicBot🤖, tu asistente virtual.\n¿En qué te puedo ayudar?\nEjecuta /menu para ver los comandos.",
        "Ola": f"¡{saludo_tiempo} @{username}!, soy NemeSicBot🤖, tu asistente virtual.\n¿En qué te puedo ayudar?\nEjecuta /menu para ver los comandos.",
        "Hello": f"¡{saludo_tiempo} @{username}!, soy NemeSicBot🤖, tu asistente virtual.\n¿En qué te puedo ayudar?\nEjecuta /menu para ver los comandos.",
        "hello": f"¡{saludo_tiempo} @{username}!, soy NemeSicBot🤖, tu asistente virtual.\n¿En qué te puedo ayudar?\nEjecuta /menu para ver los comandos.",
        "Gracias": f"¡De nada @{username}!, siempre estoy aquí para ayudar. 😊",
        "gracias": f"¡De nada @{username}!, siempre estoy aquí para ayudar. 😊",
        "Thank": f"¡De nada @{username}!, siempre estoy aquí para ayudar. 😊",
        "thank": f"¡De nada @{username}!, siempre estoy aquí para ayudar. 😊",
        "Adiós": f"¡Hasta luego @{username}!, que tengas {saludo_despedida}. 👋",
        "adiós": f"¡Hasta luego @{username}!, que tengas {saludo_despedida}. 👋",
        "Adios": f"¡Hasta luego @{username}!, que tengas {saludo_despedida}. 👋",
        "adios": f"¡Hasta luego @{username}!, que tengas {saludo_despedida}. 👋",
        "Goodbye": f"¡Hasta luego @{username}!, que tengas {saludo_despedida}. 👋",
        "goodbye": f"¡Hasta luego @{username}!, que tengas {saludo_despedida}. 👋",
        "Bye": f"¡Hasta luego @{username}!, que tengas {saludo_despedida}. 👋",
        "bye": f"¡Hasta luego @{username}!, que tengas {saludo_despedida}. 👋"
    }
    
    texto_respuesta = respuestas.get(texto, f"¡Hola @{username}!")

    sent_message = bot.reply_to(message, texto_respuesta)
    try:
        bot.set_message_reaction(sent_message.chat.id, sent_message.message_id, [ReactionTypeEmoji("❤️")])
    except Exception:
        pass


# Iniciar el bot
if __name__ == '__main__':
    try:
        # Llamamos al banner personalizado con colores pro
        mostrar_banner()

        # Mostrar mensaje personalizado
        print(conectado)
        bot.infinity_polling()
    except KeyboardInterrupt:
        print('\nNemeSicBot detenido manualmente.')
    except Exception as e:
        print(f'Error inesperado: {e}')
    finally:
        print('NemeSicBot finalizado..')
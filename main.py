import queue
import sys
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import json
import subprocess
import random 
import os
import time
import asyncio
import edge_tts
import threading 
from datetime import datetime
import hashlib

modelo = Model("vosk-model-small-es")
q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

def limpiar_microfono():
    """Limpia la cola de audio para que Elma no se escuche a sí misma"""
    time.sleep(0.5) # Pausa técnica para que termine el eco
    with q.mutex:
        q.queue.clear()

def hablar(texto):
    """Voz de Laura con velocidad y entonación ajustada"""
    print(f"🗣️ Elma dice: {texto}")
    
    if not os.path.exists("cache_audio"):
        os.makedirs("cache_audio")
        
    hash_texto = hashlib.md5(texto.encode()).hexdigest()
    archivo_wav = f"cache_audio/{hash_texto}.wav"
    
    if not os.path.exists(archivo_wav):
        modelo_piper = "es_MX-laura-high.onnx"
        parametros = "--length_scale 1.2 --noise_scale 0.8 --noise_w 1.0"
        comando_piper = f'export LD_LIBRARY_PATH=. && echo "{texto}" | ./piper --model {modelo_piper} --output_file {archivo_wav} {parametros}'
        
        try:
            subprocess.run(comando_piper, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"❌ Error al generar audio: {e}")
            
    if os.path.exists(archivo_wav):
        # Reproducimos con mpv
        subprocess.run(["mpv", "--no-video", "--no-terminal", archivo_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("❌ El audio no se generó.")
            
    limpiar_microfono()



# Variables de estado globales
# Estados posibles: "INACTIVO", "ESPERANDO_ORDEN", "ESPERANDO_TIEMPO_TIMER"
estado_elma = "INACTIVO"

def cerrar_aplicacion(texto):
    if "todas" in texto or "todo" in texto:
        hablar("Cerrando todo a la verga, pero yo sigo aquí pa ti")
        apps_a_cerrar = ["spotify", "zen-browser", "ghostty", "code", "dbeaver", "cava"]
        for app in apps_a_cerrar:
            subprocess.run(["killall", app], stderr=subprocess.DEVNULL)
        return True
    elif "spotify" in texto or "música" in texto:
        hablar("Cerrando Spotify")
        subprocess.run(["killall", "spotify"], stderr=subprocess.DEVNULL)
        return True
    elif "navegador" in texto or "zen" in texto:
        hablar("Cerrando el navegador")
        subprocess.run(["killall", "zen-browser"], stderr=subprocess.DEVNULL)
        return True
    elif "terminal" in texto or "ghostty" in texto:
        hablar("Cerrando la terminal")
        subprocess.run(["killall", "ghostty"], stderr=subprocess.DEVNULL)
        return True
    elif "visual" in texto or "code" in texto:
        hablar("Cerrando Visual Studio")
        subprocess.run(["killall", "code"], stderr=subprocess.DEVNULL)
        return True
    elif "dbeaver" in texto or "base de datos" in texto:
        hablar("Cerrando DBeaver")
        subprocess.run(["killall", "dbeaver"], stderr=subprocess.DEVNULL)
        return True
    elif "antigravity" in texto:
        hablar("Cerrando Antigravity")
        subprocess.run(["killall", "antigravity"], stderr=subprocess.DEVNULL)
        return True
    elif any(palabra in texto for palabra in ["cancela", "nada", "olvídalo", "olvidalo", "no"]):
        hablar("Sale, no cierro nada.")
        return True
    else:
        hablar("No sé qué aplicación es esa we, dime de nuevo o di cancela.")
        return False

def normalizar_numeros(texto):
    texto = texto.replace("media hora", "30 minutos")
    mapa_numeros = {
        "un": "1", "uno": "1", "una": "1", "dos": "2", "tres": "3", "cuatro": "4", "cinco": "5",
        "seis": "6", "siete": "7", "ocho": "8", "nueve": "9", "diez": "10",
        "once": "11", "doce": "12", "trece": "13", "catorce": "14", "quince": "15",
        "dieciseis": "16", "dieciséis": "16", "veinte": "20", "treinta": "30", 
        "cuarenta": "40", "cincuenta": "50", "sesenta": "60"
    }
    palabras = texto.split()
    for i, palabra in enumerate(palabras):
        if palabra in mapa_numeros:
            palabras[i] = mapa_numeros[palabra]
    return " ".join(palabras)

def ejecutar_comando(texto):
    global estado_elma
    texto = texto.lower()
    
    # --- VOLUMEN ---
    if any(palabra in texto for palabra in ["sube el volumen", "subir volumen", "más volumen", "subele", "súbele"]):
        hablar("Subiendo el volumen")
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%+"])
        subprocess.run(["amixer", "sset", "Master", "10%+"], stderr=subprocess.DEVNULL)
        return True
        
    elif any(palabra in texto for palabra in ["baja el volumen", "bajar volumen", "menos volumen", "bajale", "bájale"]):
        hablar("Bajando el volumen")
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%-"])
        subprocess.run(["amixer", "sset", "Master", "10%-"], stderr=subprocess.DEVNULL)
        return True

    # --- MULTIMEDIA ---
    elif any(palabra in texto for palabra in ["siguiente", "cambia", "next", "pon otra"]):
        hablar("Simon")
        subprocess.run(["playerctl", "next"])
        return True # Volver a dormir
        
    elif "anterior" in texto or "regresa" in texto:
        hablar("Simon")
        subprocess.run(["playerctl", "previous"])
        time.sleep(0.2)
        subprocess.run(["playerctl", "previous"])
        return True

    elif "repite" in texto or "reinicia" in texto:
        hablar("Va de nuez")
        # Mandamos ambos comandos para asegurar
        subprocess.run(["playerctl", "position", "0"])
        subprocess.run(["playerctl", "-p", "spotify", "set-position", "0"])
        subprocess.run(["playerctl", "play"])
        return True
        
    elif any(palabra in texto for palabra in ["pausa", "reproduce", "detén", "continua", "resume", "reproducir"]):
        hablar("Sale")
        subprocess.run(["playerctl", "play-pause"])
        return True
    
    # --- APLICACIONES ---
    elif any(palabra in texto for palabra in ["spotify", "música", "pon spotify", "pon música", "abre spotify", "cumbiones", "rolas"]):
        hablar("Prendiendo el ambiente")
        subprocess.Popen(["spotify"]) 
        subprocess.Popen(["ghostty", "-e", "cava"])
        
        # Hilo para darle PLAY automático en 4 segundos (mientras carga la app)
        def play_spotify():
            time.sleep(4)
            subprocess.run(["playerctl", "-p", "spotify", "play"])
        threading.Thread(target=play_spotify, daemon=True).start()
        return True

    elif "abre el navegador" in texto or "abre zen" in texto or "investiguemos" in texto or "investigar" in texto or "navegador" in texto or "zen" in texto or "navegar" in texto:
        hablar("Abriendo Zen")
        subprocess.Popen(["zen-browser"]) 
        return True

    elif any(palabra in texto for palabra in ["terminal", "abre la terminal", "consola", "abre ghostty"]):
        hablar("Abriendo la terminal")
        subprocess.Popen(["ghostty"])
        return True

    elif any(palabra in texto for palabra in ["visual studio", "abre visual", "abre code", "vscode"]):
        hablar("Abriendo Visual Studio Code")
        subprocess.Popen(["code"])
        return True

    elif "abre antigravity" in texto or "antigravity" in texto:
        hablar("Abriendo Antigravity")
        subprocess.Popen("antigravity", shell=True)
        return True

    elif any(palabra in texto for palabra in ["dbeaver", "base de datos", "abre dbeaver"]):
        hablar("Abriendo DBeaver")
        subprocess.Popen(["dbeaver"])
        return True

    # --- CERRAR APLICACIONES ---
    elif any(palabra in texto for palabra in ["cierra", "cerrar", "matar", "cerremos"]):
        apps_mencionadas = [app for app in ["spotify", "música", "navegador", "zen", "terminal", "ghostty", "visual", "code", "dbeaver", "base de datos", "antigravity", "todas", "todo"] if app in texto]
        if apps_mencionadas:
            cerrar_aplicacion(texto)
            return True
        else:
            hablar("¿Qué quieres que cierre we?")
            estado_elma = "ESPERANDO_APP_CERRAR"
            return False

    # --- SISTEMA ---
    elif any(palabra in texto for palabra in ["bloquea", "lock","regreso","ahorita","ya vuelvo", "seguridad"]):
        hablar("Ok mañana ")
        # Si usas Hyprland es hyprlock, si usas Sway es swaylock.
        # loginctl lock-session es el estándar pero requiere configuración previa.
        subprocess.run(["hyprlock"]) 
        return True

    elif "apaga la compu" in texto or "apágate" in texto:
        hablar("Orale pues, nos vemos padre santo. Descansa.")
        subprocess.run(["systemctl", "poweroff"])
        return True

    # --- INICIO DE TEMPORIZADOR ---
    elif "temporizador" in texto or "alarma" in texto:
        hablar("Simon we, ¿cuánto tiempo we? Dime los minutos.")
        estado_elma = "ESPERANDO_TIEMPO_TIMER"
        return False # No volver a dormir, esperar el tiempo

    elif any(palabra in texto for palabra in ["cancela", "olvídalo", "nada"]):
        hablar("Sobres")
        return True
        
    return False

def procesar_timer(texto):
    global estado_elma
    texto_norm = normalizar_numeros(texto)
    # Extraemos todos los números
    numeros_encontrados = [int(s) for s in texto_norm.split() if s.isdigit()]
    
    if numeros_encontrados:
        tiempo = numeros_encontrados[0]
        if "hora" in texto_norm:
            segundos = tiempo * 3600
            hablar(f"Va, alarma puesta en {tiempo} horas.")
        else:
            segundos = tiempo * 60
            hablar(f"Va, te aviso en {tiempo} minutos.")
        
        # Hilo para que la alarma suene en el futuro sin trabar a Elma
        def alarma():
            time.sleep(segundos)
            hablar("¡Hey padre santo! Ya se cumplió el tiempo.")
        
        threading.Thread(target=alarma, daemon=True).start()
        estado_elma = "INACTIVO" # Volver a esperar el nombre "Elma"
    else:
        hablar("No te entendí el número we, dime cuántos minutos o di cancela.")


intentos_fallidos = 0 # Variable para contar errores

def main():
    global estado_elma, intentos_fallidos
    print("Iniciando los engranes de Elma...")
    recognizer = KaldiRecognizer(modelo, 16000)
    
    alias_elma = ["elma","el na","elna","el más", "el alma", "el mar", "telma", "selma", "delma", "el ma", "e lma", "elm a", "el am", "el mas", "en la", "el una","alma"] 
    frases_despertar = ["¿Qué pasó?", "¿Qué quieres we?", "Dime", "¿Qué tranza?"]
    
    with sd.RawInputStream(samplerate=16000, blocksize=8000, device=None, dtype='int16',
                           channels=1, callback=callback):
        print("🟢 Elma en línea...")
        
        while True:
            data = q.get()
            if recognizer.AcceptWaveform(data):
                resultado = json.loads(recognizer.Result())
                texto = resultado.get("text", "").lower()
                
                if texto.strip():
                    print(f"[Vosk]: {texto}")
                    
                    # --- ESTADO 1: ESPERANDO NOMBRE ---
                    if estado_elma == "INACTIVO":
                        if any(alias in texto for alias in alias_elma):
                            hablar(random.choice(frases_despertar))
                            estado_elma = "ESPERANDO_ORDEN"
                            intentos_fallidos = 0 # Reseteamos al despertar
                            
                            # Si ya viene la orden en la misma frase
                            if ejecutar_comando(texto):
                                estado_elma = "INACTIVO"
                                
                    # --- ESTADO 2: ESPERANDO LA ORDEN ---
                    elif estado_elma == "ESPERANDO_ORDEN":
                        estado_previo = estado_elma
                        
                        if ejecutar_comando(texto):
                            # Si se ejecutó con éxito
                            estado_elma = "INACTIVO"
                            intentos_fallidos = 0
                        elif estado_elma == estado_previo:
                            # Si NO se ejecutó nada Y el estado no cambió (no entró a timer)
                            intentos_fallidos += 1
                            
                            if intentos_fallidos < 2:
                                frases_reintento = [
                                    "No te entendí w, ¿qué dijiste?",
                                    "Repíteme eso, no te capté.",
                                    "¿Mande? Otra vez porfa.",
                                    "¿Qué dijiste wey?, no te entendí."
                                ]
                                hablar(random.choice(frases_reintento))
                            else:
                                hablar("Mejor luego me dices, no te entiendo nada.")
                                estado_elma = "INACTIVO"
                                intentos_fallidos = 0
                                
                    # --- ESTADO 3: ESPERANDO EL TIEMPO DEL TIMER ---
                    elif estado_elma == "ESPERANDO_TIEMPO_TIMER":
                        if "cancela" in texto:
                            hablar("Sale, timer cancelado.")
                            estado_elma = "INACTIVO"
                        else:
                            procesar_timer(texto)
                            
                    # --- ESTADO 4: ESPERANDO_APP_CERRAR ---
                    elif estado_elma == "ESPERANDO_APP_CERRAR":
                        if cerrar_aplicacion(texto):
                            estado_elma = "INACTIVO"

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nApagando a Elma...")
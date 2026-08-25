# Descargador Multimedia (uso local)

Aplicación web local (Flask + yt-dlp) para descargar video o solo audio de
YouTube, TikTok, Instagram y X (Twitter).

> ⚠️ Uso responsable: descarga únicamente contenido del cual tengas los
> derechos o el permiso del titular, o que esté destinado a descarga libre.
> Respeta los Términos de Servicio de cada plataforma y la legislación de
> derechos de autor de tu país. Esta herramienta es para uso personal/local.

## Requisitos

- Python 3.10+ (en este equipo no se detectó Python instalado; instálalo
  desde https://www.python.org/downloads/ marcando "Add python.exe to PATH"
  durante la instalación, o con `winget install Python.Python.3.12`)
- **ffmpeg** en el PATH (necesario para combinar pistas de video/audio y para
  convertir a MP3/WAV/AAC) — ✅ ya detectado en este equipo

### Instalar ffmpeg

**Windows (PowerShell, con winget):**
```powershell
winget install Gyan.FFmpeg
```
Luego cierra y vuelve a abrir la terminal para que se actualice el PATH.

**Windows (con Chocolatey):**
```powershell
choco install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install ffmpeg
```

Verifica la instalación con:
```bash
ffmpeg -version
```

## Instalación

Desde la carpeta `media-downloader`:

```bash
python -m venv venv
```

Activa el entorno virtual:

- Windows (PowerShell): `venv\Scripts\Activate.ps1`
- Windows (cmd): `venv\Scripts\activate.bat`
- macOS/Linux: `source venv/bin/activate`

Instala las dependencias:

```bash
pip install -r requirements.txt
```

## Ejecutar la aplicación

```bash
python app.py
```

Abre el navegador en **http://127.0.0.1:5000**.

## Uso

1. Pega la URL del video (YouTube, TikTok, Instagram o X). La plataforma se
   detecta automáticamente.
2. Elige **Video** o **Solo Audio**.
   - Video: selecciona resolución (144p a 4K, según disponibilidad real del
     contenido original).
   - Solo Audio: selecciona formato (MP3, WAV o AAC).
3. Haz clic en **Descargar**. Verás una barra de progreso y, al finalizar, el
   archivo se descargará automáticamente a tu navegador.

Los archivos se generan temporalmente en `media-downloader/downloads/<job_id>/`
antes de enviarse al navegador.

## Notas técnicas

- Si una resolución solicitada no está disponible para un video en concreto,
  yt-dlp seleccionará automáticamente la más cercana disponible por debajo del
  límite pedido.
- Instagram y X suelen requerir que el contenido sea público; contenido
  privado no podrá descargarse sin autenticación adicional (no incluida en
  esta versión).
- El límite de nombre de archivo se trunca a 150 caracteres para evitar
  errores en sistemas de archivos.

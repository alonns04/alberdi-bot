# Alberdi Bot

## Descripción

Aplicación desarrollada con **Python y Streamlit** para consultar la Constitución Nacional Argentina y otros documentos jurídicos mediante una arquitectura **RAG**.

El sistema recupera fragmentos relevantes desde una base vectorial y genera respuestas contextualizadas mediante la API de **Groq**.

<p align="left">

<a href="#instalacion-y-ejecucion">
<img src="https://img.shields.io/badge/Demo-Local-28A745?logo=googlechrome&logoColor=white&style=for-the-badge" height="40">
</a>

<a href="https://github.com/alonns04/alberdi-bot">
<img src="https://img.shields.io/badge/GitHub-Repositorio-181717?logo=github&logoColor=white&style=for-the-badge" height="40">
</a>

<a href="https://github.com/alonns04/alberdi-bot/tree/main/constitucionbot/src/pdf">
<img src="https://img.shields.io/badge/PDFs-Documentos%20procesados-B85C38?logo=adobeacrobatreader&logoColor=white&style=for-the-badge" height="40">
</a>

<a href="docs/OBTENER_API_KEY_GROQ.md">
<img src="https://img.shields.io/badge/API%20Key-Tutorial-6C5CE7?logo=key&logoColor=white&style=for-the-badge" height="40">
</a>

<a href="https://www.linkedin.com/in/claudiogabrielalonso/">
<img src="https://img.shields.io/badge/LinkedIn-Perfil-0A66C2?logo=linkedin&logoColor=white&style=for-the-badge" height="40">
</a>

</p>

## Sobre el proyecto

**Alberdi Bot** combina búsqueda semántica, documentos jurídicos indexados e inteligencia artificial para responder preguntas sobre la Constitución Nacional en lenguaje natural.

La aplicación utiliza recuperación aumentada por documentos, historial de conversación y una interfaz web construida con Streamlit.

## Objetivo

Facilitar la consulta de material jurídico mediante:

- Preguntas en lenguaje natural.
- Búsqueda semántica sobre documentos indexados.
- Recuperación de fragmentos relevantes.
- Respuestas contextualizadas.
- Conversaciones separadas por chat.

## Funcionalidades

- Chat conversacional sobre la Constitución Nacional.
- Recuperación RAG con ChromaDB.
- Embeddings con Sentence Transformers.
- Integración con modelos de lenguaje de Groq.
- Historial persistente en SQLite.
- Creación de chats nuevos desde la barra lateral.
- Navegación entre Home, Chat y Sobre el proyecto.
- Tema claro y oscuro mediante Streamlit.
- Soporte para documentos PDF y TXT.
- Validación de API key y modelo configurado.

## Módulos

| Módulo | Descripción |
|---|---|
| `app.py` | Interfaz Streamlit, navegación, sesiones y chats. |
| `constitucionbot/config.py` | Rutas, modelo y parámetros RAG. |
| `constitucionbot/pipeline/` | Orquestación de recuperación, contexto, modelo e historial. |
| `constitucionbot/llm/` | Cliente de Groq y construcción de mensajes. |
| `constitucionbot/ingestion/` | Extracción, segmentación y embeddings. |
| `constitucionbot/vectorstore/` | Indexación y consultas en ChromaDB. |
| `constitucionbot/history/` | Persistencia del historial en SQLite. |
| `constitucionbot/prompt_de_entrada/prompt.txt` | Prompt inicial del modelo. |
| `constitucionbot/src/pdf/` | Documentos PDF utilizados como fuente. |
| `constitucionbot/src/txt/` | Documentos de texto disponibles. |
| `constitucionbot/base/chroma_db/` | Base vectorial persistente. |
| `requirements.txt` | Dependencias del proyecto. |

## Tecnologías

### Lenguaje

`Python`

### Framework

`Streamlit`

### Inteligencia artificial

`Groq` · `Sentence Transformers` · `Transformers`

### Recuperación documental

`ChromaDB` · `RAG` · `Embeddings vectoriales`

### Procesamiento de documentos

`PyMuPDF` · `pypdf` · `pytesseract`

### Persistencia

`SQLite` · `JSON`

## Arquitectura

```text
Usuario
   ↓
Streamlit
   ↓
Pregunta y sesión de chat
   ↓
Embedding de la pregunta
   ↓
Consulta semántica en ChromaDB
   ↓
Fragmentos documentales relevantes
   ↓
Contexto + historial + pregunta
   ↓
API de Groq
   ↓
Respuesta en Streamlit
   ↓
Historial en SQLite
```

## Flujo de una consulta

1. El usuario ingresa una pregunta desde Chat.
2. Se identifica la conversación actual.
3. Se genera el embedding de la pregunta.
4. ChromaDB recupera los fragmentos más relevantes.
5. Se carga el historial reciente.
6. Se envían a Groq el prompt, contexto, historial y pregunta.
7. La respuesta se muestra en Streamlit y se guarda en SQLite.

## Instalación y ejecución

### Crear el entorno virtual

```bash
python -m venv venv
```

### Activar el entorno virtual

#### Windows

```bash
venv\Scripts\activate
```

#### Linux / macOS

```bash
source venv/bin/activate
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```

### Ejecutar la aplicación

```bash
streamlit run app.py
```

La aplicación estará disponible en `http://localhost:8501`.

## API key de Groq

Para utilizar el chat es necesario crear una API key de Groq. La creación de la clave es gratuita, de acuerdo con los límites y condiciones vigentes de Groq.

Guía completa: [Cómo obtener una API key de Groq](docs/OBTENER_API_KEY_GROQ.md).

Pasos resumidos:

1. Entrar en [console.groq.com/keys](https://console.groq.com/keys).
2. Iniciar sesión o crear una cuenta.
3. Seleccionar **Create API Key**.
4. Establecer el tiempo de caducidad.
5. Copiar la **Secret Key**.
6. Pegarla en el campo **API key de Groq** de la barra lateral.

También puede configurarse mediante `constitucionbot/.env`:

```env
API_KEY_GROQ=tu_api_key_de_groq
MODEL_GROQ=openai/gpt-oss-20b
```

No compartas la clave ni la subas al repositorio. Si se expone, revocala y generá una nueva desde Groq.

## Configuración RAG

Los parámetros principales se encuentran en `constitucionbot/config.py`:

```python
CHUNK_SIZE = 130
CHUNK_OVERLAP = 15
RAG_TOP_K = 4
RAG_CONTEXT_NEIGHBORS = 0
MAX_TOKENS = 800
```

La base vectorial se almacena en `constitucionbot/base/chroma_db/` y la colección utilizada es `documentos`. La escritura automática del manifiesto está desactivada.

## Historial

El historial se almacena en `constitucionbot/historial/chat.db`. Cada chat mantiene un identificador propio y se recuperan únicamente sus mensajes recientes.

La base se limpia automáticamente cuando supera 1 GiB y se ejecuta `VACUUM` para recuperar espacio.

## Documentos

Los PDFs disponibles pueden consultarse en [Documentos PDF](https://github.com/alonns04/alberdi-bot/tree/main/constitucionbot/src/pdf).

Para agregar documentos compatibles, colocá los archivos en:

```text
constitucionbot/src/pdf/
constitucionbot/src/txt/
```

Luego ejecutá el proceso de indexación correspondiente para incorporarlos a ChromaDB.

## Consideraciones

- La calidad de las respuestas depende de los documentos indexados.
- ChromaDB y SQLite requieren almacenamiento persistente en producción.
- La información generada no reemplaza asesoramiento jurídico profesional.

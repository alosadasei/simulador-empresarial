# Tutor IA para Formación Profesional

Tutor IA para Formación Profesional es una aplicación web basada en **RAG (Retrieval-Augmented Generation)** diseñada para asistir al alumnado utilizando como fuente de conocimiento la documentación proporcionada por el profesorado.

El sistema procesa los materiales docentes, transforma su contenido en información estructurada y genera una base vectorial que permite realizar búsquedas semánticas sobre la documentación disponible.

Además del sistema RAG tradicional, el proyecto incorpora **clasificación de intenciones, expansión inteligente del contexto, árboles de conocimiento, historial de conversación y un modo de aprendizaje guiado paso a paso**.

El objetivo es combinar la capacidad de búsqueda semántica de un sistema RAG con la estructura pedagógica de los materiales docentes, permitiendo tanto realizar preguntas libres como seguir procesos de aprendizaje guiados.

---

# Características principales

El sistema incorpora actualmente las siguientes funcionalidades:

- Aplicación web desarrollada con Flask.
- Interfaz pública para el alumnado.
- Panel específico para el profesorado.
- Gestión de documentos desde la aplicación web.
- Selección de la metodología activa visible para el alumnado.
- Conversión automática de documentos PDF a Markdown mediante Docling.
- Limpieza y normalización del contenido generado.
- Análisis de la estructura jerárquica de los documentos Markdown.
- División automática del contenido en chunks.
- Generación de embeddings mediante `BAAI/bge-m3`.
- Almacenamiento vectorial mediante ChromaDB.
- Recuperación semántica de información mediante RAG.
- Clasificación automática de la intención de las preguntas.
- Extracción de palabras clave para mejorar la recuperación.
- Expansión del contexto recuperado.
- Estrategias específicas de expansión de contexto.
- Generación de árboles de conocimiento a partir de los manuales.
- Asociación entre chunks y nodos del árbol de conocimiento.
- Almacenamiento de los árboles de conocimiento en JSON.
- Historial de conversaciones.
- Construcción dinámica de prompts.
- Prompt específico para el modo de aprendizaje guiado.
- Modo de consulta normal.
- Modo de aprendizaje guiado paso a paso.
- Seguimiento del progreso durante una sesión guiada.
- Generación de respuestas mediante un modelo de lenguaje a través de Groq.
- Sistema de logging para facilitar la depuración y seguimiento del pipeline.
- Arquitectura modular que permite modificar de forma independiente los principales componentes.

---

# Modos de interacción

El chatbot dispone de dos formas principales de interacción con el alumnado:

1. **Consulta normal**
2. **Aprendizaje guiado**

Ambos modos utilizan la documentación disponible como fuente de conocimiento, pero siguen flujos diferentes.

---

## Consulta normal

El modo normal permite realizar preguntas libremente sobre el contenido de una metodología.

Por ejemplo:

```text
¿Qué es Lean Startup?
```

o:

```text
¿Cuáles son los pasos para validar una idea de negocio?
```

El sistema analiza la consulta, recupera los fragmentos más relevantes y construye una respuesta utilizando el contexto obtenido.

El flujo simplificado es:

```text
Pregunta
   │
   ▼
Historial de conversación
   │
   ▼
IntentClassifier
   │
   ▼
Retriever
   │
   ▼
ContextExpander
   │
   ▼
PromptBuilder
   │
   ▼
LLM
   │
   ▼
Respuesta
   │
   ▼
Historial
```

La respuesta generada y la pregunta del alumno se almacenan posteriormente en el historial de la conversación.

---

## Aprendizaje guiado

El modo guiado permite iniciar una sesión de aprendizaje basada en la estructura del árbol de conocimiento correspondiente a la metodología seleccionada.

En este modo, el chatbot no se limita a responder una pregunta aislada, sino que mantiene un estado interno y acompaña al alumno progresivamente a través de los distintos pasos.

El flujo actual es:

```text
modo_guiado=True
        │
        ▼
    GuidedMode
        │
        ▼
  KnowledgeTree
        │
        ▼
    Paso actual
        │
        ▼
     Retriever
        │
        ▼
 ContextExpander
        │
        ▼
GuidedContextBuilder
        │
        ▼
  Prompt guiado
        │
        ▼
       LLM
        │
        ▼
    Respuesta
        │
        ▼
     Progreso
```

`GuidedMode` no conoce ninguna metodología concreta: la estructura de
pasos la prepara `guided_steps.py`, y `GuidedMode` solo gestiona el
progreso del alumno sobre esa lista.

Internamente mantiene un estado con:

```text
activo
pasos_ids
completados
paso_actual
```

El estado inicial del checklist se crea mediante:

```text
GuidedMode.estado_inicial(pasos_ids)
```

Cuando el alumno elige un elemento a trabajar:

```text
GuidedMode.seleccionar_paso(estado, paso_id)
```

Para conocer el nodo del árbol correspondiente al paso seleccionado:

```text
GuidedMode.obtener_paso_actual(estado, arbol)
```

El progreso se gestiona marcando o desmarcando elementos como completados:

```text
GuidedMode.marcar_completado(estado, paso_id)
GuidedMode.desmarcar_completado(estado, paso_id)
```

Es posible consultar en cualquier momento si un elemento está completado o si el modo guiado sigue activo mediante:

```text
GuidedMode.esta_completado(estado, paso_id)
GuidedMode.esta_activo(estado)
```

Cuando comienza una guía, el sistema obtiene el árbol de conocimiento correspondiente a la metodología seleccionada.

Posteriormente, cada paso se combina con los chunks recuperados mediante RAG y con el progreso acumulado para construir un contexto específico mediante `GuidedContextBuilder`.

---

# Arquitectura general

El sistema se divide principalmente en dos grandes procesos:

1. **Ingesta e indexación de documentos**
2. **Consulta y generación de respuestas**

La arquitectura general puede representarse de la siguiente forma:

```text
                         DOCUMENTOS
                             │
                             ▼
                            PDF
                             │
                             ▼
                          Docling
                             │
                             ▼
                       Markdown raw
                             │
                             ▼
                        TextCleaner
                             │
                             ▼
                      Markdown limpio
                             │
                             ▼
                      MarkdownParser
                             │
                             ▼
                       MarkdownNode
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
             Chunker               KnowledgeBuilder
                │                         │
                ▼                         ▼
              Chunks                KnowledgeTree
                │                         │
                └────────────┬────────────┘
                             │
                             ▼
                           Linker
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
             Embeddings             Knowledge JSON
                 │
                 ▼
              ChromaDB
                 │
                 ▼
              Retriever
                 │
                 ▼
          Intent + Context
                 │
                 ▼
           Prompt Builder
                 │
                 ▼
                 LLM
                 │
                 ▼
              Respuesta
```

---

# Pipeline de ingesta e indexación

La indexación transforma los documentos proporcionados por el profesorado en información preparada para ser utilizada posteriormente por el sistema RAG.

El módulo encargado de coordinar este proceso es:

```text
src/ingestion/indexador.py
```

El flujo general es:

```text
PDF
 │
 ▼
Conversión a Markdown
 │
 ▼
Limpieza
 │
 ▼
Carga del documento
 │
 ▼
Parser Markdown
 │
 ├───────────────┐
 ▼               ▼
Chunks      KnowledgeTree
 │               │
 └───────┬───────┘
         ▼
       Linker
         │
         ▼
     Embeddings
         │
         ▼
      ChromaDB
```

---

## 1. Documentos

Los documentos utilizados por el sistema se encuentran en:

```text
documents/
```

Estos documentos constituyen la fuente de conocimiento principal del asistente.  
Si bien el profesor/a tiene la opción de eliminarlos o subir nuevos, el sistema indexaría esos nuevos PDFs, y los pasaría por un proceso de OCR y limpieza automática que no es suficiente para dejarlos realmente limpios en formato MD.

Por ello, los cambios de archivos rompería todas la base del sistema.

Recomendamos no hacerlo a menos que se quiera cambiar toda la jerarquía o los manuales son totalmente otros.

---

## 2. Conversión de PDF a Markdown

Los documentos PDF se convierten automáticamente a Markdown mediante **Docling**.

El módulo responsable es:

```text
src/ingestion/docling_converter.py
```

Los archivos Markdown generados inicialmente se almacenan en:

```text
data/markdown_raw/
```

Trabajar con Markdown permite conservar mejor la estructura del documento, especialmente encabezados, apartados y jerarquías.

---

## 3. Limpieza del contenido

Después de la conversión se ejecuta un proceso de limpieza y normalización.

El módulo responsable es:

```text
src/ingestion/text_cleaner.py
```

Su objetivo es preparar el contenido antes de realizar el chunking y generar los árboles de conocimiento.

Los Markdown procesados se almacenan en:

```text
data/markdown_clean/
```

---

## 4. Carga de documentos

El módulo:

```text
src/ingestion/document_loader.py
```

transforma los archivos procesados en objetos utilizados internamente por el sistema.

Esto permite trabajar con una representación común de los documentos durante las siguientes etapas del pipeline.

---

## 5. Análisis del Markdown

El archivo:

```text
src/ingestion/markdown_parser.py
```

interpreta la estructura jerárquica del Markdown.

A partir de los encabezados y secciones genera una estructura de nodos `MarkdownNode`.

De forma simplificada:

```text
# Tema principal
    │
    ├── ## Sección 1
    │       │
    │       └── ### Subsección
    │
    └── ## Sección 2
```

se transforma en una estructura jerárquica que posteriormente puede utilizarse para crear el árbol de conocimiento.

---

# Chunking

El módulo:

```text
src/ingestion/chunker.py
```

divide el contenido de los documentos en fragmentos o **chunks**.

Los chunks representan las unidades de información que posteriormente serán convertidas en embeddings y almacenadas en la base vectorial.

Cada chunk mantiene metadatos que permiten relacionarlo con su documento original y con la estructura jerárquica correspondiente.

---

# Árboles de conocimiento

Una de las características principales del proyecto es la utilización de árboles de conocimiento.

Los módulos relacionados se encuentran en:

```text
src/knowledge/
```

La estructura actual es:

```text
src/knowledge/
├── builder.py
├── exporter.py
├── linker.py
├── loader.py
└── models.py
```

---

## KnowledgeBuilder

`builder.py` transforma la estructura generada por el parser Markdown en un `KnowledgeTree`.

El árbol representa jerárquicamente el contenido del manual.

Ejemplo conceptual:

```text
Metodología
│
├── Tema 1
│   ├── Concepto 1
│   └── Concepto 2
│
├── Tema 2
│   ├── Paso 1
│   ├── Paso 2
│   └── Paso 3
│
└── Tema 3
```

Esta estructura permite conocer las relaciones existentes entre diferentes partes del contenido.

---

## Linker

El módulo:

```text
src/knowledge/linker.py
```

relaciona los chunks con los nodos del árbol de conocimiento.

La relación es bidireccional conceptualmente:

```text
KnowledgeNode
      ↕
    Chunk
```

Los chunks pueden conocer el nodo al que pertenecen y los nodos pueden mantener referencias a sus chunks.

Esto permite combinar:

- búsqueda semántica;
- posición dentro del manual;
- relaciones jerárquicas;
- contexto relacionado.

---

## Exportación de árboles

Los árboles generados por los distintos niveles de jerarquia de los MD # hasta #####, pueden almacenarse en formato JSON mediante:

```text
src/knowledge/exporter.py
```

Los archivos se almacenan en:

```text
data/knowledge/
```

Actualmente existen árboles de conocimiento para las metodologías utilizadas por el sistema.

Entre los archivos disponibles se encuentran:

```text
lean_startup.json
simulacion_empresarial.json
se_material_complementario.json
```

---

## Carga de árboles

El módulo:

```text
src/knowledge/loader.py
```

permite reconstruir los objetos `KnowledgeTree` a partir de los archivos JSON almacenados.

Los árboles cargados se utilizan posteriormente durante la expansión de contexto y el modo guiado.

---

# Embeddings

Los chunks se convierten en representaciones vectoriales mediante embeddings.

El módulo responsable es:

```text
src/rag/embeddings.py
```

El modelo configurado actualmente es:

```text
BAAI/bge-m3
```

Los embeddings permiten representar semánticamente el contenido de los documentos mediante vectores numéricos.

De esta forma, el sistema puede encontrar fragmentos relacionados con una pregunta aunque no utilicen exactamente las mismas palabras.

---

# Base de datos vectorial

El proyecto utiliza **ChromaDB** como base de datos vectorial.

La lógica relacionada se encuentra en:

```text
src/rag/vector_store.py
```

Los vectores generados durante la indexación se almacenan en:

```text
data/vector_store/
```

Cuando el usuario realiza una pregunta, el sistema puede buscar los chunks cuyos embeddings sean semánticamente más próximos a la consulta.

---

# Retriever

El módulo:

```text
src/rag/retriever.py
```

se encarga de recuperar los candidatos más relevantes desde la base vectorial.

El número inicial de resultados recuperados está configurado mediante:

```python
K_BUSQUEDA = 20
```

Posteriormente, el sistema utiliza diferentes umbrales y criterios para seleccionar el contexto que será utilizado en la respuesta.

---

# Clasificación de intenciones

Antes de construir la respuesta, el sistema analiza la intención de la pregunta mediante:

```text
src/rag/intent_classifier.py
```

El clasificador permite obtener información sobre la consulta, incluyendo:

- intención detectada;
- palabras clave;
- método asociado.

Esta información se utiliza posteriormente para mejorar el tratamiento del contexto.

De forma simplificada:

```text
Pregunta
   │
   ▼
IntentClassifier
   │
   ├── intención
   ├── palabras clave
   └── método
```

La intención forma parte del pipeline RAG y se utiliza junto con los resultados recuperados.

---

# Expansión de contexto

Una búsqueda vectorial puede encontrar un chunk relevante, pero en determinados casos ese fragmento aislado puede no contener todo el contexto necesario.

Para solucionar este problema se utiliza:

```text
src/rag/context_expander.py
```

junto con:

```text
src/rag/context_strategies.py
```

El sistema puede aprovechar las relaciones existentes entre los chunks y los árboles de conocimiento para ampliar la información recuperada.

El flujo conceptual es:

```text
Chunk recuperado
       │
       ▼
KnowledgeTree
       │
       ▼
Nodos relacionados
       │
       ▼
Contexto ampliado
```

Esto permite proporcionar al modelo información más completa y estructurada.

---

# Historial de conversación

El módulo:

```text
src/rag/historial.py
```

gestiona el historial de las conversaciones, almacenado en un único archivo JSON.

Cada instancia del sistema RAG genera un identificador de conversación:

```text
id_conversacion
```

Durante una consulta se recupera el contexto reciente y, después de generar la respuesta, se almacenan:

```text
Pregunta del usuario
        +
Respuesta del asistente
```

Los datos relacionados con el historial se encuentran en:

```text
data/historial_conversaciones.json
```

El acceso al archivo está protegido mediante un lock (`filelock`) para evitar que dos escrituras simultáneas se sobrescriban entre sí.

Esto permite mantener continuidad entre diferentes mensajes de una misma conversación.

---

# Construcción de prompts

El módulo:

```text
src/rag/prompt_builder.py
```

se encarga de construir los prompts que se envían al modelo de lenguaje.

El sistema dispone de diferentes construcciones dependiendo del modo utilizado.

### Modo normal

Combina principalmente:

```text
Historial
+
Pregunta
+
Contexto recuperado
```

### Modo guiado

Utiliza un prompt específico construido a partir de:

```text
Historial
+
Pregunta
+
Contexto guiado
+
Paso actual
+
Progreso
```

La separación entre ambos flujos permite adaptar las instrucciones enviadas al LLM al tipo de interacción que está realizando el alumno.

---

# GuidedContextBuilder

El módulo:

```text
src/rag/guided_context_builder.py
```

construye el contexto específico utilizado durante el modo guiado.

Combina información relacionada con:

- el paso actual;
- los chunks recuperados;
- el progreso de la sesión.

El resultado se utiliza posteriormente para construir el prompt guiado.

---

# Pipeline RAG

El archivo principal que coordina el sistema de recuperación y generación es:

```text
src/rag/rag_pipeline.py
```

La clase `RAG` inicializa y coordina los principales componentes:

```text
Retriever
PromptBuilder
LLMClient
Historial
IntentClassifier
ContextExpander
GuidedMode
GuidedContextBuilder
KnowledgeTree
```

La entrada principal del sistema es:

```python
rag.responder(
    pregunta,
    metodologia,
    modo_guiado=False,
)
```

El parámetro `modo_guiado` permite seleccionar el comportamiento del pipeline.

---

## Flujo normal del RAG

```text
                  PREGUNTA
                     │
                     ▼
                  Historial
                     │
                     ▼
             IntentClassifier
                     │
                     ▼
                 Retriever
                     │
                     ▼
             Chunks candidatos
                     │
                     ▼
             ContextExpander
                     │
                     ▼
            Contexto ampliado
                     │
                     ▼
              PromptBuilder
                     │
                     ▼
                 LLMClient
                     │
                     ▼
                 Respuesta
                     │
                     ▼
                  Historial
```

---

## Flujo guiado del RAG

Cuando:

```python
modo_guiado=True
```

el pipeline comprueba si existe una sesión guiada activa.

Si no existe, se obtiene el árbol correspondiente a la metodología y se inicia una nueva guía.

```text
              modo_guiado=True
                      │
                      ▼
             ¿Guía activa?
                 │         │
                NO         SÍ
                 │         │
                 ▼         │
          KnowledgeTree    │
                 │         │
                 ▼         │
          GuidedMode.estado_inicial()
                 │         │
                 └────┬────┘
                      │
                      ▼
                 Paso actual
                      │
                      ▼
                  Retriever
                      │
                      ▼
              ContextExpander
                      │
                      ▼
          GuidedContextBuilder
                      │
                      ▼
           PromptBuilder guiado
                      │
                      ▼
                     LLM
                      │
                      ▼
                  Respuesta
                      │
                      ▼
                   Progreso
```

Cuando no quedan más pasos, la guía finaliza.

---

# Modelo de lenguaje

La comunicación con el modelo se centraliza en:

```text
src/rag/llm_client.py
```

Actualmente se utiliza el cliente de **Groq**.

El modelo configurado en:

```text
src/core/config.py
```

es:

```text
qwen/qwen3.6-27b
```

La configuración actual utiliza:

```text
temperature = 0
```

para favorecer respuestas más deterministas.

La clave de acceso se obtiene mediante la variable de entorno:

```text
GROQ_API_KEY
```

---

# Aplicación web

La interfaz está desarrollada mediante **Flask**.

El punto de entrada principal es:

```text
app.py
```

La aplicación registra diferentes Blueprints para separar responsabilidades.

```text
web/
├── auth.py
├── profesor.py
├── public.py
├── services/
├── static/
└── templates/
```

---

## Área pública

El archivo:

```text
web/public.py
```

gestiona las rutas de la aplicación y la interacción con el chatbot.

Desde esta interfaz el alumnado realiza consultas al sistema. El chat requiere haber iniciado sesión (cualquier rol): un visitante anónimo es redirigido a `/login`.

---

## Área de profesorado

La aplicación dispone de una sección específica destinada al profesorado.

Los módulos relacionados son:

```text
web/profesor.py
web/auth.py
web/services/
```

Esta parte de la aplicación permite separar las funciones administrativas de la interfaz utilizada por el alumnado.

---

## Usuarios y roles

Las cuentas se guardan en una base de datos **SQLite** (`data/usuarios.db`) gestionada sin ORM mediante el módulo `sqlite3` de la biblioteca estándar.

```text
src/usuarios/
├── modelos.py         # Modelo Usuario y constantes de rol
├── seguridad.py       # Hash bcrypt y validación de DNI, email y fecha
├── repositorio.py     # RepositorioUsuarios: esquema, alta, autenticación y consultas
├── correo.py          # Envío de correo por SMTP (biblioteca estándar)
├── verificacion.py    # RepositorioVerificacion: códigos de un solo uso (tabla parametrizable)
└── restablecimiento.py  # RepositorioRestablecimiento: reutiliza el anterior con su propia tabla

web/services/usuarios.py         # Instancia única del repositorio + utilidades de sesión
web/services/verificacion.py     # Orquesta el código de acceso en dos pasos
web/services/restablecimiento.py # Orquesta el código de "¿Has olvidado tu contraseña?"
```

Cada cuenta tiene los campos `nombre_usuario`, `nombre`, `fecha_nacimiento`, `email` y `dni` (identificador único), además de un `rol` y el hash de la contraseña.

| Rol        | Acceso                                            |
|------------|---------------------------------------------------|
| `usuario`  | Solo la parte pública (chatbot).                  |
| `profesor` | Además, el panel privado de gestión de documentos. |

- **Registro** (`/registro`): crea cuentas con rol `usuario` y redirige a `/login` (no inicia sesión automáticamente).
- **Inicio de sesión** (`/login`): admite nombre de usuario, DNI o email como identificador. Al ser correctos, continúa con la verificación en dos pasos.
- **Profesor inicial**: al arrancar, `app.py` llama a `inicializar_usuarios()`, que crea el esquema y siembra una cuenta de profesor a partir de `USUARIO_PROFESOR` y `CONTRASENA_PROFESOR` (solo si todavía no existe ninguna cuenta de profesor).

La protección de rutas se hace con los decoradores de `web/services/auth.py`: `profesor_requerido` (alias histórico `login_requerido`) para la parte privada y `sesion_requerida` para cualquier usuario autenticado.

### Dos accesos

- **`/login`** (`web/auth.py`) — acceso de alumnado. Puede entrar **cualquier cuenta**, también la de un profesor: en ese caso accede a la parte pública y al chatbot como un alumno más y **nunca aparece en el listado de alumnado** (`/profesor/alumnos` filtra por `rol = usuario`).
- **`/profesorado/acceso`** (`web/profesorado.py`, sin enlaces públicos) — única puerta al panel privado. Una cuenta de alumnado que lo intente recibe "usuario o contraseña incorrectos".

El destino final tras el segundo paso lo decide el acceso por el que se empezó (`origen`, guardado en `verificacion_pendiente`), no el rol: `origen = "profesorado"` lleva al panel; `origen = "alumnado"` lleva siempre a la parte pública.

### Verificación en dos pasos

El acceso tiene dos pasos y **es obligatorio para todas las cuentas** (alumnado y profesorado):

1. `/login` o `/profesorado/acceso` — identificador + contraseña. Si son correctos, se genera un código de 6 dígitos, se guarda con hash bcrypt en la tabla `codigos_verificacion` (caduca a los 10 min, máximo 5 intentos) y se envía por correo.
2. `/login/verificar` — el usuario introduce el código (paso compartido por los dos accesos). Al acertar se completa el inicio de sesión. `/login/reenviar` pide otro código (espera mínima de 60 s entre envíos) y `/login/cancelar` aborta el proceso.

Mientras el código está pendiente, la sesión guarda solo `verificacion_pendiente = {dni, origen}`; el usuario **no** está autenticado hasta introducir el código.

El correo se envía por **SMTP con `smtplib`** (biblioteca estándar), configurado con `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` y `SMTP_TLS` en `.env`. **Si `SMTP_HOST` no está configurado, el inicio de sesión queda bloqueado** (no hay forma de entregar el código); para desarrollo se puede usar un buzón de pruebas como Mailtrap.

### Restablecer contraseña

Ambos accesos (alumnado y profesorado) muestran un enlace **«¿Has olvidado tu contraseña?»** que lleva a un flujo compartido en `web/auth.py`:

1. `/recuperar-contrasena?origen=<alumnado|profesorado>` — el usuario introduce su correo. Se genera un código de un solo uso en la tabla `codigos_restablecimiento` (mismos parámetros que el de acceso: 6 dígitos, 10 min, 5 intentos) y se envía por correo. La respuesta es **siempre la misma exista o no la cuenta** (no se revela qué correos están registrados); además cada puerta solo atiende a su propio rol.
2. `/restablecer-contrasena` — el usuario introduce el código y la contraseña nueva (con confirmación). Al acertar se actualiza el hash y se le redirige al login que corresponda. `/restablecer-contrasena/reenviar` y `/restablecer-contrasena/cancelar` completan el flujo.

El parámetro `origen` (guardado en la sesión como `restablecimiento_origen`) solo sirve para volver al login correcto. Igual que el acceso, **requiere SMTP configurado**.

---

## Conversaciones del chatbot

Las conversaciones de cada usuario se guardan en la misma base de datos SQLite (`data/usuarios.db`), de modo que al volver a entrar puede **retomarlas** donde las dejó.

```text
src/rag/conversaciones_bd.py   # RepositorioConversaciones: tablas, lista, mensajes y estado guiado
```

- Tabla `conversaciones` (`id`, `dni`, `titulo`, `metodologia`, `estado_guiado` en JSON, fechas) y tabla `mensajes` (`rol`, `contenido`, orden). Al borrar un usuario se eliminan en cascada sus conversaciones y mensajes.
- `RepositorioConversaciones` implementa además la interfaz de historial que espera el pipeline RAG (`obtener_contexto`, `agregar_mensaje`…), por lo que se pasa como `historial` a `RAG` y sustituye al antiguo `data/historial_conversaciones.json` para la web.
- **Límite de 5 por usuario**: al pulsar «Nueva conversación» estando en el máximo, se bloquea con un aviso (no se borra nada automáticamente).
- **Lista de conversaciones**: se muestra sobre el chat; cada una se puede seleccionar o eliminar. El título se genera con el primer mensaje del usuario.
- **Reiniciar conversación**: botón en la cabecera del chat que vacía los mensajes y el progreso guiado de la conversación activa, pero la mantiene en la lista.
- El progreso del modo guiado (checklist) se guarda por conversación en la columna `estado_guiado`, no en la sesión.

Rutas nuevas en `web/public.py`: `POST /chat/nueva`, `POST /chat/cambiar`, `POST /chat/reiniciar`, `POST /chat/eliminar`.

---

# Estructura del proyecto

```text
Proyecto-IA-FP/
│
├── app.py
├── requirements.txt
├── README.md
│
├── documents/
│   └── Documentación utilizada por el sistema
│
├── data/
│   ├── historial_conversaciones.json
│   ├── knowledge/
│   │   ├── lean_startup.json
│   │   ├── se_material_complementario.json
│   │   └── simulacion_empresarial.json
│   │
│   ├── markdown_clean/
│   ├── markdown_raw/
│   ├── vector_store/
│   └── logs/
│
├── src/
│   │
│   ├── core/
│   │   ├── aplanar_tablas.py
│   │   ├── config.py
│   │   ├── limpiar_encabezados.py
│   │   └── models.py
│   │
│   ├── ingestion/
│   │   ├── chunker.py
│   │   ├── docling_converter.py
│   │   ├── document_loader.py
│   │   ├── indexador.py
│   │   ├── markdown_parser.py
│   │   └── text_cleaner.py
│   │
│   ├── knowledge/
│   │   ├── builder.py
│   │   ├── exporter.py
│   │   ├── linker.py
│   │   ├── loader.py
│   │   └── models.py
│   │
│   └── rag/
│       ├── context_expander.py
│       ├── context_strategies.py
│       ├── embeddings.py
│       ├── guided_context_builder.py
│       ├── guided_mode.py
        ├── guided_steps
│       ├── historial.py
│       ├── intent_classifier.py
│       ├── llm_client.py
│       ├── prompt_builder.py
│       ├── rag_pipeline.py
│       ├── retriever.py
│       └── vector_store.py
│
├── tests/
│
├── pruebas_codigo/
│
└── web/
    ├── auth.py
    ├── profesor.py
    ├── public.py
    │
    ├── services/
    │   ├── auth.py
    │   └── documentos.py
    │
    ├── static/
    │   └── styles.css
    │
    └── templates/
        ├── chatbot.html
        ├── gestion_documentos.html
        ├── inicio.html
        └── login.html
```

---

# Tecnologías utilizadas

| Tecnología            | Uso                                                                             |
| --------------------- | ------------------------------------------------------------------------------- |
| Python                | Lenguaje principal del proyecto                                                 |
| Flask                 | Aplicación e interfaz web                                                       |
| Jinja2                | Renderizado de plantillas HTML                                                  |
| Docling               | Conversión de documentos PDF a Markdown                                         |
| Sentence Transformers | Generación de embeddings                                                        |
| BAAI/bge-m3           | Modelo de embeddings                                                            |
| ChromaDB              | Base de datos vectorial                                                         |
| Groq                  | Cliente para el modelo de lenguaje                                              |
| Qwen 3.6 27B          | Modelo de lenguaje configurado                                                  |
| NumPy                 | Operaciones numéricas                                                           |
| python-dotenv         | Gestión de variables de entorno                                                 |
| filelock              | Bloqueo de archivos para evitar condiciones de carrera al escribir el historial |

---

# Instalación

## 1. Clonar el repositorio

```bash
git clone <github.com/Violetarki>
cd Proyecto-IA-FP
```

---

## 2. Crear un entorno virtual

```bash
python -m venv venv
```

### macOS / Linux

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

---

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

# Variables de entorno

Para utilizar el modelo de lenguaje es necesario disponer de una clave de Groq.

Puede configurarse mediante un archivo `.env`:

```env
GROQ_API_KEY=tu_clave
```

La aplicación también permite configurar:

```env
FLASK_SECRET_KEY=tu_clave_secreta
USUARIO_PROFESOR=profesor
CONTRASENA_PROFESOR=tu_contraseña
```

No se recomienda almacenar credenciales reales directamente en el código fuente ni subir el archivo `.env` al repositorio.

---

# Configuración principal

Las principales constantes del proyecto se encuentran en:

```text
src/core/config.py
```

Actualmente se utilizan, entre otras:

```python
MODELO_EMBEDDINGS = "BAAI/bge-m3"

K_BUSQUEDA = 20

UMBRAL_EXCELENTE = 0.4
UMBRAL_BUENO = 0.6
UMBRAL_ACEPTABLE = 0.8

MINIMO_CHUNKS = 2
MAXIMO_CHUNKS = 3

MODELO_LLM = "qwen/qwen3.6-27b"
```

Esta centralización permite modificar la configuración principal sin tener que alterar directamente los diferentes módulos del sistema.

---

# Ejecución

El punto de entrada de la aplicación es:

```text
app.py
```

Para iniciar la aplicación:

```bash
python app.py
```

Flask iniciará el servidor de desarrollo y mostrará en la terminal la dirección desde la que puede accederse a la aplicación.

---

# Logging

La aplicación utiliza el módulo `logging` de Python para registrar información sobre su funcionamiento.

Los logs del sistema RAG se almacenan en:

```text
data/logs/rag.log
```

Entre otra información, pueden registrarse:

- intención detectada;
- palabras clave;
- número de candidatos recuperados;
- chunks seleccionados;
- documento de origen;
- posición del chunk;
- distancia semántica;
- construcción del prompt;
- consultas al modelo;
- errores durante el pipeline.

Esto facilita la depuración y evaluación del comportamiento del sistema.

---

# Tests

El proyecto dispone de una carpeta específica para pruebas:

```text
tests/
```

Las pruebas permiten validar de forma independiente diferentes componentes del sistema.

También existe:

```text
pruebas_codigo/
```

donde se almacenan pruebas y experimentos utilizados durante el desarrollo.

---

# Organización modular

El proyecto intenta mantener separadas las responsabilidades de cada componente.

## `src/core`

Configuración y modelos compartidos por la aplicación.

## `src/ingestion`

Procesamiento inicial de los documentos:

```text
PDF → Markdown → limpieza → parser → chunks
```

## `src/knowledge`

Construcción y gestión de los árboles de conocimiento.

## `src/rag`

Sistema de recuperación y generación:

```text
Embeddings
Retriever
IntentClassifier
ContextExpander
Historial
PromptBuilder
GuidedMode
LLMClient
```

## `web`

Interfaz web y rutas Flask.

## `tests`

Pruebas automatizadas.

## `pruebas_codigo`

Experimentos y pruebas realizadas durante el desarrollo.

---

# Flujo completo del sistema

De forma resumida, el funcionamiento completo puede representarse así:

```text
                        PROFESOR
                           │
                           ▼
                       Documentos
                           │
                           ▼
                          PDF
                           │
                           ▼
                        Docling
                           │
                           ▼
                        Markdown
                           │
                           ▼
                        Limpieza
                           │
                           ▼
                    MarkdownParser
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
           Chunker               KnowledgeTree
              │                         │
              └────────────┬────────────┘
                           ▼
                         Linker
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
          Embeddings              Knowledge JSON
              │
              ▼
           ChromaDB
              │
              │
              │
           ALUMNO
              │
              ▼
           Pregunta
              │
              ▼
       IntentClassifier
              │
              ▼
          Retriever
              │
              ▼
       ContextExpander
              │
              ▼
       ¿Modo normal o guiado?
              │
        ┌─────┴─────┐
        │           │
        ▼           ▼
     Normal       Guiado
        │           │
        │      GuidedMode
        │           │
        │     KnowledgeTree
        │           │
        │ GuidedContextBuilder
        │           │
        └─────┬─────┘
              ▼
        PromptBuilder
              │
              ▼
          LLMClient
              │
              ▼
             Groq
              │
              ▼
       Qwen 3.6 27B
              │
              ▼
          Respuesta
              │
              ▼
          Historial
```

---

# Objetivo del proyecto

El objetivo del proyecto es desarrollar un **asistente educativo inteligente para Formación Profesional** capaz de responder utilizando documentación específica proporcionada por el profesorado.

A diferencia de un chatbot generalista, el sistema utiliza una base de conocimiento construida a partir de los materiales docentes.

La combinación de:

- Retrieval-Augmented Generation;
- embeddings;
- búsqueda semántica;
- clasificación de intenciones;
- expansión de contexto;
- árboles de conocimiento;
- historial de conversación;
- aprendizaje guiado;

permite ofrecer una experiencia adaptada tanto a consultas concretas como a procesos de aprendizaje estructurados.

El diseño modular facilita además la evolución del proyecto y la incorporación de nuevas estrategias de recuperación, modelos de embeddings, proveedores de LLM o metodologías educativas.

---

# Licencia

Proyecto desarrollado con fines educativos.

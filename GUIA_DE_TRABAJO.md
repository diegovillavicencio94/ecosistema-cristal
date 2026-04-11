# Guía de trabajo — Cómo usar este Claude Project

## ¿Qué es este Project?

Este Claude Project tiene toda la memoria del Ecosistema de Cristal cargada. No necesitas re-explicar el contexto en cada conversación. Puedes entrar directamente a trabajar.

---

## Cómo iniciar cada sesión

### Opción A — Continuar donde lo dejaste
```
Continuamos. Último estado: [describe brevemente dónde quedaste].
Hoy quiero avanzar con [archivo o tarea concreta].
```

### Opción B — Sesión de debugging
```
Tengo un error al ejecutar [archivo].
Este es el error: [pega el error completo].
```

### Opción C — Sesión de revisión / decisión
```
Antes de continuar con el código, quiero revisar 
si la arquitectura de [componente] tiene sentido.
```

### Opción D — Subir un PDF de prueba
```
Aquí está el PDF de prueba. Testea el módulo actual con él.
[adjunta el archivo]
```

---

## Orden de construcción recomendado

Sigue este orden. No saltes pasos — cada módulo depende del anterior.

### Bloque 1: Ingesta (transformar PDFs en vectores)
```
Paso 1  →  ingestion/pdf_extractor.py
Paso 2  →  ingestion/normalizer.py
Paso 3  →  ingestion/chunker.py
Paso 4  →  ingestion/embedder.py
✓ TEST: subir un PDF real y verificar que aparece en Qdrant dashboard
```

### Bloque 2: RAG (responder preguntas)
```
Paso 5  →  rag/retriever.py
Paso 6  →  rag/llm.py
Paso 7  →  rag/chain.py
✓ TEST: hacer una pregunta por terminal y ver respuesta con fuente citada
```

### Bloque 3: Orquestación
```
Paso 8  →  pipeline.py
✓ TEST: correr pipeline.py --ingest y pipeline.py --query desde CLI
```

### Bloque 4: Interfaz
```
Paso 9  →  interface/app.py
✓ TEST: demo completa en Streamlit
```

---

## Comandos útiles que usarás constantemente

```bash
# Arrancar Qdrant (hazlo siempre al iniciar sesión de desarrollo)
docker compose up -d

# Ver si Qdrant está corriendo
docker ps

# Dashboard Qdrant (ver colecciones y vectores)
# Abre en el navegador:
http://localhost:6333/dashboard

# Instalar dependencias (solo la primera vez o al añadir nuevas)
pip install -r requirements.txt

# Testear un módulo individualmente
python ingestion/pdf_extractor.py
python ingestion/chunker.py
# etc.

# Correr el pipeline completo (cuando esté listo)
python pipeline.py --ingest       # cargar PDFs
python pipeline.py --query "tu pregunta aquí"   # hacer consulta

# Ver logs de Qdrant si algo falla
docker logs ecosistema-cristal-qdrant
```

---

## Cómo subir archivos de prueba

1. Pon tus PDFs en la carpeta `data/raw/` del proyecto
2. En la conversación del Project, adjunta el PDF
3. Escribe: *"Testea pdf_extractor.py con este archivo"*

---

## Cómo documentar el avance (DEVLOG)

Al final de cada sesión donde hayas avanzado código, pide:
```
Genera el bloque de sesión de hoy para el DEVLOG.
```

Luego copia ese bloque al archivo `DEVLOG.md` en tu carpeta local.

---

## Cuándo crear una nueva conversación vs continuar en la misma

| Situación | Qué hacer |
|---|---|
| Continuar con el siguiente archivo del orden | Nueva conversación en el Project |
| Debuggear algo del archivo actual | Continuar en la misma conversación |
| Revisar arquitectura o tomar decisión de diseño | Nueva conversación, empieza con "Quiero revisar..." |
| El contexto de la conversación se hace muy largo | Nueva conversación, empieza con "Continuamos desde paso X" |

---

## Checklist antes de cerrar una sesión

- [ ] El archivo creado tiene su bloque de test (`if __name__ == "__main__"`)
- [ ] Lo has ejecutado y funciona sin errores
- [ ] Has generado el bloque de DEVLOG
- [ ] Sabes exactamente cuál es el siguiente paso

---

## Cuando el equipo aúne avances (cada sprint)

Trae al Project:
```
Sprint [N] completado. Estos son los avances del equipo:
- [describe qué hizo cada miembro]
Necesito revisar cómo integrar [componente X] con lo que yo he construido.
```

El Project te ayudará a identificar conflictos de arquitectura y proponer la integración.

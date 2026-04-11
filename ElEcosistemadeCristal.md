# El Ecosistema de Cristal
## Plataforma de Transparencia Ciudadana impulsada por IA
**De la exploración macro a la definición algorítmica**

* **Contexto del Proyecto:** AI Challenge · Sprint 2
* **Fecha:** Abril 2026
* **Equipo 1:** Paula · Diego · Klaus · Edgar · Ginés · Mamen

---

### El Problema
El dinero público desaparece en silencio. La ineficiencia ahoga el sistema y todo permanece oculto bajo montañas de datos intraducibles. Los datos existen y son públicos, pero la barrera técnica impide su fiscalización. 

* **600.000M€:** Gasto público anual en España.
* **101%:** Deuda pública sobre el PIB.
* **60.000M€:** Ahorro potencial (media OCDE).

Dos barreras estructurales bloquean la fiscalización:
1.  **La Barrera de Complejidad (Presupuestos incomprensibles):** Los datos existen, pero la jerga técnica y la estructura contable impiden a la ciudadanía comparar gastos o entender el destino de los fondos.
2.  **La Invisibilidad del Fraude (Adjudicaciones anómalas invisibles):** El volumen diario de contratos es tan masivo que las irregularidades pasan desapercibidas. Las auditorías actuales son manuales y llegan tarde.

---

### La Solución: Una plataforma de IA con dos motores
La Plataforma de Transparencia Ciudadana opera como un ecosistema dual para erradicar el malgasto. 

**1. Motor de Explicación Presupuestaria (Reto 1: El Guía Experto)**
* **Tecnología:** RAG + LLM.
* **Objetivo:** Traducir la complejidad contable a lenguaje natural accesible para la ciudadanía. Domina el inventario histórico, acompaña al visitante y traduce datos áridos a explicaciones claras, coloquiales y accesibles.
* **Input / Output:** Consulta en lenguaje natural → Respuesta coloquial + gráficos.

**2. Motor de Análisis de Licitaciones (Reto 2: El Circuito de Seguridad)**
* **Tecnología:** Machine Learning.
* **Objetivo:** Vigilancia pasiva y detección temprana de banderas rojas en el ecosistema de contratos. Vigila silenciosamente en segundo plano procesando millones de interacciones para detectar automáticamente movimientos sospechosos o irregulares.
* **Input / Output:** Flujo masivo de contratos → Alertas tempranas + Dashboard.

---

### Metodología de 4 Fases (Sprint 2)
* **1. Investigación:** Soluciones existentes similares en transparencia pública.
* **2. Identificación:** Herramientas de IA disponibles para nuestros retos.
* **3. Pruebas:** Evaluación de funcionalidad, coste y compatibilidad.
* **4. Selección:** Decisión final con justificación técnica.

---

### Fase 1: Investigación de Soluciones Existentes

**Transparencia presupuestaria**
* **OpenBudgets.eu:** Portal europeo de visualización presupuestaria y referencia para accesibilidad ciudadana.
* **Gobierto (España):** Herramienta usada por ayuntamientos españoles para publicar presupuestos de forma visual e interactiva, integrando ejecución presupuestaria.
* **Civio / Dónde van mis impuestos:** ONG española que combina scraping de datos públicos con visualización, siendo referente nacional en transparencia fiscal.
* **dBrain+ (Corea del Sur):** Sistema nacional con IA para análisis fiscal en tiempo real que integra 63 sistemas de 46 instituciones (Modelo de referencia OCDE).
> **Conclusión:** Existen plataformas de visualización, pero ninguna ofrece RAG conversacional sobre presupuestos en España.

**Detección de fraude**
* **Alice (Brasil):** Sistema IA del CGU brasileño que analiza 191.000 adquisiciones/año, reduce auditorías de 400 a 8 días, e identificó 40 tipologías de riesgo, suspendiendo licitaciones por 1.500M€.
* **Dozorro (Ucrania):** Plataforma de feedback con IA integrada en ProZorro, logrando +26% de detección de selección injusta y +298% en colusión, con 30.000 usuarios.
* **ETHIX (Latam):** Startup GovTech que utiliza LLMs para analizar documentos legales a escala, activa en más de 10 instituciones en Chile, Perú, Colombia y México.
* **CMA ML Tool (UK):** Herramienta ML de la Competition and Markets Authority que escanea datos de licitaciones para detectar bid-rigging con contratos de más de £300bn bajo escrutinio.
> **Conclusión:** Existen sistemas exitosos y precedentes parciales, pero ninguno cubre el ecosistema específico español (PLACE, BORME, portales CCAA) ni integra explicación + vigilancia en un ecosistema dual.

---

### Fases 2-3: Comparativas y Selección

**1. Modelos LLM**
*(Criterios: Capacidad en español, coste, contexto largo, fidelidad a datos)*

| Modelo | Contexto | Español | Coste | RAG |
| :--- | :--- | :--- | :--- | :--- |
| GPT-4o (OpenAI) | 128K | Excelente | Alto | Muy bueno |
| **Claude Sonnet 4 (Anthropic)** | **200K** | **Excelente** | **Medio** | **Excelente** |
| Gemini 1.5 Pro | 1M | Bueno | Medio | Bueno |
| Llama 3.1 70B | 128K | Bueno | Bajo* | Bueno |

* **Selección:** Claude Sonnet 4 (Anthropic).
* **Justificación:** Mejor equilibrio entre capacidad de contexto (200K tokens), fidelidad a las fuentes en RAG, excelente español y coste competitivo. Su política de no alucinación es crítica para un sistema que debe citar fuentes oficiales con precisión.

**2. Bases de Datos Vectoriales**
*(Criterios: Escalabilidad, filtrado híbrido, latencia, open source)*

| Vector Store | Tipo | Filtros | Escalabilidad | Coste |
| :--- | :--- | :--- | :--- | :--- |
| Pinecone | Cloud | Bueno | Excelente | Alto |
| Weaviate | Self-hosted/Cloud | Excelente | Muy bueno | Medio |
| **Qdrant** | **Self-hosted/Cloud** | **Excelente** | **Muy bueno** | **Bajo** |
| ChromaDB | Local/Embed | Básico | Limitado | Gratis |
| pgvector | Extensión PostgreSQL | SQL nativo | Bueno | Bajo |

* **Selección:** Qdrant.
* **Justificación:** Combina excelente filtrado híbrido (semántico + metadatos) con posibilidad de self-hosting (control de datos públicos), alto rendimiento y coste bajo. Es crítico para filtrar por año, administración, código COFOG y rango de importes.

**3. Modelos de Embeddings**
*(Criterios: Calidad semántica en español, dimensionalidad, coste por token)*

| Modelo | Proveedor | Dimensiones | Español | Coste |
| :--- | :--- | :--- | :--- | :--- |
| **text-embedding-3-large** | **OpenAI** | **3072** | **Excelente** | **Medio** |
| text-embedding-3-small | OpenAI | 1536 | Muy bueno | Bajo |
| multilingual-e5-large | HuggingFace | 1024 | Excelente | Gratis* |
| voyage-large-2 | Voyage AI | 1536 | Muy bueno | Alto |

* **Selección:** text-embedding-3-large (OpenAI).
* **Justificación:** Su mayor dimensionalidad (3072) captura mejor los matices semánticos de la jerga presupuestaria, ofreciendo un excelente rendimiento en español y buena relación calidad-precio. Una alternativa viable si se prioriza self-hosting es multilingual-e5-large.

**4. Frameworks RAG**
*(Criterios: Madurez, comunidad, integración con LLMs, facilidad de uso)*

| Framework | Madurez | Comunidad | Flexibilidad | Curva |
| :--- | :--- | :--- | :--- | :--- |
| **LangChain** | **Alta** | **Muy grande** | **Muy alta** | **Media** |
| LlamaIndex | Alta | Grande | Alta | Media |
| Haystack | Alta | Media | Alta | Alta |
| DIY (custom) | N/A | N/A | Total | Alta |

* **Selección:** LangChain.
* **Justificación:** Es el ecosistema más maduro con la mayor comunidad activa, permitiendo integración nativa con Claude, Qdrant y múltiples fuentes de datos. Posee módulos pre-construidos para retrieval híbrido, re-ranking y chain-of-thought, además de extensa documentación y casos de uso similares.

---

### Pipelines Técnicos

**Pipeline Reto 1: El Guía Experto (RAG)**
Diseñado para la traducción de la complejidad contable a lenguaje ciudadano.

**Pipeline Reto 2: El Circuito de Seguridad (ML)**
* **1. Ingesta masiva:** Conexión vía streaming o micro-lotes a fuentes gubernamentales. Herramientas: Scrapy + Kafka, Playwright, Airbyte.
* **2. Procesamiento (ETL):** Limpieza automatizada, resolución de entidades y creación de variables. Herramientas: Airflow + dbt, Prefect, Dagster.
* **3. Modelado ML:** Algoritmos de agrupación y evaluación de redes. Modelos: IsoForest + GNN, Autoencoder, Rule-based only.
* **4. Sistemas de alertas:** Almacenamiento en BBDD vectorial. Sistemas: LangChain + Qdrant, LlamaIndex + FAISS, Haystack + Weaviate.
* **Output Final:** Alertas de riesgo + Visualización de redes anómalas + Informes automáticos.

---

### Stack Tecnológico Estratégico
Arquitectura modular, cloud-native y libre de bloqueos legacy.

* **Capa 4: Frontend:** Streamlit (Prototipado) | React.js (Producción).
* **Capa 3: Inteligencia Artificial:** RAG: LangChain | LLM: Claude Sonnet 4 | ML: Scikit-learn, XGBoost, Isolation Forest, PyTorch Geometric (GNN).
* **Capa 2: Bases de Datos:** Relacional: PostgreSQL | Vectorial: Qdrant | Búsqueda: Elasticsearch.
* **Capa 1: Infraestructura:** Cloud: AWS/GCP | Contenedores: Kubernetes | Orquestación: Airflow + dbt | Streaming: Kafka | Scraping: Scrapy.

---

### Detección de Anomalías: Isolation Forest
El algoritmo no busca el fraude predefinido; busca el dato que requiere menos cortes para ser aislado.

* **El Estándar (Clustering):** El 99% de los contratos siguen patrones lógicos de plazos, presupuestos y adjudicatarios, y el algoritmo agrupa esta normalidad.
* **La Anomalía (Árbol Aislado):** Isolation Forest busca el dato que requiere menos cortes para ser aislado del resto.
* **El Resultado (Bandera Roja):** Una adjudicación a una empresa recién creada, con plazo anormalmente corto, se ilumina instantáneamente.

**Tipos de Banderas Rojas a detectar:**
* **Precio atípico:** Importe fuera de rango para su categoría CPV.
* **Proveedor novel:** Empresa creada poco antes de la adjudicación.
* **Concentración:** Alta repetición de adjudicatario en el organismo.
* **Plazos sospechosos:** Adjudicación en festivo o fin de ejercicio.
* **Red de empresas:** Administradores compartidos entre licitadoras.
* **Fraccionamiento:** Importes justo por debajo del umbral legal.

---

### Directrices de Gobernanza del Sistema RAG
Criterios estrictos para limitar el conocimiento del LLM y mitigar riesgos de alucinación.

| Qué Incluir | Qué Excluir |
| :--- | :--- |
| ✓ Bases de datos estructuradas (JSON/CSV) | ✗ PDFs escaneados sin OCR perfecto |
| ✓ Memorias justificativas oficiales | ✗ Leyes generales masivas (solo extractos) |
| ✓ Glosarios contables de la administración | ✗ Históricos obsoletos pre-cambios normativos |
| ✓ Metadatos con jerarquía presupuestaria estricta | ✗ Datos personales (PII) irrelevantes |
| ✓ Anuncios y resoluciones de PLACE/TED | ✗ Documentos de opinión/análisis de terceros |
| ✓ Pliegos de condiciones técnicas | ✗ Fuentes no oficiales o de dudosa procedencia |

---

### Matriz de Contraste Analítico
Distinción de arquitecturas según el reto cívico.

| Dimensión | Motor A (Reto 1) | Motor B (Reto 2) |
| :--- | :--- | :--- |
| **Objetivo** | Explicación y Accesibilidad | Auditoría y Vigilancia |
| **Analogía** | El Guía del Museo | La Cámara de Seguridad |
| **Paradigma IA** | IA Generativa (LLM) | IA Predictiva/Analítica (ML) |
| **Naturaleza de Ingesta** | Documental (presupuestos, textos) | Transaccional (flujo de licitaciones) |
| **Output Final** | Chat interactivo + gráficos | Alertas de riesgo + redes anómalas |
| **Métricas** | Viabilidad 5/5 \| Escal. 5/5 | Impacto 5/5 \| Viabilidad 4/5 |

---

### Visión y Roadmap
Transformando el dinero público de una caja negra a un ecosistema de cristal. El Guía explica, la Cámara vigila y la ciudadanía recupera el control.

* **Auditoría Continua:** De la revisión post-mortem a la vigilancia pasiva en tiempo real.
* **Traducción Ciudadana:** De la opacidad contable al diálogo abierto y accesible.
* **Escalabilidad Inmediata:** Tecnología nativa construida sobre datos públicos, sin alterar sistemas legacy.

La transparencia moderna no es solo publicar datos; es hacerlos comprensibles e inquebrantables.

**Roadmap de Implementación:**
* **Sprint 2 (Sem. 3-6):** MVP con conectores PLACE + BORME, modelo de anomalías de precio, dashboard básico, chat RAG v1.
* **Sprint 3 (Sem. 7-10):** Motor de grafos (redes de empresas), módulo LSTM temporal, gráficos D3.js, comparativas.
* **Sprint 4 (Sem. 11-14):** 47 reglas GRECO/OLAF completas, API pública, informes automáticos, corpus municipal.
* **Sprint 5 (Sem. 15-18):** Integración TED (fondos UE), widget embebible, Eurostat, modo accesible (WCAG).
* **Producción (Mes 5+):** Despliegue K8s, piloto con 3 ayuntamientos, acuerdo IGAE/MINHAP para validación.
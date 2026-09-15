# Evidencias de validación de SentinelAI

Esta carpeta contiene la evidencia visual y técnica utilizada para demostrar el funcionamiento real de SentinelAI.

Las pruebas automatizadas validan el comportamiento del sistema de manera determinística, mientras que las evidencias de esta carpeta documentan ejecuciones reales contra servicios externos cuando corresponde.

---

## 1. Objetivo

La evidencia permite demostrar aspectos que no quedan completamente representados únicamente mediante código o tests automatizados, entre ellos:

- ejecución real del workflow multiagente;
- trazabilidad de LangGraph;
- llamadas reales al proveedor LLM;
- ciclos correctivos;
- uso del Verification Agent;
- composición posterior a la verificación;
- tokens y latencia;
- identificación del proveedor y modelo;
- correlación mediante trace ID.

---

## 2. Evidencia de LangSmith

Durante el desarrollo se realizó una ejecución real completa con observabilidad habilitada.

### Ejecución principal

```text
thread_id:
e2e-langsmith-003
```

```text
trace_id:
01a0a371-1847-7230-b3b4-e73fa5ceaa50
```

Proveedor observado:

```text
Groq
```

Modelo:

```text
openai/gpt-oss-20b
```

La ejecución finalizó correctamente y produjo una respuesta verificada.

---

## 3. Secuencia multiagente observada

La traza mostró una secuencia equivalente a:

```text
sentinel_query
|
|-- supervisor
|-- procedure_agent
|-- supervisor
|-- incident_analyst
|-- supervisor
|-- verification_agent
|
|-- supervisor
|-- procedure_agent
|-- supervisor
|-- incident_analyst
|-- supervisor
|-- verification_agent
|
|-- supervisor
`-- response_composer
```

La existencia de dos ejecuciones de:

```text
procedure_agent
incident_analyst
verification_agent
```

demuestra un ciclo correctivo real.

La primera verificación determinó que la evidencia disponible no era suficiente.

El workflow realizó una nueva recuperación antes de volver a analizar y verificar.

---

## 4. Aspectos demostrados por la traza

La ejecución real permite demostrar:

### Routing dinámico

El Supervisor interviene entre agentes y determina la siguiente transición.

### Multi-step agents

La respuesta no se obtiene mediante una única llamada al modelo.

### Corrective cycle

El sistema vuelve a recuperación cuando la evidencia inicial resulta insuficiente.

### Verification before composition

El Response Composer aparece después de una verificación aprobada.

### Observabilidad

Cada etapa puede inspeccionarse como span individual.

### Correlación

El workflow puede identificarse mediante:

```text
thread_id
trace_id
```

---

## 5. Métricas observadas

Durante la ejecución se observaron aproximadamente:

```text
Duración total: ~82 segundos
Tokens: ~16.8K
Costo estimado: ~$0.0022
```

Estas métricas corresponden a una ejecución real con ciclo correctivo.

No deben interpretarse como métricas de rendimiento promedio del sistema.

---

## 6. Metadata observada

La interfaz de LangSmith mostró metadata relacionada con:

```text
llm_provider = groq
Python = 3.12.10
LangSmith = 0.12.4
```

También se observaron datos de:

- duración;
- tokens de entrada;
- tokens de salida;
- llamadas al modelo;
- spans;
- modelo utilizado;
- ejecución de agentes.

---

## 7. Capturas recomendadas

Las capturas visuales deben permitir verificar al menos:

```text
01 - Vista general del trace sentinel_query
02 - Waterfall completo de agentes
03 - Primer Verification Agent
04 - Ciclo de nueva recuperación
05 - Segunda verificación y Response Composer
06 - Tokens, duración y costo
07 - Metadata de proveedor/modelo
```

No es obligatorio utilizar exactamente siete imágenes si una misma captura demuestra varios puntos.

---

## 8. Convención de nombres

Las capturas pueden almacenarse con nombres como:

```text
langsmith-01-trace-overview.png
langsmith-02-agent-waterfall.png
langsmith-03-verification-cycle.png
langsmith-04-final-composition.png
langsmith-05-metrics.png
```

Los nombres deben describir claramente qué demuestra cada imagen.

---

## 9. Evidencia de tests automatizados

Última ejecución local completa:

```text
119 passed
```

Comando:

```powershell
python -m pytest -q
```

Los tests incluyen categorías:

```text
unit
integration
e2e
```

Los escenarios end-to-end cubren:

- ejecución multiagente;
- ciclo correctivo;
- Supervisor dinámico;
- persistencia;
- Safe Response.

---

## 10. Evidencia de calidad estática

Última ejecución:

```text
All checks passed!
```

Comando:

```powershell
python -m ruff check .
```

---

## 11. Evidencia de RAG

La ingesta real fue ejecutada localmente.

Resultado:

```text
Ingested 154 chunks from 8 documents.
```

La colección persistida mantuvo:

```text
154 puntos
```

después de repetir la ingesta.

Esto demuestra idempotencia del pipeline.

---

## 12. Evaluación del retrieval

Resultados medidos:

| Estrategia | MRR |
| --- | ---: |
| Dense | 0.850 |
| BM25 | 0.750 |
| RRF | 0.900 |
| RRF + ColBERT | 0.900 |

La estrategia predeterminada seleccionada es RRF.

---

## 13. Docker

La configuración de Docker se encuentra implementada mediante:

```text
Dockerfile
docker-compose.yml
run.sh
run.ps1
```

En la máquina utilizada durante el desarrollo no se encontraba instalado Docker.

Por lo tanto:

```text
Configuración Docker: validada estáticamente
Ejecución Docker real: pendiente
```

No se presenta la ejecución del contenedor como evidencia completada hasta realizar una prueba real en un entorno compatible.

---

## 14. Política de evidencia

La carpeta `evidence/` debe contener únicamente material verificable.

No deben agregarse:

- capturas simuladas;
- métricas inventadas;
- resultados no ejecutados;
- credenciales;
- API keys;
- contenido sensible de archivos `.env`.

Las evidencias deben corresponder a ejecuciones reales del proyecto.

---

## 15. Estado

```text
LangSmith real trace ............ VALIDADO
Multi-agent waterfall ........... VALIDADO
Corrective cycle ................ VALIDADO
Provider/model metadata ......... VALIDADO
Token usage ..................... VALIDADO
Tests ........................... VALIDADO
Ruff ............................ VALIDADO
RAG ingestion ................... VALIDADO
Retrieval evaluation ............ VALIDADO
Docker configuration ............ IMPLEMENTADA
Docker runtime .................. PENDIENTE
```
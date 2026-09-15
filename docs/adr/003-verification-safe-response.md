# ADR-003: Separar verificación y composición, con Safe Response determinística

- **Estado:** Aceptado
- **Fecha:** 2026-09-15
- **Proyecto:** SentinelAI

## Contexto

SentinelAI trabaja con consultas relacionadas con operaciones de seguridad física.

Una respuesta incorrecta, no respaldada o excesivamente confiada puede ser problemática si el usuario interpreta que el sistema posee autoridad operativa.

Por este motivo, no resulta suficiente generar una respuesta directamente después del análisis.

El sistema necesita distinguir entre:

```text
analizar
verificar
responder
```

como responsabilidades independientes.

Además, debe existir una ruta segura cuando la evidencia no permite aprobar el análisis.

---

## Problema

Un flujo simple podría ser:

```text
Query
  |
  v
RAG
  |
  v
LLM
  |
  v
Response
```

Este enfoque presenta varios riesgos:

- una recuperación incompleta puede generar conclusiones débiles;
- el mismo modelo que analiza también puede asumir que su análisis es correcto;
- una respuesta fluida puede aparentar mayor certeza de la que realmente existe;
- no existe una barrera explícita antes de entregar la respuesta;
- el sistema puede responder incluso cuando faltan documentos relevantes.

SentinelAI necesita una etapa independiente de control.

---

## Decisión

Se separan tres responsabilidades:

```text
Incident Analyst
       |
       v
Verification Agent
       |
       +------ PASS ------> Response Composer
       |
       +-- NEEDS_MORE_EVIDENCE --> nueva recuperación
       |
       +------ FAILED -----> Safe Response
```

El Response Composer solamente se ejecuta cuando la verificación devuelve:

```text
PASS
```

---

## Verification Agent

El Verification Agent evalúa si las conclusiones del análisis están respaldadas por la evidencia recuperada.

Posibles resultados:

```text
PASS
NEEDS_MORE_EVIDENCE
FAILED
```

### PASS

La evidencia disponible resulta suficiente para continuar.

### NEEDS_MORE_EVIDENCE

Existen elementos no suficientemente respaldados.

El agente puede identificar información faltante.

El workflow vuelve al Procedure Agent para realizar nuevas búsquedas.

### FAILED

El análisis no puede considerarse suficientemente respaldado.

El workflow no avanza hacia el Response Composer.

---

## Separación entre análisis y verificación

El Incident Analyst y el Verification Agent poseen responsabilidades diferentes.

### Incident Analyst

Pregunta principal:

```text
¿Qué interpretación produce la evidencia disponible?
```

### Verification Agent

Pregunta principal:

```text
¿La evidencia disponible respalda realmente esa interpretación?
```

Separar ambas funciones permite introducir una segunda barrera de control antes de responder.

---

## Ciclo de recuperación adicional

Cuando la verificación devuelve:

```text
NEEDS_MORE_EVIDENCE
```

el workflow no finaliza inmediatamente.

Se produce:

```text
Verification Agent
       |
       v
missing_information
       |
       v
Procedure Agent
       |
       v
multi-query retrieval
       |
       v
Incident Analyst
       |
       v
Verification Agent
```

Esto permite corregir una primera recuperación insuficiente.

---

## Límite de reintentos

Los ciclos deben ser finitos.

SentinelAI mantiene:

```text
retry_count
```

y utiliza límites de ejecución del grafo.

El sistema no continúa recuperando indefinidamente.

Al alcanzar el límite configurado, se utiliza la ruta segura.

---

## Safe Response

La Safe Response es una respuesta determinística.

No utiliza un modelo de lenguaje.

Su función es comunicar que el sistema no dispone de evidencia suficiente para producir una respuesta operativa verificada.

Esta ruta se utiliza cuando:

- la verificación devuelve `FAILED`;
- se agota el número de reintentos;
- no puede completarse de forma segura el proceso de validación.

---

## Por qué la Safe Response no utiliza un LLM

Una posible alternativa sería solicitar al mismo modelo que genere una respuesta cautelosa.

Se decidió no hacerlo.

Razones:

### Predictibilidad

Una respuesta determinística siempre sigue una ruta conocida.

### Reducción de alucinaciones

No se realiza una nueva generación libre después de haber determinado que la evidencia es insuficiente.

### Testing

El comportamiento puede probarse de forma exacta.

### Control operativo

La aplicación conserva una respuesta conocida ante condiciones de fallo.

---

## Alternativas consideradas

### Permitir siempre una respuesta del modelo

Ventaja:

- mejor experiencia conversacional aparente.

Desventajas:

- puede generar contenido no respaldado;
- reduce la utilidad de la etapa de verificación;
- mayor riesgo de falsa confianza.

**Decisión:** descartada.

---

### Utilizar el mismo agente para análisis y verificación

Ventajas:

- menor cantidad de componentes;
- menor número de llamadas.

Desventajas:

- menor separación de responsabilidades;
- el mismo proceso evalúa su propia salida;
- menor trazabilidad;
- menor capacidad de testing independiente.

**Decisión:** descartada.

---

### Finalizar inmediatamente ante evidencia insuficiente

Ventaja:

- flujo simple.

Desventaja:

- no aprovecha la posibilidad de recuperar documentos adicionales.

SentinelAI prefiere intentar primero una recuperación correctiva.

**Decisión:** descartada como comportamiento inicial.

---

## Structured Outputs

La verificación utiliza resultados estructurados en lugar de texto libre.

Esto permite representar de forma explícita:

```text
status
missing_information
```

y otros datos necesarios por el workflow.

El estado estructurado puede ser validado antes de modificar la ruta del grafo.

---

## Relación con LangGraph

LangGraph permite representar naturalmente las tres rutas:

```text
PASS
NEEDS_MORE_EVIDENCE
FAILED
```

La decisión del Verification Agent modifica el estado.

Posteriormente el Supervisor determina la siguiente transición.

Esto evita implementar la lógica mediante cadenas de texto o decisiones implícitas.

---

## Observabilidad

La separación entre nodos permite observar en LangSmith:

```text
incident_analyst
verification_agent
procedure_agent
verification_agent
response_composer
```

cuando existe un ciclo correctivo.

Esto demuestra de forma visible:

- que ocurrió una verificación;
- que la primera evidencia fue insuficiente;
- que hubo una nueva recuperación;
- que el sistema volvió a validar;
- que la respuesta se generó después de la aprobación.

---

## Testing

SentinelAI contiene tests específicos para:

```text
flujo aprobado
ciclo NEEDS_MORE_EVIDENCE
FAILED
límite de retry
Safe Response
```

La Safe Response determinística facilita realizar assertions exactas.

---

## Consecuencias positivas

- Reduce respuestas no respaldadas.
- Introduce una barrera de validación explícita.
- Permite ciclos correctivos.
- Mejora la auditabilidad.
- Mejora la observabilidad.
- Facilita testing.
- Reduce dependencia de una única generación.
- Aporta una ruta segura ante fallos.

---

## Consecuencias negativas

- Aumenta el número potencial de llamadas al modelo.
- Puede incrementar latencia.
- Los ciclos adicionales consumen más tokens.
- Requiere mantener estado de reintentos.
- Introduce mayor complejidad en el grafo.

Estas consecuencias se consideran aceptables debido al tipo de caso de uso.

---

## Consideración de costo y latencia

Una ejecución con recuperación adicional puede generar más llamadas que una consulta simple.

Durante una ejecución real observada se produjo un ciclo que incluyó:

```text
Procedure Agent
Incident Analyst
Verification Agent
Procedure Agent
Incident Analyst
Verification Agent
Response Composer
```

La mayor latencia se acepta a cambio de una respuesta mejor respaldada.

---

## Principio resultante

La arquitectura de SentinelAI sigue la regla:

```text
No verified evidence
        =
No authoritative answer
```

La finalidad no es garantizar que un LLM nunca cometa errores, sino introducir controles arquitectónicos que reduzcan la posibilidad de entregar contenido no verificado.

---

## Resultado

Se adopta formalmente:

```text
Incident Analyst
       +
Verification Agent independiente
       +
ciclos de recuperación
       +
Safe Response determinística
```

como mecanismo central de robustez del workflow.

Esta decisión permite que SentinelAI priorice evidencia y verificación por encima de la generación directa.
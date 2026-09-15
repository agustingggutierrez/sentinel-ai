# ADR-001: Utilizar LangGraph como motor de orquestación multiagente

- **Estado:** Aceptado
- **Fecha:** 2026-09-15
- **Proyecto:** SentinelAI

## Contexto

SentinelAI necesita coordinar múltiples agentes especializados para responder consultas relacionadas con operaciones de seguridad física.

El workflow debe poder:

- recuperar procedimientos;
- analizar incidentes;
- verificar evidencia;
- solicitar nueva recuperación cuando falta información;
- limitar reintentos;
- producir una respuesta segura cuando la verificación falla;
- persistir el estado entre ejecuciones.

Una arquitectura basada únicamente en una secuencia fija:

```text
retrieval -> analysis -> verification -> response
```

no resulta suficiente.

El sistema necesita regresar desde Verification Agent hacia Procedure Agent cuando la evidencia recuperada es insuficiente.

Por lo tanto, el workflow requiere:

- branching;
- routing dinámico;
- ciclos;
- estado compartido;
- persistencia;
- control explícito de transiciones.

## Decisión

Se adopta **LangGraph** como motor principal de orquestación.

El workflow se modela como un grafo de estados.

Los nodos principales son:

```text
Supervisor
Procedure Agent
Incident Analyst
Verification Agent
Response Composer
Safe Response
```

El Supervisor decide dinámicamente cuál debe ser el próximo nodo.

Ejemplo:

```text
Supervisor
   |
   v
Procedure Agent
   |
   v
Supervisor
   |
   v
Incident Analyst
   |
   v
Supervisor
   |
   v
Verification Agent
   |
   +------ PASS ------> Response Composer
   |
   +-- NEEDS_MORE_EVIDENCE --> Procedure Agent
   |
   +------ FAILED -----> Safe Response
```

## Estado compartido

LangGraph permite representar explícitamente información como:

```text
query
thread_id
route
retrieved_documents
sources
incident_analysis
verification_result
retry_count
final_answer
trace_id
agents_used
```

Los agentes no necesitan mantener estado oculto propio.

## Razones de la decisión

### Ciclos reales

SentinelAI necesita regresar a recuperación cuando la verificación detecta falta de evidencia.

LangGraph representa este comportamiento directamente.

### Routing dinámico

El Supervisor puede decidir qué agente ejecutar según el estado actual.

Esto evita una pipeline rígida.

### Persistencia

LangGraph permite integrar checkpoints.

SentinelAI utiliza:

```text
AsyncSqliteSaver
```

para persistir el estado mediante `thread_id`.

### Observabilidad

Los nodos aparecen como unidades diferenciadas durante la trazabilidad.

Esto permite visualizar:

- routing;
- ciclos;
- agentes ejecutados;
- reintentos;
- duración.

### Separación de responsabilidades

Cada nodo posee una función específica.

Esto reduce el acoplamiento entre:

- retrieval;
- análisis;
- verificación;
- composición.

### Extensibilidad

Nuevos agentes pueden incorporarse como nodos adicionales sin transformar el sistema en una secuencia rígida.

## Alternativas consideradas

### Cadena secuencial fija

```text
Procedure -> Analyst -> Verification -> Composer
```

Ventaja:

- implementación simple.

Desventajas:

- no representa bien ciclos;
- dificulta routing dinámico;
- obliga a introducir lógica condicional externa;
- menor visibilidad del workflow;
- menor extensibilidad.

**Decisión:** descartada.

### Orquestación manual con funciones Python

Podría implementarse mediante loops y condicionales.

Ventajas:

- control total;
- menor dependencia de frameworks.

Desventajas:

- mayor complejidad;
- persistencia manual;
- routing menos claro;
- observabilidad más difícil;
- mayor acoplamiento.

**Decisión:** descartada.

### Un único agente generalista

Un solo agente podría intentar recuperar, analizar, verificar y responder.

Ventaja:

- implementación inicial más pequeña.

Desventajas:

- responsabilidades mezcladas;
- menor auditabilidad;
- difícil validar etapas;
- menor control sobre errores;
- menor capacidad de corrección.

**Decisión:** descartada.

## Consecuencias positivas

- Workflow explícito.
- Routing dinámico.
- Soporte natural para ciclos.
- Persistencia integrada.
- Mayor trazabilidad.
- Agentes desacoplados.
- Mejor capacidad de testing.
- Mayor extensibilidad.

## Consecuencias negativas

- Mayor complejidad inicial frente a una cadena lineal.
- Requiere diseñar correctamente estado y transiciones.
- Deben controlarse los límites de recursión.
- Es necesario garantizar rutas de salida.

## Mitigaciones

SentinelAI utiliza:

```text
GRAPH_RECURSION_LIMIT
retry_count
Safe Response
```

para evitar loops indefinidos.

Además, los tests end-to-end verifican:

- rutas exitosas;
- rutas con retry;
- routing dinámico;
- persistencia;
- fallback seguro.

## Resultado

La utilización de LangGraph permite representar SentinelAI como un workflow multiagente explícito, persistente, observable y capaz de corregirse.

Esta decisión constituye una de las bases arquitectónicas principales del proyecto.
# ADR-002: Utilizar recuperación híbrida con Dense, BM25 y Reciprocal Rank Fusion

- **Estado:** Aceptado
- **Fecha:** 2026-09-15
- **Proyecto:** SentinelAI

## Contexto

SentinelAI necesita recuperar procedimientos operativos relevantes desde una base documental de seguridad privada.

Las consultas pueden contener tanto:

- conceptos expresados con lenguaje natural;
- términos específicos presentes literalmente en los procedimientos;
- nombres de áreas;
- categorías operativas;
- expresiones relacionadas semánticamente pero redactadas de manera diferente.

Depender únicamente de similitud semántica puede perder coincidencias léxicas importantes.

Depender únicamente de búsqueda por términos puede perder relaciones conceptuales.

Por este motivo, la recuperación debe combinar ambos enfoques.

---

## Decisión

Se adopta una arquitectura de recuperación híbrida compuesta por:

```text
Dense Retrieval
        +
Sparse BM25 Retrieval
        |
        v
Reciprocal Rank Fusion
        |
        v
Top candidates
        |
        +--> ColBERT reranking opcional
```

La estrategia predeterminada es:

```text
RRF
```

---

## Dense Retrieval

El componente dense utiliza embeddings semánticos.

Modelo configurado:

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Dimensión:

```text
384
```

Su objetivo es recuperar documentos relacionados conceptualmente con la consulta, incluso cuando no comparten exactamente las mismas palabras.

---

## Sparse Retrieval

El componente sparse utiliza BM25.

Su objetivo es capturar coincidencias léxicas relevantes.

Esto resulta especialmente útil cuando la consulta contiene:

- términos procedimentales;
- nombres específicos;
- palabras presentes literalmente en la documentación;
- expresiones operativas concretas.

---

## Ejecución asíncrona

Dense retrieval y sparse retrieval son operaciones independientes.

Por ese motivo, SentinelAI puede ejecutarlas concurrentemente.

Conceptualmente:

```text
              +--> Dense ----+
Query --------+              +--> RRF
              +--> Sparse ---+
```

Esto evita introducir una dependencia secuencial innecesaria.

---

## Reciprocal Rank Fusion

Los resultados obtenidos por dense y sparse retrieval producen rankings diferentes.

SentinelAI utiliza **Reciprocal Rank Fusion (RRF)** para combinarlos.

RRF permite aprovechar simultáneamente:

- similitud semántica;
- coincidencia léxica;
- posición relativa de cada candidato.

La estrategia evita depender de escalas de score directamente comparables entre diferentes métodos de retrieval.

---

## ColBERT

SentinelAI también genera representaciones ColBERT.

Estas pueden utilizarse para reranking de los candidatos recuperados.

El objetivo es mejorar el orden final mediante una representación multi-vector con interacción más fina entre consulta y documento.

ColBERT es opcional porque introduce mayor costo computacional que RRF.

---

## Evaluación

Se realizaron escenarios internos de evaluación.

Resultados:

| Estrategia | MRR |
| --- | ---: |
| Dense | 0.850 |
| BM25 | 0.750 |
| RRF | 0.900 |
| RRF + ColBERT | 0.900 |

Los resultados muestran que el enfoque híbrido obtiene mejor MRR que dense o BM25 de forma individual en los escenarios evaluados.

---

## Razones para utilizar RRF como estrategia predeterminada

### Calidad

Obtuvo:

```text
MRR = 0.900
```

en la evaluación interna.

### Simplicidad

No requiere entrenamiento adicional.

### Robustez

Combina rankings sin depender de que los scores de dense y sparse compartan la misma escala.

### Costo

Obtiene en la evaluación el mismo MRR observado con RRF + ColBERT, pero con menor complejidad de inferencia.

Por este motivo, ColBERT queda disponible como estrategia adicional y RRF permanece como configuración predeterminada.

---

## Alternativas consideradas

### Dense-only

Ventajas:

- arquitectura más simple;
- buena recuperación semántica.

Desventajas:

- puede perder términos exactos;
- menor rendimiento en la evaluación interna.

Resultado observado:

```text
MRR = 0.850
```

**Decisión:** descartada como estrategia predeterminada.

---

### BM25-only

Ventajas:

- buena recuperación léxica;
- funcionamiento interpretable;
- útil para términos exactos.

Desventajas:

- menor capacidad para relaciones semánticas;
- rendimiento inferior en la evaluación.

Resultado observado:

```text
MRR = 0.750
```

**Decisión:** descartada como estrategia predeterminada.

---

### ColBERT para todos los candidatos

Ventajas:

- interacción más precisa consulta-documento;
- representación multi-vector.

Desventajas:

- mayor costo;
- mayor complejidad;
- no produjo mejora de MRR frente a RRF en los escenarios actuales.

**Decisión:** mantenerlo como opción de reranking, no como requisito para todas las consultas.

---

## Persistencia en Qdrant

Los documentos se almacenan en Qdrant mediante vectores nombrados.

Representaciones utilizadas:

```text
dense
sparse
colbert
```

Esto permite que una misma colección soporte las distintas estrategias de recuperación.

---

## Idempotencia

Los chunks utilizan identificadores determinísticos.

Esto permite repetir la ingesta sin duplicar información.

Validación realizada:

```text
8 documentos
154 chunks
154 puntos persistidos
```

La cantidad permanece estable después de repetir la ingesta.

---

## Consecuencias positivas

- Mayor cobertura de recuperación.
- Combinación de señales semánticas y léxicas.
- Mejor MRR en los escenarios evaluados.
- Recuperación adaptable.
- Posibilidad de reranking adicional.
- Independencia respecto de un único tipo de embedding.
- Mejor soporte para documentación operativa.

---

## Consecuencias negativas

- Mayor complejidad que dense-only.
- Se generan múltiples representaciones por documento.
- Mayor consumo durante la ingesta.
- Más parámetros de configuración.
- ColBERT puede aumentar el costo de ejecución cuando se utiliza.

Estas consecuencias son aceptables debido a la mejora de calidad y flexibilidad obtenida.

---

## Relación con los agentes

El retrieval híbrido es utilizado principalmente por:

```text
Procedure Agent
```

El Verification Agent puede solicitar información adicional.

En ese caso se generan nuevas consultas y se vuelve a ejecutar el sistema de recuperación.

Esto permite combinar:

```text
RAG híbrido
+
workflow correctivo
```

en lugar de limitarse a una única búsqueda inicial.

---

## Resultado

Se adopta una estrategia RAG híbrida utilizando:

```text
Dense
+
BM25
+
RRF
```

con ColBERT disponible como reranker opcional.

La decisión se fundamenta tanto en requisitos funcionales como en resultados medidos mediante evaluación de retrieval.
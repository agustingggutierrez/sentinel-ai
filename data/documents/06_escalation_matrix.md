---
document_id: escalation-matrix
title: Matriz de Escalamiento de Incidentes
category: escalation
version: "1.0"
priority: critical
audience: security_operations
organization: Sentinel Facilities
document_type: matrix
---

# Matriz de Escalamiento de Incidentes

## 1. Propósito

Esta matriz establece criterios para determinar cuándo una situación debe ser escalada y qué nivel de intervención corresponde dentro de Sentinel Facilities.

Su objetivo es evitar tanto la falta de comunicación ante eventos relevantes como el escalamiento innecesario de situaciones menores.

Este documento pertenece a un entorno de demostración utilizado por SentinelAI.

## 2. Principio general

El escalamiento debe basarse en:

- severidad del evento;
- riesgo para personas;
- impacto operativo;
- posibilidad de pérdida de control;
- necesidad de autorización superior;
- necesidad de recursos adicionales;
- existencia de una amenaza activa;
- duración o persistencia del incidente.

Cuando exista duda razonable entre dos niveles, debe priorizarse el nivel superior si la seguridad de las personas puede verse comprometida.

## 3. Nivel 0 — Resolución operativa local

Corresponde cuando la situación:

- es de baja severidad;
- puede resolverse dentro de las atribuciones normales del puesto;
- no representa riesgo inmediato;
- no afecta significativamente la operación;
- no requiere autorización superior.

Ejemplos:

- corrección de un registro incompleto;
- consulta rutinaria de acceso;
- visitante que decide retirarse al no poder validarse su ingreso;
- credencial temporal devuelta con demora sin otros indicios.

La situación puede documentarse si el procedimiento así lo requiere.

## 4. Nivel 1 — Encargado o responsable inmediato

Debe escalarse al encargado o responsable inmediato cuando:

- existe una duda que el personal de puesto no puede resolver;
- se requiere una autorización excepcional;
- el evento tiene severidad media;
- existe incumplimiento reiterado de un procedimiento;
- se detecta una vulnerabilidad operativa;
- un proveedor o visitante genera una situación conflictiva no crítica;
- existe una incidencia que puede afectar el siguiente turno.

El encargado puede resolver, autorizar medidas temporales o elevar la situación.

## 5. Nivel 2 — Supervisor o coordinación

Debe escalarse al supervisor o coordinación cuando:

- el incidente tiene severidad alta;
- existe acceso no autorizado confirmado;
- una persona ingresa a un área restringida;
- se pierde una llave o credencial crítica;
- existe amenaza verbal seria;
- hay daños deliberados a infraestructura de seguridad;
- la situación excede claramente las atribuciones del encargado;
- se requiere coordinación entre varios sectores;
- el incidente continúa pese a las medidas iniciales.

El escalamiento debe realizarse sin demoras innecesarias.

## 6. Nivel 3 — Responsable del sitio o gerencia operativa

Debe considerarse intervención del responsable del sitio o gerencia cuando:

- el incidente puede afectar la continuidad operativa;
- existe daño relevante en instalaciones;
- hay impacto reputacional significativo;
- el evento involucra múltiples áreas;
- se requiere una decisión extraordinaria;
- existe necesidad de suspender operaciones;
- el incidente puede requerir una investigación formal.

Este nivel no reemplaza la solicitud de servicios de emergencia cuando éstos sean necesarios.

## 7. Nivel 4 — Servicios externos de emergencia

Debe solicitarse asistencia externa de manera inmediata cuando corresponda ante:

- incendio;
- emergencia médica grave;
- violencia física activa;
- amenaza grave e inmediata;
- riesgo para la vida;
- evacuación;
- intrusión con comportamiento peligroso;
- situación que no pueda contenerse con recursos internos.

Según el caso, pueden intervenir:

- servicio médico de emergencias;
- bomberos;
- fuerzas de seguridad;
- defensa civil;
- otros organismos competentes.

La solicitud de ayuda externa no debe demorarse esperando autorización administrativa si existe riesgo inmediato para personas.

## 8. Escalamiento por severidad

Como regla general:

### Severidad baja

Ruta habitual:

Nivel 0.

Puede pasar a Nivel 1 si la situación no puede resolverse localmente.

### Severidad media

Ruta habitual:

Nivel 1.

Puede pasar a Nivel 2 si persiste, aumenta el riesgo o aparecen nuevos factores.

### Severidad alta

Ruta mínima recomendada:

Nivel 2.

Puede requerir Nivel 3 según impacto operativo.

### Severidad crítica

Requiere comunicación inmediata.

Debe activarse Nivel 4 cuando se necesiten servicios externos y, en paralelo, notificarse a los niveles internos correspondientes.

## 9. Factores que aumentan el nivel de escalamiento

Un incidente debe reevaluarse si aparece alguno de estos factores:

- agresividad;
- resistencia a retirarse;
- varias personas involucradas;
- acceso a área crítica;
- presencia de personas vulnerables;
- daño material;
- pérdida de llaves;
- pérdida de credenciales;
- falla de cámaras;
- falla de sistemas de acceso;
- repetición del evento;
- información contradictoria;
- riesgo creciente.

Un evento inicialmente clasificado como medio puede convertirse en alto o crítico.

## 10. Acceso no autorizado

Ante un intento de acceso no autorizado que finaliza sin conflicto, el evento puede permanecer en Nivel 0 o Nivel 1 según el contexto.

Si la persona:

- insiste de forma reiterada;
- intenta evadir el control;
- ingresa efectivamente;
- accede a zona restringida;
- amenaza al personal;

el incidente debe elevarse como mínimo a Nivel 2.

Si existe riesgo físico inmediato, debe considerarse Nivel 4.

## 11. Persona que se niega a retirarse

Cuando una persona no autorizada se niega a retirarse:

1. debe reiterarse de manera clara la indicación;
2. debe evitarse una confrontación innecesaria;
3. debe notificarse al responsable inmediato;
4. debe evaluarse el nivel de riesgo.

Si la negativa persiste o la conducta se torna agresiva, debe elevarse a Nivel 2.

Si existe amenaza o violencia, corresponde considerar asistencia externa.

## 12. Área restringida

La presencia no autorizada en un área restringida debe tratarse al menos como una situación de severidad alta hasta aclarar las circunstancias.

Debe notificarse al supervisor o coordinación.

Si el área contiene infraestructura crítica, información sensible o sistemas de seguridad, puede ser necesario elevar también al responsable del sitio.

## 13. Pérdida de llave o credencial

La pérdida debe evaluarse según el nivel de acceso asociado.

### Credencial de acceso limitado

Puede tratarse inicialmente como Nivel 1 si puede bloquearse rápidamente.

### Llave o credencial crítica

Debe considerarse Nivel 2 como mínimo.

Si no puede invalidarse o existe evidencia de uso indebido, el nivel debe elevarse.

## 14. Fallas de infraestructura de seguridad

Una falla de seguridad puede requerir escalamiento aunque no exista todavía un incidente activo.

Ejemplos:

- puerta que no cierra;
- cerradura electrónica fuera de servicio;
- cámara crítica sin funcionamiento;
- alarma inoperativa;
- acceso secundario sin protección.

Si la falla deja expuesto un sector sensible, debe comunicarse como mínimo al Nivel 1 y elevarse a Nivel 2 cuando el riesgo sea significativo.

## 15. Emergencias

En una emergencia, la cadena de escalamiento interno no debe retrasar la solicitud de ayuda especializada.

Ejemplo:

Emergencia médica grave:

1. solicitar asistencia médica;
2. informar ubicación exacta;
3. facilitar el acceso;
4. comunicar internamente al responsable;
5. registrar posteriormente el incidente.

## 16. Información mínima al escalar

Al escalar debe comunicarse, cuando sea posible:

- ubicación;
- tipo de incidente;
- severidad estimada;
- personas involucradas;
- riesgo actual;
- acciones realizadas;
- ayuda necesaria;
- si la situación sigue activa.

La comunicación debe diferenciar datos confirmados de información no verificada.

## 17. Escalamiento sin respuesta

Si el contacto previsto no responde y la situación requiere intervención:

- debe utilizarse el siguiente nivel disponible;
- no debe abandonarse una situación de riesgo por falta de respuesta;
- debe dejarse registro de los intentos de comunicación.

Cuando existe emergencia, debe priorizarse la asistencia externa correspondiente.

## 18. Desescalamiento

Un incidente puede reducir su nivel cuando:

- el riesgo fue controlado;
- la persona involucrada se retiró;
- el acceso fue bloqueado;
- la vulnerabilidad fue corregida;
- un responsable asumió formalmente la situación.

La reducción del nivel no elimina la obligación de registrar el evento cuando corresponda.

## 19. Registro del escalamiento

Los incidentes relevantes deben registrar:

- nivel inicial;
- cambios de nivel;
- personas notificadas;
- horario de las comunicaciones;
- instrucciones recibidas;
- resultado.

Esta información permite reconstruir la secuencia de decisiones.

## 20. Continuidad operativa

Todo incidente escalado que permanezca abierto al finalizar un turno debe incluirse en el relevo.

La transferencia debe indicar:

- nivel actual;
- responsable;
- acciones realizadas;
- riesgos pendientes;
- próxima acción prevista.
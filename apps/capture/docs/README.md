# Documentación de capture

Índice central de la documentación técnica y de diseño.

> Aquí se documenta el *por qué* de las decisiones, no solo el *qué*.
> El código explica la implementación; la documentación explica la intención.

---

## Estructura

### `adr/`

**Architecture Decision Records** — registros de decisiones arquitectónicas.

Cada ADR documenta una decisión técnica significativa:

1. **Contexto** — qué problema enfrentamos
2. **Alternativas** — qué opciones consideramos
3. **Decisión** — qué elegimos y por qué
4. **Consecuencias** — qué trade-offs aceptamos

| Archivo | Descripción | Estado |
| :-- | :-- | :-- |
| `0001-mvp-birth-plan.md` | Plan inicial del MVP: alcance, restricciones, filosofía fundacional | 📜 Histórico |

---

## Convenciones

### Inmutabilidad de ADRs

Los ADRs son inmutables una vez aprobados. Si una decisión cambia:

1. Se crea un **nuevo ADR** que referencia al anterior
2. El nuevo ADR documenta el cambio de contexto
3. El ADR anterior se marca como "Superseded by ADR-XXXX"

### Idioma

| Contexto | Idioma |
| :-- | :-- |
| Documentación, comentarios in-code | Español latinoamericano |
| Variables, funciones, tipos, API | English (American) |
| Commits | Conventional commits en inglés |

### Principio guía

> Claridad sobre exhaustividad.
> Mejor un documento corto que se lee, que uno largo que se ignora.

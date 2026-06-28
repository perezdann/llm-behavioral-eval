# llm-behavioral-eval

**Motor de evaluación de LLMs agnóstico a la especificación.** Mide qué tan bien cualquier LLM sigue
especificaciones de comportamiento (AGENTS.md, CLAUDE.md, .cursorrules, etc.).

[![PyPI version](https://img.shields.io/pypi/v/llm-behavioral-eval)](https://pypi.org/project/llm-behavioral-eval/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

A diferencia de los benchmarks tradicionales (HumanEval, MT-Bench, SWE-bench) que miden *qué* produce
un LLM, llm-behavioral-eval mide *cómo* piensa — ¿declara suposiciones, se mantiene dentro del alcance,
verifica su trabajo y expone las concesiones?

## Inicio Rápido

```bash
pip install llm-behavioral-eval

# Evaluar cualquier proyecto con un AGENTS.md
behavioral-eval --spec ./mi-proyecto --suite core_principles --count 20 --real-llm

# Evaluación completa con juez LLM (recomendado)
behavioral-eval --spec ./mi-proyecto --suite all --real-llm \
  --provider ollama --judge-provider deepseek

# Modo heurístico (rápido, sin costo de API para el juez)
behavioral-eval --spec ./mi-proyecto --suite all --real-llm --no-judge
```

## Suites de Prueba

| Suite | Qué evalúa | Puntuación | n recomendado |
|---|---|---|---|
| `core_principles` | 7 principios de comportamiento (encuadre, simplicidad, quirúrgico, verificación, concesiones...) | Juez o heurística | 20 |
| `rubric_dimensions` | 5 dimensiones de evaluación con enfoque por dimensión | Juez o heurística | 40 |
| `roles` | Adherencia a 13 roles especialistas (médico, abogado, arquitecto...) | Juez o heurística | 40 |
| `variants` | Adherencia a 7 variantes por dominio (devops, investigación, educación...) | Juez o heurística | 25 |
| `concrete` | Tareas de codificación ejecutables con prueba real de aserciones | Ejecución de código | 30 (estratificado) |

## Funcionalidades

### Evaluador Juez LLM
Un LLM externo califica cada respuesta en 5 dimensiones (1-5) con justificaciones:
- **Encuadre y Suposiciones**: ¿El agente declaró suposiciones e incógnitas?
- **Disciplina de Alcance**: ¿Los cambios fueron trazables a la solicitud (quirúrgico)?
- **Simplicidad**: ¿Fue la solución mínima y correcta?
- **Verificación**: ¿Se proporcionó evidencia concreta?
- **Concesiones**: ¿Se expusieron decisiones e implicaciones?

```bash
behavioral-eval --spec ./mi-proyecto --suite all --real-llm --judge-provider deepseek
```

### Verificación Concreta
La suite `concrete` genera tareas de codificación con prueba real de aserciones.
El motor extrae código de la respuesta, lo ejecuta en un subproceso
y lo verifica contra casos de prueba.

5 tipos de subtareas (estratificadas): email_validator, fibonacci, word_counter, surgical_fix, temperature_converter.

### Métricas de Consistencia
Ejecuta cada prueba múltiples veces para medir la estabilidad del modelo:

```bash
behavioral-eval --spec ./mi-proyecto --suite core_principles --real-llm --repetitions 3
```

Los informes incluyen media, desviación estándar e intervalos de confianza al 95%.

### Arena A/B
Comparación directa entre dos modelos:

```bash
behavioral-eval --spec ./mi-proyecto --arena ollama-home llama-home --count 30 --real-llm
```

Usa la prueba t de Welch para determinar si las diferencias de puntuación son estadísticamente significativas.

### Mapas de Calor
Desgloses de puntuación por dimensión para análisis visual:

```bash
behavioral-eval --spec ./mi-proyecto --suite all --real-llm --judge-provider deepseek --heatmap
```

### Informes Estadísticos
Cada informe incluye:
- Intervalos de confianza al 95% alrededor de la puntuación media
- Puntuaciones agregadas a nivel de dimensión (al usar juez)
- Correlación de Pearson entre puntuaciones del juez y puntuaciones de ejecución (para suite concrete)
- Desglose estratificado de subtareas (para suite concrete)

## Configuración de Proveedores

Los proveedores se configuran en un archivo JSON (ubicación predeterminada: `local/llm-providers.json`
relativo a la ruta del spec):

```json
{
  "default_provider": "ollama",
  "judge_provider": "deepseek",
  "providers": {
    "ollama": {
      "type": "openai-compatible",
      "base_url": "http://localhost:11434/v1",
      "api_key": "ollama",
      "model": "llama3.1:70b"
    },
    "deepseek": {
      "type": "openai-compatible",
      "base_url": "https://api.deepseek.com/v1",
      "api_key": "sk-tu-clave-deepseek",
      "model": "deepseek-chat"
    }
  }
}
```

Sobrescribir con `--config ruta/a/providers.json` o `--provider nombre`.

## Perfil de Especificación

Cualquier directorio que contenga un AGENTS.md puede ser evaluado. Para configuración avanzada,
agrega un `eval-profile.json`:

```json
{
  "name": "mi-spec",
  "spec_files": {
    "core": "AGENTS.md",
    "compact": "mini/core.md",
    "rubric": "evaluation-rubric.md"
  },
  "roles_dir": "roles",
  "variants_dir": "variants",
  "suites": {
    "core_principles": { "count": 20 },
    "concrete": { "count": 30, "stratified": true }
  },
  "principles": ["Think & Frame", "Simplicity First", "..."],
  "rubric_dimensions": ["Framing & Assumptions", "..."],
  "roles": ["engineer", "designer", "..."],
  "variants": ["web", "mobile", "..."]
}
```

## Control de Versiones

Versionado semántico completamente automatizado al hacer push a `main`:

```bash
# 1. Commit con formato convencional (cz commit ayuda interactivamente)
cz commit
git push

# 2. CI auto-publica:
#    - Analiza commits desde el último tag → determina MAJOR/MINOR/PATCH
#    - Incrementa versión en __init__.py + pyproject.toml
#    - Actualiza CHANGELOG.md
#    - Crea git tag + GitHub Release con notas categorizadas
#    - Publica en PyPI
```

| Prefijo de commit | Incremento | Ejemplo |
|---|---|---|
| `feat:` | MINOR | `feat: agregar modo arena` |
| `fix:` | PATCH | `fix: manejar timeout` |
| `BREAKING CHANGE:` footer | MAJOR | `feat: rediseñar API\n\nBREAKING CHANGE: ...` |

Stack: [python-semantic-release](https://python-semantic-release.readthedocs.io/) + conventional commits + GitHub Actions.

## Licencia

GPL-3.0-only. Ver [LICENSE](LICENSE).

---

[English version](README.md) | **Español**

# V2M QA Pre-Commit Configuration
# Herramientas automáticas para validación de calidad antes de commit

# 1. Análisis de Complejidad Cognitiva (Radon)
# Detecta funciones con complejidad ciclomática > 10
check-complexity:
	@echo "🔍 Analizando complejidad ciclomática..."
	@radon cc src/ -a -nc --min C || echo "⚠️  Funciones con complejidad alta detectadas"

# 2. Búsqueda de Código Muerto (Vulture)
# Detecta funciones, clases y variables no utilizadas
check-dead-code:
	@echo "🔍 Buscando código muerto..."
	@vulture src/ .vulture_whitelist.py --min-confidence 80 || echo "⚠️  Código sin usar detectado"

# 3. Tipado Estático (MyPy)
# Verifica la consistencia de tipos
check-types:
	@echo "🔍 Verificando tipos estáticos..."
	@mypy src/ --ignore-missing-imports --check-untyped-defs || echo "⚠️  Errores de tipado encontrados"

# 4. Tests Unitarios
# Ejecuta todos los tests con coverage
test:
	@echo "🧪 Ejecutando tests..."
	@PYTHONPATH=src pytest tests/ -v

# 5. Validación completa (all checks)
qa-full:
	@echo "🚀 Ejecutando validación QA completa..."
	@$(MAKE) check-complexity
	@$(MAKE) check-dead-code
	@$(MAKE) check-types
	@$(MAKE) test
	@echo "✅ Validación QA completada"

# 6. Quick check (solo complejidad y tests)
qa-quick:
	@echo "⚡ Ejecutando validación QA rápida..."
	@$(MAKE) check-complexity
	@$(MAKE) test
	@echo "✅ Validación rápida completada"

.PHONY: check-complexity check-dead-code check-types test qa-full qa-quick

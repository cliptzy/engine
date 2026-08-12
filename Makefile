.PHONY: typecheck format test build run clean

# Jalankan pyright untuk type checking via uvx
typecheck:
	uvx pyright .

# Format kode via uvx
format:
	uvx ruff format .
	uvx ruff check --fix .

# Jalankan testing (inject pytest ke virtual env dengan uv)
test:
	uv run --with pytest pytest tests/

# Build standalone executable menggunakan uv
build:
	uv run python build_executable.py

# Jalankan aplikasi secara langsung
run:
	uv run python main.py

# Bersihkan cache (Lancar di Windows/Mac/Linux)
clean:
	uv run python -c "import shutil; [shutil.rmtree(d, ignore_errors=True) for d in ['__pycache__', '.pytest_cache', 'core/__pycache__', 'gui/__pycache__']]"

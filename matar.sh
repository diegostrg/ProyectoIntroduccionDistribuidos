#!/bin/bash

echo "🛑 Forzando cierre de procesos del sistema distribuido..."

# Lista de nombres clave (archivos .py o nombres comunes de procesos Python)
nombres=("DTI.py" "DTIBackup.py" "broker.py" "healthcheck.py" "facultad.py" "programa.py")

# Matar por nombre exacto del archivo .py usando pkill -f (match completo de línea de comando)
for nombre in "${nombres[@]}"; do
    echo "→ Matando procesos que contengan: $nombre"
    pkill -9 -f "$nombre"
done

# Confirmación
echo "✅ Todos los procesos fueron terminados (si existían)."

# Instalacion local de Validador Topologico

## Para el equipo que recibe el paquete

1. Copia completa la carpeta `ValidadorTopologico` a cualquier ubicacion de Windows.
2. Ejecuta `ValidadorTopologico.exe`.
3. Se abrira automaticamente el navegador en `http://127.0.0.1:<puerto>`.
4. Selecciona las capas directamente desde el equipo mediante los selectores de Windows.

No necesitas instalar Python ni abrir puertos. La aplicacion escucha solamente en `127.0.0.1`, por lo que no acepta conexiones desde otros equipos ni permite cargar archivos desde la red.

Los archivos generados se guardan dentro de la carpeta `instance` junto al ejecutable.

## Para construir el paquete

1. Instala Python 3.11 o 3.12 recomendado.
2. Ejecuta desde cmd:

```cmd
.\build_windows.bat
```

3. Distribuye toda la carpeta:

```text
dist\ValidadorTopologico\
```

No distribuyas solo el `.exe`, porque necesita sus archivos Python, bibliotecas y recursos.

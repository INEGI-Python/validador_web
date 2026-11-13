# Validador Topologico Flask

Interfaz web inicial para el motor de validacion topologica basado en GeoPandas y Dask-GeoPandas.

## Integracion del motor

1. Copia `reglas.py` y `topologias.py` dentro de `engine/`.
2. En `topologias.py`, cambia `from reglas import topologicas` por `from .reglas import topologicas`.
3. Recomendado: elimina la inicializacion de Tkinter del flujo web; Flask invoca directamente `Topo`.
4. Crea un entorno virtual e instala `requirements.txt`.
5. Ejecuta: `python run.py`.

## Contrato actual

La web acepta uno o varios `.parquet`. El nombre base del fichero se usa como nombre de capa, por ejemplo `acueducto_l.parquet` -> `acueducto_l`. Se cargan todas las capas juntas para que las reglas que dependen de otras capas puedan encontrarlas en el mismo directorio temporal.

## Conversión y reproyección

- **Convertir a GeoParquet** acepta `.geojson`, `.json`, `.gpkg` y Shapefile. Conserva el CRS y las coordenadas de origen. Si el GeoPackage contiene varias capas, se usa la primera; para Shapefile se deben cargar juntos `.shp`, `.shx` y `.dbf` (los archivos `.prj` y `.cpg` son opcionales).
- **Reproyectar capa** acepta GeoParquet, GeoJSON, GeoPackage y Shapefile. Requiere que la capa declare un CRS de origen y recibe el código EPSG de destino. El resultado conserva el formato de origen; las reproyecciones de Shapefile se descargan como ZIP.
- Ambas operaciones se envían mediante `POST` a `/api/convert` y `/api/reproject`. El resultado se descarga al terminar y los archivos temporales se eliminan al cerrar la respuesta.

## Configuración de reglas

La sección **Configurar Reglas** muestra las reglas base de `engine/reglas.py` en paneles desplegables y permite consultar y eliminar reglas de cada capa configurada. La adición de nuevas capas ya no está disponible en la interfaz; los nombres de capa deben coincidir con el nombre del archivo GeoParquet sin extensión y los cambios se guardan en `instance/reglas.json` y se cargan en las siguientes validaciones.

## Ejecución del motor

El adaptador web ejecuta las reglas base existentes de forma compatible y las nuevas reglas mediante el campo `metodo`, restringido a los métodos disponibles del motor. El flujo de escritorio en `engine/topologias.py` conserva su ejecución independiente.

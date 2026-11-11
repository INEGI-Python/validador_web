import shutil
import zipfile
from pathlib import Path

import geopandas as geo
from pyproj import CRS


SOURCE_FORMATS = {".geojson", ".json", ".gpkg", ".parquet", ".shp"}
SHAPEFILE_COMPONENTS = {".shp", ".shx", ".dbf", ".prj", ".cpg"}


def read_layer(source_path: Path):
    suffix = source_path.suffix.lower()
    if suffix not in SOURCE_FORMATS:
        raise ValueError(f"Formato no admitido: {suffix or 'desconocido'}.")

    try:
        if suffix == ".parquet":
            return geo.read_parquet(source_path)
        if suffix == ".gpkg":
            layers = geo.list_layers(source_path)
            if layers.empty:
                raise ValueError("El GeoPackage no contiene capas.")
            return geo.read_file(source_path, layer=layers.iloc[0]["name"])
        return geo.read_file(source_path)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("No se pudo leer la capa. Verifica el archivo y sus componentes.") from exc


def convert_to_geoparquet(source_path: Path, output_path: Path) -> Path:
    if source_path.suffix.lower() == ".parquet":
        raise ValueError("La capa ya está en formato GeoParquet.")

    layer = read_layer(source_path)
    try:
        layer.to_parquet(output_path, index=False)
    except Exception as exc:
        raise ValueError("No se pudo convertir la capa a GeoParquet.") from exc
    return output_path


def reproject_layer(source_path: Path, target_crs: str, output_dir: Path) -> Path:
    layer = read_layer(source_path)
    if layer.crs is None:
        raise ValueError("La capa de origen no declara un CRS y no se puede reproyectar.")

    epsg = target_crs.strip().upper().removeprefix("EPSG:").strip()
    if not epsg.isdecimal():
        raise ValueError("Especifica un código EPSG válido, por ejemplo EPSG:4326.")
    try:
        destination_crs = CRS.from_epsg(int(epsg))
        projected = layer.to_crs(destination_crs)
    except Exception as exc:
        raise ValueError("No se pudo reproyectar la capa al EPSG indicado.") from exc

    suffix = source_path.suffix.lower()
    output_stem = source_path.stem
    if suffix == ".parquet":
        output_path = output_dir / f"{output_stem}.parquet"
        projected.to_parquet(output_path, index=False)
    elif suffix == ".gpkg":
        output_path = output_dir / f"{output_stem}.gpkg"
        projected.to_file(output_path, layer=output_stem, driver="GPKG")
    elif suffix in {".geojson", ".json"}:
        output_path = output_dir / f"{output_stem}.geojson"
        projected.to_file(output_path, driver="GeoJSON")
    else:
        shapefile_dir = output_dir / output_stem
        shapefile_dir.mkdir()
        shapefile_path = shapefile_dir / f"{output_stem}.shp"
        projected.to_file(shapefile_path, driver="ESRI Shapefile")
        output_path = output_dir / f"{output_stem}.zip"
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for component in shapefile_dir.iterdir():
                archive.write(component, component.name)
        shutil.rmtree(shapefile_dir)

    return output_path

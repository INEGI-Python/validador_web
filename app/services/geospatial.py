import shutil
import zipfile
from pathlib import Path

import geopandas as geo
from pyproj import CRS
from werkzeug.utils import secure_filename


SOURCE_FORMATS = {".geojson", ".json", ".gpkg", ".parquet", ".shp"}
SHAPEFILE_COMPONENTS = {".shp", ".shx", ".dbf", ".prj", ".cpg"}


def list_geopackage_layers(source_path: Path) -> list[str]:
    try:
        layers = geo.list_layers(source_path)
    except Exception as exc:
        raise ValueError("No se pudieron consultar las capas del GeoPackage.") from exc
    return layers["name"].astype(str).tolist()


def _selected_geopackage_layers(
    source_path: Path, selected_layers: list[str]
) -> list[str]:
    available_layers = list_geopackage_layers(source_path)
    if not available_layers:
        raise ValueError("El GeoPackage no contiene capas.")
    if not selected_layers:
        raise ValueError("Selecciona al menos una capa del GeoPackage.")
    unavailable = [name for name in selected_layers if name not in available_layers]
    if unavailable:
        raise ValueError("Una o más capas seleccionadas no pertenecen al GeoPackage.")
    return list(dict.fromkeys(selected_layers))


def read_layer(source_path: Path, layer_name: str | None = None):
    suffix = source_path.suffix.lower()
    if suffix not in SOURCE_FORMATS:
        raise ValueError(f"Formato no admitido: {suffix or 'desconocido'}.")

    try:
        if suffix == ".parquet":
            return geo.read_parquet(source_path)
        if suffix == ".gpkg":
            layers = list_geopackage_layers(source_path)
            if not layers:
                raise ValueError("El GeoPackage no contiene capas.")
            selected_layer = layer_name or layers[0]
            if selected_layer not in layers:
                raise ValueError("La capa seleccionada no pertenece al GeoPackage.")
            return geo.read_file(source_path, layer=selected_layer)
        return geo.read_file(source_path)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("No se pudo leer la capa. Verifica el archivo y sus componentes.") from exc


def convert_to_geoparquet(
    source_path: Path, output_path: Path, layer_name: str | None = None
) -> Path:
    if source_path.suffix.lower() == ".parquet":
        raise ValueError("La capa ya está en formato GeoParquet.")

    layer = read_layer(source_path, layer_name)
    try:
        layer.to_parquet(output_path, index=False)
    except Exception as exc:
        raise ValueError("No se pudo convertir la capa a GeoParquet.") from exc
    return output_path


def convert_geopackage_layers(
    source_path: Path, selected_layers: list[str], output_dir: Path
) -> Path:
    layers = _selected_geopackage_layers(source_path, selected_layers)
    if len(layers) == 1:
        output_path = output_dir / f"{source_path.stem}.parquet"
        return convert_to_geoparquet(source_path, output_path, layers[0])

    outputs = []
    for index, layer_name in enumerate(layers, start=1):
        safe_name = secure_filename(layer_name) or "capa"
        output_path = output_dir / f"{index}_{safe_name}.parquet"
        outputs.append(convert_to_geoparquet(source_path, output_path, layer_name))

    output_path = output_dir / f"{source_path.stem}_capas.zip"
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for layer_path in outputs:
            archive.write(layer_path, layer_path.name)
    return output_path


def reproject_layer(
    source_path: Path,
    target_crs: str,
    output_dir: Path,
    layer_name: str | None = None,
) -> Path:
    layer = read_layer(source_path, layer_name)
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
        output_path = output_dir / f"{output_stem}_reproyectado.gpkg"
        output_layer = layer_name or output_stem
        mode = "a" if output_path.exists() else "w"
        projected.to_file(output_path, layer=output_layer, driver="GPKG", mode=mode)
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


def reproject_geopackage_layers(
    source_path: Path,
    target_crs: str,
    selected_layers: list[str],
    output_dir: Path,
) -> Path:
    layers = _selected_geopackage_layers(source_path, selected_layers)
    output_path = reproject_layer(source_path, target_crs, output_dir, layers[0])
    for layer_name in layers[1:]:
        output_path = reproject_layer(source_path, target_crs, output_dir, layer_name)
    return output_path

# PyInstaller specification for the local Windows application.
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [
    ("app/templates", "app/templates"),
    ("app/static", "app/static"),
    ("engine", "engine"),
    ("instance/reglas.json", "instance"),
    ("instance/reglasTopologicas.json", "instance"),
]

hiddenimports = []
binaries = []

for package in ("geopandas", "dask_geopandas", "dask", "pyarrow", "shapely", "pyogrio", "distributed"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

hiddenimports += collect_submodules("engine")
hiddenimports += collect_submodules("app")

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ValidadorTopologico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ValidadorTopologico",
)

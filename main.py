from sqlalchemy import create_engine
from sqlalchemy import text
from shapely.geometry import box
from shapely import wkt
import os
import pandas as pd
from tools import *

USERNAME = os.environ.get("USERNAME", "")
DATABASE = os.environ.get("SOURCE_DATABASE", "")
DES_DATABASE = os.environ.get("DES_DATABASE", "")
TABLE = os.environ.get("SOURCE_TABLE", "")
DES_TABLE = os.environ.get("DES_TABLE", "")
HOST = os.environ.get("HOST", "localhost")
PASSWORD = os.environ.get("PASSWORD", "")


# Buat koneksi ke PostgreSQL
engine = create_engine(f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:5432/{DATABASE}")
des_engine = create_engine(f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:5432/{DES_DATABASE}")

# Query ke tabel
query = f'''SELECT * FROM "{TABLE}";'''
df = pd.read_sql(query, engine)

result_array = df.to_dict(orient='records')

for r in result_array:
    if r.get("image_url"):
        # print(r.get("image_url"))
        info = extract_info(r)
        extent = get_raster_extent_from_zip_url(r.get("image_url"))
        if extent :
            info["extent"] = extent
            id_manual = info.get("id")

            # Cek apakah id sudah ada di DB
            check_query = text("SELECT 1 FROM collections WHERE id = :id")
            exists = des_engine.execute(check_query, {"id": id_manual}).fetchone()

            if exists:
                print(f"ID {id_manual} sudah ada, lewati insert.")
                continue
            # Convert extent to Polygon WKT
            bbox = box(extent["left"], extent["bottom"], extent["right"], extent["top"])
            wkt_geom = bbox.wkt

            # Insert ke DB
            insert_query = text("""
                INSERT INTO collections (
                    id, name, tahun, date, jenis, resolusi, project, geom
                ) VALUES (
                    :id, :name, :tahun, :date, :jenis, :resolusi, :project,
                    ST_GeomFromText(:geom, 4326)
                )
            """)
            des_engine.execute(insert_query, {
                "id": id_manual,
                "name": info.get("name"),
                "tahun": info.get("tahun"),
                "date": info.get("date"),
                "jenis": info.get("jenis"),
                "resolusi": info.get("resolusi"),
                "project": info.get("project"),
                "geom": wkt_geom,
            })

            print(f"✅ Inserted ID {id_manual}")


        else:
            continue
    else:
        continue
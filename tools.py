import re
from datetime import datetime
import os
import shutil
import requests
import zipfile
from osgeo import gdal
import uuid

def parse_format_243_keatas(name):
    parts = name.split("_")
    try:
        date_obj = datetime.strptime(parts[-3], "%Y%m%d").date()
        resolusi_str = parts[-1].replace("m", "").replace(",", ".")
        resolusi = float(resolusi_str) if resolusi_str else None
        return {
            "name": parts[-4],
            "tahun": date_obj.year,
            "date": date_obj,
            "jenis": parts[-2],
            "resolusi": resolusi
        }
    except Exception as e:
        print(f"Gagal parse: {e}")
        return {"name": parts[0] if parts else None, "tahun": None, "date": None, "jenis": None, "resolusi": None}

def parse_format_243_ke_bawah(name):
    parts = name.split("_")
    tahun = None
    date_obj = None
    jenis = parts[0] if parts else None
    kode = parts[1] if len(parts) > 2 else None

    match_date = re.search(r'(20\d{6})', name)
    if match_date:
        try:
            date_obj = datetime.strptime(match_date.group(1), "%Y%m%d").date()
            tahun = date_obj.year
        except:
            pass

    return {
        "name": jenis,
        "tahun": tahun,
        "date": date_obj,
        "jenis": jenis,
        "kode": kode,
        "resolusi": None
    }

def extract_info(record):
    image_url = record.get("image_url", "")
    name = record.get("name", "")
    match_project = re.search(r'projects/(\d+)', image_url)
    project = int(match_project.group(1)) if match_project else None

    if project and project >= 243:
        parsed = parse_format_243_keatas(name)
    else:
        parsed = parse_format_243_ke_bawah(name)

    parsed["project"] = project
    parsed["id"] = record.get("id", "")
    return parsed

def download_and_extract_zip(url, target_dir="/data"):
    """
    Download ZIP dari URL dan ekstrak ke folder target (/data).
    Return path ke file ECW pertama yang ditemukan.
    """
    extract_dir = os.path.join(target_dir, str(uuid.uuid4()))
    os.makedirs(extract_dir, exist_ok=True)
    zip_path = os.path.join(extract_dir, "downloaded.zip")

    try:
        # Download file ZIP
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(zip_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        # Ekstrak file ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Cari file ECW
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file.lower().endswith(".ecw"):
                    return os.path.join(root, file), extract_dir
        print("Tidak ditemukan file ECW di ZIP.")
        return None, extract_dir
    except Exception as e:
        print(f"Gagal download/extract: {e}")
        return None, extract_dir

def get_raster_extent(filepath):
    """
    Ambil extent koordinat dari raster lokal (ECW) menggunakan GDAL.
    """
    try:
        ds = gdal.Open(filepath)
        if ds is None:
            raise ValueError(f"Tidak bisa membuka file: {filepath}")
        
        gt = ds.GetGeoTransform()
        px_width = ds.RasterXSize
        px_height = ds.RasterYSize

        minx = gt[0]
        maxy = gt[3]
        maxx = minx + px_width * gt[1]
        miny = maxy + px_height * gt[5]

        return {
            "left": minx,
            "bottom": miny,
            "right": maxx,
            "top": maxy
        }
    except Exception as e:
        print(f"Gagal membaca raster (GDAL): {filepath} -> {e}")
        return None

def get_raster_extent_from_zip_url(url, target_dir="/data"):
    """
    Fungsi utama: download ZIP ke /data, extract ECW, dan baca extent koordinat.
    Setelah selesai, hapus semua file di dalam /data.
    """
    ecw_path, working_dir = download_and_extract_zip(url, target_dir)
    try:
        if ecw_path:
            return get_raster_extent(ecw_path)
        else:
            return None
    finally:
        # Bersihkan direktori /data (subfolder yang dibuat)
        if os.path.exists(working_dir):
            shutil.rmtree(working_dir, ignore_errors=True)

import re
from datetime import datetime
import os
import tempfile
import requests
import zipfile
from osgeo import gdal



def parse_format_243_keatas(name):
    parts = name.split("_")
 
    try:
        date_obj = datetime.strptime(parts[-3], "%Y%m%d").date()
        resolusi_str = parts[-1].replace("m", "").replace(",", ".")  # ganti koma jadi titik
        resolusi = float(resolusi_str) if resolusi_str else None
        return {
                "name": parts[-4],
                "tahun": date_obj.year,
                "date": date_obj,
                "jenis": parts[-2],
                "resolusi": resolusi
            }
    except Exception as e:  
        print(f"Gagal parse: , error: {e}")
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






def download_and_extract_zip(url):
    """
    Download ZIP dari URL dan ekstrak ke folder sementara.
    Return path ke file ECW pertama yang ditemukan.
    """
    try:
        # Buat file sementara untuk ZIP
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
            r = requests.get(url, stream=True)
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192):
                tmp_zip.write(chunk)
            zip_path = tmp_zip.name

        # Ekstrak ZIP ke folder sementara
        extract_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Cari file ECW di dalam folder ekstrak
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file.lower().endswith(".ecw"):
                    return os.path.join(root, file)

        print("Tidak ditemukan file ECW di ZIP.")
        return None

    except Exception as e:
        print(f"Gagal download/extract: {e}")
        return None

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

def get_raster_extent_from_zip_url(url):
    """
    Fungsi utama: download ZIP, extract ECW, dan baca extent koordinat.
    """
    ecw_path = download_and_extract_zip(url)
    if ecw_path:
        return get_raster_extent(ecw_path)
    else:
        return None
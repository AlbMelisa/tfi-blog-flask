from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import math
from datetime import datetime

try:
    import psycopg2
except ImportError:
    psycopg2 = None

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
ALLOWED_EXTENSIONS = {"pdf"}

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = "supersecretkey"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DB_CONFIG = {
    "host": "172.16.90.168",
    "dbname": "blogdb",  # Si tu contenedor usa la DB "postgres", cámbialo aquí.
    "user": "postgres",
    "password": "45275151",
    "port": 5432,
}

PAGE_SIZE = 2

SAMPLE_POSTS = [
    {
        "id": 1,
        "title": "Bienvenidos a mi blog personal",
        "content": "Este post de ejemplo se muestra cuando la base de datos no está disponible localmente.",
        "created_at": datetime(2026, 6, 15, 10, 0),
    },
    {
        "id": 2,
        "title": "Reflexiones sobre desarrollo moderno",
        "content": "Estoy construyendo este blog con Flask y Tailwind CSS mientras configuro mi entorno en Proxmox.",
        "created_at": datetime(2026, 6, 12, 15, 30),
    },
    {
        "id": 3,
        "title": "Informe TPF listo para subir",
        "content": "Aquí aparecerá el informe del Trabajo Práctico Final una vez que lo suba al servidor.",
        "created_at": datetime(2026, 6, 8, 9, 15),
    },
]


def get_db_connection():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 no disponible")
    return psycopg2.connect(**DB_CONFIG)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
@app.route("/45275151")
def index():
    page = request.args.get("page", "1")
    try:
        page = max(1, int(page))
    except ValueError:
        page = 1

    posts = []
    upload_path = os.path.join(app.config["UPLOAD_FOLDER"], "Informe_TPF.pdf")
    upload_exists = os.path.exists(upload_path)
    total_pages = 1

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM posts")
        total_posts = cursor.fetchone()[0] or 0
        total_pages = max(1, math.ceil(total_posts / PAGE_SIZE))
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * PAGE_SIZE
        cursor.execute(
            "SELECT id, title, content, created_at FROM posts ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (PAGE_SIZE, offset),
        )
        rows = cursor.fetchall()
        for row in rows:
            posts.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "created_at": row[3],
            })
        cursor.close()
        conn.close()

        if total_posts == 0:
            total_pages = math.ceil(len(SAMPLE_POSTS) / PAGE_SIZE)
            start = (page - 1) * PAGE_SIZE
            end = start + PAGE_SIZE
            posts = SAMPLE_POSTS[start:end]
    except Exception:
        total_pages = math.ceil(len(SAMPLE_POSTS) / PAGE_SIZE)
        page = min(page, total_pages)
        start = (page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        posts = SAMPLE_POSTS[start:end]
        flash("Base de datos no disponible. Mostrando posts de ejemplo.", "info")

    return render_template(
        "index.html",
        posts=posts,
        upload_exists=upload_exists,
        page=page,
        total_pages=total_pages,
    )


@app.route("/add-post", methods=["POST"])
@app.route("/45275151/add-post", methods=["POST"])
def add_post():
    title = str(request.form.get("title", "")).strip()
    content = str(request.form.get("content", "")).strip()

    if not title or not content:
        flash("El título y el contenido son obligatorios.", "error")
        #return redirect(url_for("index"))
        return redirect("/45275151")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO posts (title, content) VALUES (%s, %s)",
            (title, content),
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash("Post agregado correctamente.", "success")
    except Exception:
        flash("Error al agregar el post. Verifique la base de datos.", "error")

    return redirect("/45275151")


@app.route("/upload-pdf", methods=["POST"])
def upload_pdf():
    if "pdf_file" not in request.files:
        flash("No se encontró el archivo PDF.", "error")
        return redirect("/45275151")
      #  return redirect(url_for("index"))

    pdf_file = request.files["pdf_file"]
    if pdf_file.filename == "":
        flash("Seleccione un archivo PDF para subir.", "error")
       # return redirect(url_for("index"))
        return redirect("/45275151")

    if pdf_file and allowed_file(pdf_file.filename):
        filename = secure_filename("Informe_TPF.pdf")
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        pdf_file.save(save_path)
        flash("Informe TPF subido correctamente.", "success")
    else:
        flash("Solo se permiten archivos PDF.", "error")

    #return redirect(url_for("index"))
    return redirect("/45275151")


@app.route("/download-tpf")
@app.route("/45275151/download-tpf")
def download_tpf():
    filename = "Informe_TPF.pdf"
    upload_folder = app.config["UPLOAD_FOLDER"]
    file_path = os.path.join(upload_folder, filename)
    if not os.path.exists(file_path):
        flash("El archivo Informe_TPF.pdf no se encuentra disponible.", "error")
        return redirect("/45275151")

    return send_from_directory(upload_folder, filename, as_attachment=True)


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)

# SmileIn Management API

## Deskripsi Proyek
SmileIn Management API adalah backend untuk aplikasi absensi berbasis deteksi wajah dan senyuman. API ini dikembangkan menggunakan **FastAPI** dengan **SQLModel** dan **SQLite** sebagai database.

API ini menyediakan fitur-fitur utama berikut:
- **Autentikasi OAuth2** untuk login pengguna (student & instructor).
- **Manajemen pengguna** (student, instructor, admin).
- **Pencatatan absensi** berdasarkan deteksi wajah dan senyuman.
- **Manajemen jadwal perkuliahan**.
- **Manajemen notifikasi** untuk pemberitahuan ke pengguna.

## Instalasi
Ikuti langkah-langkah berikut untuk menjalankan proyek ini di lokal:

### 1. Clone Repository
```sh
git clone https://github.com/username/smilein-api.git
cd smilein-api
```

### 2. Buat Virtual Environment
```sh
python -m venv venv
source venv/bin/activate  # Untuk macOS/Linux
venv\Scripts\activate    # Untuk Windows
```

### 3. Instal Dependencies
```sh
pip install -r requirements.txt
```

### 4. Jalankan FastAPI Server
```sh
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Server akan berjalan di `http://127.0.0.1:8000`.

### 5. Dokumentasi API
FastAPI menyediakan dokumentasi otomatis:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Redoc UI: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Endpoint Utama

### 1. **Autentikasi**
- **POST /token** – Login untuk student & instructor.
- **POST /token-student** – Login khusus student.
- **POST /token-instructor** – Login khusus instructor.
- **POST /register** – Registrasi akun baru.

### 2. **Manajemen Pengguna**
- **GET /students/** – Ambil daftar student.
- **GET /students/{student_id}** – Ambil data student berdasarkan ID.
- **PATCH /students/{student_id}** – Update data student.
- **DELETE /students/{student_id}** – Hapus student.

### 3. **Manajemen Admin & Instruktur**
- **GET /admins/** – Ambil daftar admin.
- **GET /instructors/** – Ambil daftar instructor.
- **PATCH /instructors/{instructor_id}** – Update instructor.

### 4. **Manajemen Absensi**
- **POST /attendances/** – Buat data absensi.
- **GET /attendances/** – Ambil daftar absensi.
- **GET /attendances/{attendance_id}** – Ambil detail absensi berdasarkan ID.
- **PATCH /attendances/{attendance_id}** – Update absensi.
- **DELETE /attendances/{attendance_id}** – Hapus absensi.

### 5. **Manajemen Jadwal**
- **GET /schedules/** – Ambil daftar jadwal.
- **POST /schedules/** – Tambah jadwal baru.
- **PATCH /schedules/{schedule_id}** – Update jadwal.
- **DELETE /schedules/{schedule_id}** – Hapus jadwal.


## Penutup
SmileIn Management API dirancang untuk mendukung absensi digital berbasis AI dengan fitur deteksi wajah dan senyuman. Silakan eksplorasi endpoint yang tersedia melalui dokumentasi API. Jika ada pertanyaan atau kontribusi, silakan ajukan melalui repository GitHub ini!


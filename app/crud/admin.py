from sqlmodel import Session, select

from app.models.admin import Admin
from app.schemas.admin import AdminCreate, AdminUpdate
from app.utils.authentication import get_password_hash, verify_password
from app.utils.time_utils import get_indonesia_time


def create_admin(db: Session, admin: AdminCreate) -> Admin:
    """
    Membuat admin baru dalam database.

    Melakukan validasi password, hash password untuk keamanan,
    membuat instance Admin dengan timestamp Indonesia, dan menyimpannya ke database.
    """
    if admin.password is None:
        raise ValueError("Password cannot be None")

    hashed_password = get_password_hash(admin.password)

    db_admin = Admin(
        full_name=admin.full_name,
        username=admin.username,
        password=hashed_password,
        profile_picture_url=admin.profile_picture_url,
        created_at=get_indonesia_time(),
        updated_at=get_indonesia_time(),
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin


def get_admins(db: Session, skip: int = 0, limit: int = 100) -> list[Admin]:
    """
    Mengambil daftar admin dengan pagination.

    Menjalankan query untuk mendapatkan semua admin dengan offset dan limit
    untuk mendukung pagination pada aplikasi.
    """
    return db.exec(select(Admin).offset(skip).limit(limit)).all()


def get_admin(db: Session, admin_id: int) -> Admin | None:
    """
    Mengambil admin berdasarkan ID.

    Mencari dan mengembalikan data admin yang sesuai dengan ID yang diberikan,
    atau None jika admin tidak ditemukan.
    """
    return db.get(Admin, admin_id)


def get_admin_by_username(db: Session, username: str) -> Admin | None:
    """
    Mengambil admin berdasarkan username.

    Mencari admin dengan username yang spesifik, berguna untuk proses autentikasi
    dan validasi keunikan username.
    """
    return db.exec(select(Admin).where(Admin.username == username)).first()


def update_admin(db: Session, admin_id: int, admin: AdminUpdate) -> Admin | None:
    """
    Memperbarui data admin yang sudah ada.

    Mengambil admin berdasarkan ID, memperbarui field yang diberikan (termasuk hash password jika ada),
    memperbarui timestamp updated_at, dan menyimpan perubahan ke database.
    """
    db_admin = db.get(Admin, admin_id)
    if db_admin is None:
        return None

    admin_data = admin.dict(exclude_unset=True)

    if "password" in admin_data:
        admin_data["password"] = get_password_hash(admin_data.pop("password"))

    for key, value in admin_data.items():
        setattr(db_admin, key, value)

    db_admin.updated_at = get_indonesia_time()

    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin


def delete_admin(db: Session, admin_id: int) -> bool:
    """
    Menghapus admin dari database.

    Mencari admin berdasarkan ID, menghapusnya dari database jika ditemukan,
    dan mengembalikan status keberhasilan operasi.
    """
    admin = db.get(Admin, admin_id)
    if admin is None:
        return False

    db.delete(admin)
    db.commit()
    return True


def change_admin_password(
    db: Session, admin_id: int, current_password: str, new_password: str
) -> Admin | None | bool:
    """
    Mengubah password admin dengan verifikasi password lama.

    Memverifikasi password saat ini, mengganti dengan password baru yang di-hash,
    memperbarui timestamp, dan menyimpan perubahan ke database.
    """
    db_admin = db.get(Admin, admin_id)
    if db_admin is None:
        return None

    if not verify_password(current_password, db_admin.password):
        return False

    db_admin.password = get_password_hash(new_password)
    db_admin.updated_at = get_indonesia_time()

    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin

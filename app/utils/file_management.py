import os
from datetime import datetime


def save_uploaded_image(file, student_id: int) -> str:
    file_location = (
        f"uploads/faces/{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    )
    os.makedirs(os.path.dirname(file_location), exist_ok=True)

    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())

    return file_location

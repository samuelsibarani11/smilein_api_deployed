import cv2
import numpy as np
import base64
import io
from PIL import Image
from keras.models import load_model  # type: ignore
import os
import json
from datetime import datetime
from typing import Dict, Any, BinaryIO, Union
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FaceVerificationService:
    """
    Service class for face verification using the MobileNetV2 model with ArcFace
    """

    def __init__(self, model_path: str):
        """
        Initialize the face verification service

        Args:
            model_path: Path to the trained model file (.keras)
        """
        try:
            # Load face detection model (Haar Cascade)
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )

            # Load the face recognition model
            logger.info(f"Loading model from {model_path}")
            self.model = load_model(model_path)

            # Class labels from your model
            self.class_labels = [
                "11322005_Maria Sibarani",
                "11322007_Putri",
                "11322008_Maria Pangaribuan",
                "11322009_Iqbal",
                "11322012_Carloka",
                "11322014_Daniel Siahaan",
                "11322016_Horas",
                "11322017_Jessica",
                "11322018_Maranatha",
                "11322019_Silvi",
                "11322020_Okta",
                "11322022_Keren",
                "11322023_Mananda",
                "11322026_Aqustin",
                "11322031_Daniel Manalu",
                "11322032_Sabar",
                "11322036_Tom",
                "11322037_Hasan",
                "11322038_Samuel",
                "11322038_Kenan",
                "11322041_Cecilia",
                "11322042_Kesia",
                "11322043_Risna",
                "11322044_Kristina",
                "11322046_Indah",
                "11322047_Olivia",
                "11322048_Resa",
                "11322049_Trinita",
                "11322050_Elisabeth",
                "11322051_Sarah",
                "11322052_Blessherin",
                "11322057_Citra",
                "11322058_Dian",
                "11322059_Cesia",
                "11322060_Vanessa",
                "11322061_Johanna",
                "11322062_Monica",
                "11322063_Hagai",
            ]

            logger.info("Face verification service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing face verification service: {e}")
            raise

    def extract_nim(self, prediction: str) -> Union[str, None]:
        """
        Extract NIM from the class label

        Args:
            prediction: The predicted class label (e.g., '2019001234_Maria Sibarani')

        Returns:
            NIM or None if extraction fails
        """
        if prediction:
            parts = prediction.split("_")
            if len(parts) > 0:
                return parts[0]  # Return the NIM portion
        return None

    def preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocess image for model input

        Args:
            img: Original image in numpy array format

        Returns:
            Processed image ready for the model
        """
        # Convert to BGR if not already (for OpenCV)
        if len(img.shape) > 2 and img.shape[2] == 3:
            # Check if already BGR (OpenCV format)
            if img.dtype != np.uint8:
                img = (img * 255).astype(np.uint8)

        return img

    def detect_face(self, img: np.ndarray) -> Union[np.ndarray, None]:
        """
        Detect face in image and return the cropped face

        Args:
            img: Input image

        Returns:
            Cropped face image or None if no face detected
        """
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=6, minSize=(80, 80)
        )

        if len(faces) == 0:
            return None

        # Use first face detected (assuming one person in frame)
        x, y, w, h = faces[0]
        face = img[y : y + h, x : x + w]

        return face, (x, y, w, h)

    def verify_face(
        self, img_data: Union[str, bytes, BinaryIO], nim: str
    ) -> Dict[str, Any]:
        """
        Verify if the face in the image matches the expected student NIM

        Args:
            img_data: Can be a base64 string, a file path, or binary image data
            nim: The student NIM to verify against

        Returns:
            Dict containing verification results
        """
        try:
            # Convert image data to numpy array
            if isinstance(img_data, str):
                if img_data.startswith("data:image"):  # base64 image
                    img_data = img_data.split(",")[1]
                    img = Image.open(io.BytesIO(base64.b64decode(img_data)))
                    img = np.array(img)
                elif os.path.exists(img_data):  # file path
                    img = cv2.imread(img_data)
                else:
                    try:
                        img = Image.open(io.BytesIO(base64.b64decode(img_data)))
                        img = np.array(img)
                    except:  # noqa: E722
                        return {
                            "verified": False,
                            "message": "Invalid image data format",
                            "confidence": 0.0,
                            "predicted_id": None,
                        }
            else:  # Binary data
                try:
                    img = Image.open(io.BytesIO(img_data))
                    img = np.array(img)
                except:  # noqa: E722
                    return {
                        "verified": False,
                        "message": "Could not process image data",
                        "confidence": 0.0,
                        "predicted_id": None,
                    }

            # Preprocess image
            img = self.preprocess_image(img)

            # Detect face
            face_result = self.detect_face(img)
            if face_result is None:
                return {
                    "verified": False,
                    "message": "No face detected in the image",
                    "confidence": 0.0,
                    "predicted_id": None,
                }

            face, face_coords = face_result

            # Resize and normalize face for the model
            face_resized = cv2.resize(face, (224, 224)) / 255.0
            face_resized = np.expand_dims(face_resized, axis=0)

            # Get prediction from model
            logger.info("Running face recognition model inference")
            prediction = self.model.predict(face_resized)
            predicted_class_idx = np.argmax(prediction)
            confidence = float(prediction[0][predicted_class_idx])
            predicted_class = self.class_labels[predicted_class_idx]

            # Ekstrak NIM dari prediksi
            predicted_nim = self.extract_nim(predicted_class)

            # Periksa apakah NIM yang diprediksi cocok dengan NIM mahasiswa
            verified = predicted_nim and predicted_nim == nim

            logger.info(
                f"Face verification result: verified={verified}, confidence={confidence:.4f}, "
                f"predicted={predicted_class}, expected nim={nim}"
            )

            return {
                "verified": verified,
                "message": "Face verified successfully"
                if verified
                else "Face verification failed",
                "confidence": confidence,
                "predicted_nim": predicted_nim,
                "predicted_name": predicted_class,
                "face_coords": face_coords,
            }

        except Exception as e:
            logger.error(f"Error during face verification: {str(e)}")
            return {
                "verified": False,
                "message": f"Error during face verification: {str(e)}",
                "confidence": 0.0,
                "predicted_id": None,
            }


async def student_check_in_with_verification(
    db,
    attendance_id: int,
    check_in_data,
    image_file,
    current_user,
    model_path="/model_face_recognition/mobilenetv2_model-1a.keras",
):
    """
    Process student check-in with face verification
    Only allows check-in if face is verified

    Args:
        db: Database session
        attendance_id: ID of the attendance record
        check_in_data: Check-in data object
        image_file: Uploaded image file
        current_user: Current user object
        model_path: Path to face recognition model

    Returns:
        Dict with check-in results
    """
    try:
        # Create face verification service
        face_service = FaceVerificationService(model_path)

        # Get student NIM from current user (bukan student_id)
        nim = current_user.nim  # Menggunakan NIM dari model Student

        # Read image file
        content = await image_file.read()

        # Process image for verification
        verification_result = face_service.verify_face(content, nim)  # Gunakan NIM

        # Store verification data
        face_verification_data = json.dumps(
            {
                "verified": verification_result["verified"],
                "confidence": verification_result["confidence"],
                "predicted_name": verification_result.get("predicted_name", ""),
                "timestamp": str(datetime.now()),
            }
        )

        logger.info(
            f"Verification result for student {nim}: {verification_result['verified']}"
        )

        # Only proceed with check-in if face verification is successful
        if verification_result["verified"]:
            # Save image to uploads directory
            upload_dir = "uploads/attendance_images"
            os.makedirs(upload_dir, exist_ok=True)

            # Create filename using attendance_id and timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            file_extension = os.path.splitext(image_file.filename)[1]
            filename = f"attendance_{attendance_id}_{timestamp}{file_extension}"
            file_path = os.path.join(upload_dir, filename)

            # Reset file position for reading again
            await image_file.seek(0)
            content = await image_file.read()

            # Save image
            with open(file_path, "wb") as buffer:
                buffer.write(content)

            # Set image URL
            image_url = f"/uploads/attendance_images/{filename}"

            # Update check-in data with verification results
            check_in_data.face_verification_data = face_verification_data

            # Process check-in
            from app.crud.attendance import student_check_in

            updated_attendance = student_check_in(
                db=db,
                attendance_id=attendance_id,
                check_in_data=check_in_data,
                image_captured_url=image_url,
            )

            return {
                "success": True,
                "message": "Check-in successful",
                "attendance": updated_attendance,
                "verification": verification_result,
            }
        else:
            return {
                "success": False,
                "message": f"Face verification failed: {verification_result['message']}",
                "verification": verification_result,
            }

    except Exception as e:
        logger.error(f"Error during check-in with verification: {str(e)}")
        return {
            "success": False,
            "message": f"Error during check-in: {str(e)}",
            "verification": {"verified": False, "message": str(e)},
        }

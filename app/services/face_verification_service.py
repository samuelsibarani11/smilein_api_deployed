import cv2
import numpy as np
import base64
import io
from PIL import Image
from keras.models import load_model  # type: ignore
import os
import json
from datetime import datetime
from typing import Dict, Any, BinaryIO, Union, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FaceVerificationService:
    """
    Service class for face verification using the MobileNetV2 model with ArcFace
    Synchronized with Colab testing implementation for consistent results
    """

    def __init__(self, model_path: str):
        """
        Initialize the face verification service

        Args:
            model_path: Path to the trained model file (.keras)
        """
        try:
            # Load face detection model (Haar Cascade) - SAME AS COLAB
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )

            # Load the face recognition model
            logger.info(f"Loading model from {model_path}")
            self.model = load_model(model_path)

            # UPDATED: Class labels EXACTLY matching Colab version
            self.class_labels = [
                "11322005_Maria Sibarani",
                "11322007_Putri",
                "11322008_Maria Pangaribuan",
                "11322009_Iqbal",
                "11322012_Carloka",
                "11322016_Horas",
                "11322017_Jessica",
                "11322018_Maranatha",
                "11322019_Silvi",
                "11322020_Okta",
                "11322022_Keren",
                "11322023_Mananda",
                "11322026_Aqustin",
                "11322027_Lenni",
                "11322031_Daniel Manalu",
                "11322032_Sabar",
                "11322036_Tom",
                "11322037_Hasan",
                "11322038_Samuel",
                "11322039_Kenan",
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
            logger.info(f"Total classes loaded: {len(self.class_labels)}")
        except Exception as e:
            logger.error(f"Error initializing face verification service: {e}")
            raise

    def extract_nim(self, prediction: str) -> Union[str, None]:
        """
        Extract NIM from the class label

        Args:
            prediction: The predicted class label (e.g., '11322005_Maria Sibarani')

        Returns:
            NIM or None if extraction fails
        """
        if prediction:
            parts = prediction.split("_")
            if len(parts) > 0:
                return parts[0]  # Return the NIM portion
        return None

    def preprocess_image_for_opencv(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocess image for OpenCV operations - SAME AS COLAB

        Args:
            img: Original image in numpy array format

        Returns:
            Processed image ready for OpenCV operations
        """
        # Ensure image is in the right format for OpenCV
        if len(img.shape) == 3:
            # If image has 3 channels, ensure it's in BGR format for OpenCV
            if img.shape[2] == 3:
                # Convert from RGB to BGR if needed (PIL/Image typically loads as RGB)
                if hasattr(img, "mode") or np.max(img) <= 1.0:
                    # If it's normalized or from PIL, convert properly
                    if np.max(img) <= 1.0:
                        img = (img * 255).astype(np.uint8)
                    # Convert RGB to BGR for OpenCV
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            elif img.shape[2] == 4:  # RGBA
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

        return img

    def detect_face(
        self, img: np.ndarray
    ) -> Optional[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Detect face in image and return the cropped face - EXACTLY SAME AS COLAB

        Args:
            img: Input image in BGR format

        Returns:
            Tuple of (cropped face image, face coordinates) or None if no face detected
        """
        try:
            # Convert to grayscale for face detection - SAME AS COLAB
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Detect faces with EXACTLY SAME parameters as Colab
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=6, minSize=(80, 80)
            )

            if len(faces) == 0:
                logger.warning("No face detected in the image")
                return None

            # Use first face detected (assuming one person in frame) - SAME AS COLAB
            x, y, w, h = faces[0]
            face = img[y : y + h, x : x + w]

            logger.info(f"Face detected at coordinates: ({x}, {y}, {w}, {h})")
            return face, (x, y, w, h)

        except Exception as e:
            logger.error(f"Error in face detection: {str(e)}")
            return None

    def preprocess_face_for_model(self, face: np.ndarray) -> np.ndarray:
        """
        Preprocess detected face for model input - EXACTLY SAME AS COLAB

        Args:
            face: Cropped face image

        Returns:
            Processed face ready for model prediction
        """
        # Resize and normalize - EXACTLY SAME AS COLAB
        face_resized = cv2.resize(face, (224, 224)) / 255.0
        face_resized = np.expand_dims(face_resized, axis=0)

        return face_resized

    def convert_input_to_image(
        self, img_data: Union[str, bytes, BinaryIO]
    ) -> Optional[np.ndarray]:
        """
        Convert various input formats to numpy array image

        Args:
            img_data: Can be a base64 string, a file path, or binary image data

        Returns:
            Image as numpy array or None if conversion fails
        """
        try:
            if isinstance(img_data, str):
                if img_data.startswith("data:image"):  # base64 image
                    img_data = img_data.split(",")[1]
                    img = Image.open(io.BytesIO(base64.b64decode(img_data)))
                    img = np.array(img)
                elif os.path.exists(img_data):  # file path
                    img = cv2.imread(img_data)
                    if img is None:
                        # Try with PIL if OpenCV fails
                        img = Image.open(img_data)
                        img = np.array(img)
                else:
                    try:
                        # Try as base64 without header
                        img = Image.open(io.BytesIO(base64.b64decode(img_data)))
                        img = np.array(img)
                    except Exception:
                        logger.error("Invalid image data format")
                        return None
            else:  # Binary data
                try:
                    img = Image.open(io.BytesIO(img_data))
                    img = np.array(img)
                except Exception:
                    logger.error("Could not process binary image data")
                    return None

            return img

        except Exception as e:
            logger.error(f"Error converting input to image: {str(e)}")
            return None

    def verify_face(
        self,
        img_data: Union[str, bytes, BinaryIO],
        nim: str,
        confidence_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Verify if the face in the image matches the expected student NIM
        SYNCHRONIZED with Colab implementation for consistent results

        Args:
            img_data: Can be a base64 string, a file path, or binary image data
            nim: The student NIM to verify against
            confidence_threshold: Minimum confidence threshold for verification

        Returns:
            Dict containing verification results
        """
        try:
            # Convert image data to numpy array
            img = self.convert_input_to_image(img_data)
            if img is None:
                return {
                    "verified": False,
                    "message": "Invalid image data format",
                    "confidence": 0.0,
                    "predicted_nim": None,
                    "predicted_name": None,
                    "face_coords": None,
                }

            # Preprocess image for OpenCV operations
            img = self.preprocess_image_for_opencv(img)

            # Detect face - SAME AS COLAB
            face_result = self.detect_face(img)
            if face_result is None:
                return {
                    "verified": False,
                    "message": "No face detected in the image",
                    "confidence": 0.0,
                    "predicted_nim": None,
                    "predicted_name": None,
                    "face_coords": None,
                }

            face, face_coords = face_result

            # Preprocess face for model - EXACTLY SAME AS COLAB
            face_processed = self.preprocess_face_for_model(face)

            # Get prediction from model - SAME AS COLAB
            logger.info("Running face recognition model inference")
            prediction = self.model.predict(face_processed, verbose=0)
            predicted_class_idx = np.argmax(prediction)
            confidence = float(prediction[0][predicted_class_idx])
            predicted_class = self.class_labels[predicted_class_idx]

            logger.info(
                f"Model prediction: {predicted_class} with confidence: {confidence:.4f}"
            )

            # Extract NIM from prediction
            predicted_nim = self.extract_nim(predicted_class)

            # Check if predicted NIM matches expected NIM AND confidence is above threshold
            nim_match = predicted_nim and predicted_nim == nim
            confidence_ok = confidence >= confidence_threshold
            verified = nim_match and confidence_ok

            # Create detailed message
            if not nim_match and not confidence_ok:
                message = f"Face verification failed: Wrong person (predicted: {predicted_class}) and low confidence ({confidence:.4f})"
            elif not nim_match:
                message = f"Face verification failed: Wrong person (predicted: {predicted_class})"
            elif not confidence_ok:
                message = f"Face verification failed: Low confidence ({confidence:.4f})"
            else:
                message = "Face verified successfully"

            logger.info(
                f"Face verification result: verified={verified}, confidence={confidence:.4f}, "
                f"predicted={predicted_class}, expected_nim={nim}, nim_match={nim_match}, confidence_ok={confidence_ok}"
            )

            return {
                "verified": verified,
                "message": message,
                "confidence": confidence,
                "predicted_nim": predicted_nim,
                "predicted_name": predicted_class,
                "face_coords": face_coords,
                "confidence_threshold": confidence_threshold,
                "nim_match": nim_match,
                "confidence_ok": confidence_ok,
            }

        except Exception as e:
            logger.error(f"Error during face verification: {str(e)}")
            return {
                "verified": False,
                "message": f"Error during face verification: {str(e)}",
                "confidence": 0.0,
                "predicted_nim": None,
                "predicted_name": None,
                "face_coords": None,
            }

    def batch_verify_faces(
        self, image_paths: list, expected_results: dict = None
    ) -> Dict[str, Any]:
        """
        Batch verification for testing purposes - similar to Colab batch testing

        Args:
            image_paths: List of image file paths
            expected_results: Optional dict mapping image paths to expected NIMs

        Returns:
            Dict containing batch verification results
        """
        results = []

        for img_path in image_paths:
            if not os.path.exists(img_path):
                results.append({"image_path": img_path, "error": "File not found"})
                continue

            # Extract expected NIM from filename or provided dict
            expected_nim = None
            if expected_results and img_path in expected_results:
                expected_nim = expected_results[img_path]
            else:
                # Try to extract from filename (if follows pattern)
                filename = os.path.basename(img_path)
                if "_" in filename:
                    parts = filename.split("_")
                    if len(parts) > 0 and parts[0].isdigit():
                        expected_nim = parts[0]

            if expected_nim:
                result = self.verify_face(img_path, expected_nim)
                result["image_path"] = img_path
                result["expected_nim"] = expected_nim
                results.append(result)
            else:
                results.append(
                    {
                        "image_path": img_path,
                        "error": "Could not determine expected NIM",
                    }
                )

        # Calculate statistics
        total_images = len(results)
        successful_verifications = sum(1 for r in results if r.get("verified", False))
        failed_verifications = total_images - successful_verifications

        return {
            "results": results,
            "statistics": {
                "total_images": total_images,
                "successful_verifications": successful_verifications,
                "failed_verifications": failed_verifications,
                "success_rate": successful_verifications / total_images
                if total_images > 0
                else 0,
            },
        }


async def student_check_in_with_verification(
    db,
    attendance_id: int,
    check_in_data,
    image_file,
    current_user,
    model_path="/model_face_recognition/mobilenetv2_model-1a.keras",
    confidence_threshold: float = 0.5,  # Added configurable threshold
):
    """
    Process student check-in with face verification
    Only allows check-in if face is verified with improved accuracy

    Args:
        db: Database session
        attendance_id: ID of the attendance record
        check_in_data: Check-in data object
        image_file: Uploaded image file
        current_user: Current user object
        model_path: Path to face recognition model
        confidence_threshold: Minimum confidence threshold for verification

    Returns:
        Dict with check-in results
    """
    try:
        # Create face verification service
        face_service = FaceVerificationService(model_path)

        # Get student NIM from current user
        nim = current_user.nim

        # Read image file
        content = await image_file.read()

        # Process image for verification with threshold
        verification_result = face_service.verify_face(
            content, nim, confidence_threshold
        )

        # Store comprehensive verification data
        face_verification_data = json.dumps(
            {
                "verified": verification_result["verified"],
                "confidence": verification_result["confidence"],
                "predicted_name": verification_result.get("predicted_name", ""),
                "predicted_nim": verification_result.get("predicted_nim", ""),
                "expected_nim": nim,
                "confidence_threshold": confidence_threshold,
                "nim_match": verification_result.get("nim_match", False),
                "confidence_ok": verification_result.get("confidence_ok", False),
                "timestamp": str(datetime.now()),
            }
        )

        logger.info(
            f"Verification result for student {nim}: {verification_result['verified']} "
            f"(confidence: {verification_result['confidence']:.4f})"
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
                "message": "Check-in successful with face verification",
                "attendance": updated_attendance,
                "verification": verification_result,
            }
        else:
            return {
                "success": False,
                "message": f"Check-in denied: {verification_result['message']}",
                "verification": verification_result,
            }

    except Exception as e:
        logger.error(f"Error during check-in with verification: {str(e)}")
        return {
            "success": False,
            "message": f"Error during check-in: {str(e)}",
            "verification": {"verified": False, "message": str(e)},
        }

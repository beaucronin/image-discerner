from abc import ABC, abstractmethod
from typing import Dict, List, Any

class CVBackend(ABC):
    """Abstract base class for computer vision backends"""
    
    @abstractmethod
    def classify_image(self, image_data: bytes, image_format: str = "JPEG", image_dimensions: Dict[str, int] = None) -> Dict[str, Any]:
        """
        Classify objects in an image.
        
        Args:
            image_data: Raw image bytes
            image_format: Image format (JPEG, PNG, etc.)
            image_dimensions: Dict with 'width' and 'height' keys for accurate bounding boxes
            
        Returns:
            Dict containing classifications, confidence scores, detected objects
        """
        pass
    
    @abstractmethod
    def extract_text(self, image_data: bytes, image_format: str = "JPEG") -> Dict[str, Any]:
        """
        Extract text from an image using OCR.
        
        Args:
            image_data: Raw image bytes
            image_format: Image format (JPEG, PNG, etc.)
            
        Returns:
            Dict containing extracted text, text blocks with coordinates
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this CV provider"""
        pass
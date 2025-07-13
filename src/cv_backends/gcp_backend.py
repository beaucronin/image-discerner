import json
import boto3
import os
from typing import Dict, List, Any
from google.cloud import vision
import io
from .base import CVBackend

class GCPVisionBackend(CVBackend):
    """GCP Vision API backend for computer vision tasks"""
    
    def __init__(self):
        self.secrets_client = boto3.client('secretsmanager')
        self.vision_client = None
        self._setup_vision_client()
    
    def _setup_vision_client(self):
        """Set up GCP Vision client with credentials from AWS Secrets Manager"""
        try:
            secret_name = os.environ.get('GCP_CREDENTIALS_SECRET_NAME')
            if not secret_name:
                raise ValueError("GCP_CREDENTIALS_SECRET_NAME environment variable not set")
            
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            credentials_json = json.loads(response['SecretString'])
            
            # Create Vision client with credentials
            self.vision_client = vision.ImageAnnotatorClient.from_service_account_info(credentials_json)
            
        except Exception as e:
            print(f"Failed to set up GCP Vision client: {e}")
            self.vision_client = None
    
    def classify_image(self, image_data: bytes, image_format: str = "JPEG") -> Dict[str, Any]:
        """Classify objects in image using GCP Vision API"""
        if not self.vision_client:
            raise RuntimeError("GCP Vision client not initialized")
        
        try:
            # Prepare image for Vision API
            image = vision.Image(content=image_data)
            
            # Perform object localization and label detection
            objects = self.vision_client.object_localization(image=image).localized_object_annotations
            labels = self.vision_client.label_detection(image=image).label_annotations
            
            # Convert to our standard format
            classifications = []
            detected_objects = []
            confidence_scores = {}
            
            # Process object detections
            for obj in objects:
                classification = {
                    'category': self._categorize_object(obj.name),
                    'subcategory': obj.name.lower(),
                    'confidence': obj.score,
                    'brand': None,  # TODO: Brand detection logic
                    'bounding_box': {
                        'x': min([v.x for v in obj.bounding_poly.normalized_vertices]),
                        'y': min([v.y for v in obj.bounding_poly.normalized_vertices]),
                        'width': max([v.x for v in obj.bounding_poly.normalized_vertices]) - min([v.x for v in obj.bounding_poly.normalized_vertices]),
                        'height': max([v.y for v in obj.bounding_poly.normalized_vertices]) - min([v.y for v in obj.bounding_poly.normalized_vertices])
                    }
                }
                classifications.append(classification)
                
                detected_objects.append({
                    'name': obj.name,
                    'confidence': obj.score,
                    'bounding_box': classification['bounding_box']
                })
                
                confidence_scores[obj.name.lower()] = obj.score
            
            return {
                'classifications': classifications,
                'detected_objects': detected_objects,
                'confidence_scores': confidence_scores,
                'processing_metadata': {
                    'api_provider': 'gcp_vision',
                    'model_version': 'latest',
                    'processing_time_ms': 0  # TODO: Track actual time
                }
            }
            
        except Exception as e:
            raise RuntimeError(f"GCP Vision classification failed: {str(e)}")
    
    def extract_text(self, image_data: bytes, image_format: str = "JPEG") -> Dict[str, Any]:
        """Extract text from image using GCP Vision API OCR"""
        if not self.vision_client:
            raise RuntimeError("GCP Vision client not initialized")
        
        try:
            # Prepare image for Vision API
            image = vision.Image(content=image_data)
            
            # Perform text detection
            response = self.vision_client.text_detection(image=image)
            texts = response.text_annotations
            
            if response.error.message:
                raise Exception(f"GCP Vision API error: {response.error.message}")
            
            # Extract full text and individual text blocks
            extracted_text = texts[0].description if texts else ""
            
            text_blocks = []
            confidence_sum = 0
            for text in texts[1:]:  # Skip first element which is full text
                vertices = text.bounding_poly.vertices
                text_blocks.append({
                    'text': text.description,
                    'confidence': 0.9,  # GCP doesn't provide per-text confidence in this API
                    'bounding_box': {
                        'x': min([v.x for v in vertices]),
                        'y': min([v.y for v in vertices]),
                        'width': max([v.x for v in vertices]) - min([v.x for v in vertices]),
                        'height': max([v.y for v in vertices]) - min([v.y for v in vertices])
                    }
                })
                confidence_sum += 0.9
            
            avg_confidence = confidence_sum / len(text_blocks) if text_blocks else 0.0
            
            return {
                'extracted_text': extracted_text,
                'text_blocks': text_blocks,
                'processing_metadata': {
                    'api_provider': 'gcp_vision',
                    'text_confidence': avg_confidence,
                    'processing_time_ms': 0  # TODO: Track actual time
                }
            }
            
        except Exception as e:
            raise RuntimeError(f"GCP Vision text extraction failed: {str(e)}")
    
    def _categorize_object(self, object_name: str) -> str:
        """Map GCP object names to our categories"""
        object_name = object_name.lower()
        
        if any(word in object_name for word in ['truck', 'van', 'car', 'vehicle']):
            return 'vehicle'
        elif any(word in object_name for word in ['container', 'cargo']):
            return 'container'
        elif any(word in object_name for word in ['building', 'warehouse', 'structure']):
            return 'infrastructure'
        else:
            return 'other'
    
    def get_provider_name(self) -> str:
        return "gcp_vision"
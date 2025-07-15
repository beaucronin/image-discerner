import json
import boto3
import os
import base64
import requests
from typing import Dict, List, Any
from .base import CVBackend

class GCPVisionRestBackend(CVBackend):
    """GCP Vision API REST backend for computer vision tasks"""
    
    def __init__(self):
        self.secrets_client = boto3.client('secretsmanager')
        self.access_token = None
        self.project_id = None
        self._setup_credentials()
    
    def _setup_credentials(self):
        """Set up GCP credentials and get access token"""
        try:
            secret_name = os.environ.get('GCP_CREDENTIALS_SECRET_NAME')
            if not secret_name:
                raise ValueError("GCP_CREDENTIALS_SECRET_NAME environment variable not set")
            
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            credentials_json = json.loads(response['SecretString'])
            
            self.project_id = credentials_json['project_id']
            
            # Get OAuth2 access token using service account
            self.access_token = self._get_access_token(credentials_json)
            
        except Exception as e:
            print(f"Failed to set up GCP credentials: {e}")
            self.access_token = None
    
    def _get_access_token(self, credentials: dict) -> str:
        """Get OAuth2 access token from service account credentials"""
        import time
        import jwt
        
        # Create JWT for service account
        now = int(time.time())
        payload = {
            'iss': credentials['client_email'],
            'scope': 'https://www.googleapis.com/auth/cloud-platform',
            'aud': 'https://oauth2.googleapis.com/token',
            'iat': now,
            'exp': now + 3600
        }
        
        # Sign JWT with private key
        private_key = credentials['private_key']
        token = jwt.encode(payload, private_key, algorithm='RS256')
        
        # Exchange JWT for access token
        token_url = 'https://oauth2.googleapis.com/token'
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': token
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        return response.json()['access_token']
    
    def classify_image(self, image_data: bytes, image_format: str = "JPEG", image_dimensions: Dict[str, int] = None) -> Dict[str, Any]:
        """Classify objects in image using GCP Vision REST API"""
        if not self.access_token:
            raise RuntimeError("GCP credentials not initialized")
        
        try:
            # Encode image as base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Vision API REST endpoint
            url = f"https://vision.googleapis.com/v1/images:annotate"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Request object localization and label detection
            request_body = {
                'requests': [{
                    'image': {
                        'content': image_base64
                    },
                    'features': [
                        {'type': 'OBJECT_LOCALIZATION', 'maxResults': 10},
                        {'type': 'LABEL_DETECTION', 'maxResults': 10}
                    ]
                }]
            }
            
            response = requests.post(url, headers=headers, json=request_body)
            response.raise_for_status()
            
            result = response.json()
            
            if 'responses' not in result or not result['responses']:
                raise RuntimeError("No response from Vision API")
            
            vision_response = result['responses'][0]
            
            # Check for errors
            if 'error' in vision_response:
                raise RuntimeError(f"Vision API error: {vision_response['error']}")
            
            # Process results
            classifications = []
            detected_objects = []
            confidence_scores = {}
            
            # Process object localizations
            objects = vision_response.get('localizedObjectAnnotations', [])
            for obj in objects:
                # Convert normalized coordinates to pixel coordinates using actual image dimensions
                vertices = obj['boundingPoly']['normalizedVertices']
                # Use provided dimensions or fall back to defaults
                img_width = image_dimensions.get('width', 800) if image_dimensions else 800
                img_height = image_dimensions.get('height', 600) if image_dimensions else 600
                
                x_coords = [v.get('x', 0) * img_width for v in vertices]
                y_coords = [v.get('y', 0) * img_height for v in vertices]
                
                classification = {
                    'category': self._categorize_object(obj['name']),
                    'subcategory': obj['name'].lower(),
                    'confidence': obj['score'],
                    'brand': None,  # TODO: Brand detection logic
                    'bounding_box': {
                        'x': int(min(x_coords)),
                        'y': int(min(y_coords)),
                        'width': int(max(x_coords) - min(x_coords)),
                        'height': int(max(y_coords) - min(y_coords))
                    }
                }
                classifications.append(classification)
                
                detected_objects.append({
                    'name': obj['name'],
                    'confidence': obj['score'],
                    'bounding_box': classification['bounding_box']
                })
                
                confidence_scores[obj['name'].lower()] = obj['score']
            
            return {
                'classifications': classifications,
                'detected_objects': detected_objects,
                'confidence_scores': confidence_scores,
                'processing_metadata': {
                    'api_provider': 'gcp_vision_rest',
                    'model_version': 'latest',
                    'processing_time_ms': 0
                }
            }
            
        except Exception as e:
            raise RuntimeError(f"GCP Vision REST classification failed: {str(e)}")
    
    def extract_text(self, image_data: bytes, image_format: str = "JPEG") -> Dict[str, Any]:
        """Extract text from image using GCP Vision REST API"""
        if not self.access_token:
            raise RuntimeError("GCP credentials not initialized")
        
        try:
            # Encode image as base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Vision API REST endpoint
            url = f"https://vision.googleapis.com/v1/images:annotate"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Request text detection
            request_body = {
                'requests': [{
                    'image': {
                        'content': image_base64
                    },
                    'features': [
                        {'type': 'TEXT_DETECTION', 'maxResults': 50}
                    ]
                }]
            }
            
            response = requests.post(url, headers=headers, json=request_body)
            response.raise_for_status()
            
            result = response.json()
            
            if 'responses' not in result or not result['responses']:
                raise RuntimeError("No response from Vision API")
            
            vision_response = result['responses'][0]
            
            # Check for errors
            if 'error' in vision_response:
                raise RuntimeError(f"Vision API error: {vision_response['error']}")
            
            # Process text annotations
            text_annotations = vision_response.get('textAnnotations', [])
            
            # First annotation is the full text
            extracted_text = text_annotations[0]['description'] if text_annotations else ""
            
            # Remaining annotations are individual text blocks
            text_blocks = []
            for text_annotation in text_annotations[1:]:
                vertices = text_annotation['boundingPoly']['vertices']
                x_coords = [v.get('x', 0) for v in vertices]
                y_coords = [v.get('y', 0) for v in vertices]
                
                text_blocks.append({
                    'text': text_annotation['description'],
                    'confidence': 0.9,  # GCP doesn't provide per-text confidence in basic API
                    'bounding_box': {
                        'x': min(x_coords),
                        'y': min(y_coords),
                        'width': max(x_coords) - min(x_coords),
                        'height': max(y_coords) - min(y_coords)
                    }
                })
            
            avg_confidence = 0.9 if text_blocks else 0.0
            
            return {
                'extracted_text': extracted_text,
                'text_blocks': text_blocks,
                'processing_metadata': {
                    'api_provider': 'gcp_vision_rest',
                    'text_confidence': avg_confidence,
                    'processing_time_ms': 0
                }
            }
            
        except Exception as e:
            raise RuntimeError(f"GCP Vision REST text extraction failed: {str(e)}")
    
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
        return "gcp_vision_rest"
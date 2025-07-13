import random
import time
from typing import Dict, List, Any
from .base import CVBackend

class MockCVBackend(CVBackend):
    """Mock computer vision backend for testing and development"""
    
    def __init__(self):
        # Predefined mock data for consistent testing
        self.mock_classifications = [
            {
                'category': 'vehicle',
                'subcategory': 'truck',
                'confidence': 0.92,
                'brand': 'UPS',
                'bounding_box': {'x': 100, 'y': 50, 'width': 300, 'height': 200}
            },
            {
                'category': 'vehicle', 
                'subcategory': 'delivery_truck',
                'confidence': 0.87,
                'brand': 'FedEx',
                'bounding_box': {'x': 80, 'y': 60, 'width': 320, 'height': 180}
            },
            {
                'category': 'container',
                'subcategory': 'shipping_container',
                'confidence': 0.95,
                'brand': None,
                'bounding_box': {'x': 0, 'y': 100, 'width': 400, 'height': 150}
            },
            {
                'category': 'infrastructure',
                'subcategory': 'warehouse',
                'confidence': 0.78,
                'brand': None,
                'bounding_box': {'x': 200, 'y': 0, 'width': 600, 'height': 300}
            }
        ]
        
        self.mock_text_samples = [
            "UPS 1Z999AA1234567890",
            "FLEET 12345",
            "CONTAINER MSCU7654321",
            "LICENSE ABC123",
            "VEHICLE ID VH-9876",
            "FEDEX 7777 8888 9999",
            "TRUCK #T-4567"
        ]
    
    def classify_image(self, image_data: bytes, image_format: str = "JPEG") -> Dict[str, Any]:
        """Mock image classification that returns realistic commercial/industrial asset data"""
        start_time = time.time()
        
        # Simulate processing delay
        time.sleep(random.uniform(0.1, 0.3))
        
        # Return 1-3 random classifications
        num_classifications = random.randint(1, 3)
        selected_classifications = random.sample(self.mock_classifications, num_classifications)
        
        # Add some randomness to confidence scores
        for classification in selected_classifications:
            classification['confidence'] = max(0.5, min(1.0, classification['confidence'] + random.uniform(-0.1, 0.1)))
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            'classifications': selected_classifications,
            'detected_objects': [
                {
                    'name': cls['subcategory'],
                    'confidence': cls['confidence'],
                    'bounding_box': cls['bounding_box']
                }
                for cls in selected_classifications
            ],
            'confidence_scores': {
                cls['subcategory']: cls['confidence'] 
                for cls in selected_classifications
            },
            'processing_metadata': {
                'api_provider': 'mock_backend',
                'model_version': 'mock-v1.0',
                'processing_time_ms': processing_time
            }
        }
    
    def extract_text(self, image_data: bytes, image_format: str = "JPEG") -> Dict[str, Any]:
        """Mock text extraction that returns realistic text patterns"""
        start_time = time.time()
        
        # Simulate processing delay
        time.sleep(random.uniform(0.05, 0.2))
        
        # Select 1-4 random text samples
        num_texts = random.randint(1, 4)
        selected_texts = random.sample(self.mock_text_samples, num_texts)
        
        # Create mock text blocks with coordinates
        text_blocks = []
        y_offset = 50
        for i, text in enumerate(selected_texts):
            text_blocks.append({
                'text': text,
                'confidence': random.uniform(0.85, 0.98),
                'bounding_box': {
                    'x': random.randint(50, 200),
                    'y': y_offset + (i * 40),
                    'width': len(text) * 8,  # Approximate width
                    'height': 25
                }
            })
        
        # Join all text
        extracted_text = " ".join(selected_texts)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            'extracted_text': extracted_text,
            'text_blocks': text_blocks,
            'processing_metadata': {
                'api_provider': 'mock_backend',
                'text_confidence': sum(block['confidence'] for block in text_blocks) / len(text_blocks) if text_blocks else 0.0,
                'processing_time_ms': processing_time
            }
        }
    
    def get_provider_name(self) -> str:
        return "mock_backend"
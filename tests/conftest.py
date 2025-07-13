import pytest
import os
import sys

# Add src directory to Python path for testing
test_dir = os.path.dirname(__file__)
src_dir = os.path.join(test_dir, '..', 'src')
sys.path.insert(0, os.path.abspath(src_dir))

@pytest.fixture
def sample_image_data():
    """Fixture providing sample image data for testing"""
    return b"fake_image_data_for_testing"

@pytest.fixture
def sample_classification_result():
    """Fixture providing sample classification result"""
    return {
        'classifications': [
            {
                'category': 'vehicle',
                'subcategory': 'truck',
                'confidence': 0.92,
                'brand': 'UPS',
                'bounding_box': {'x': 100, 'y': 50, 'width': 300, 'height': 200}
            }
        ],
        'detected_objects': [
            {
                'name': 'truck',
                'confidence': 0.92,
                'bounding_box': {'x': 100, 'y': 50, 'width': 300, 'height': 200}
            }
        ],
        'confidence_scores': {'truck': 0.92},
        'processing_metadata': {
            'api_provider': 'mock_backend',
            'model_version': 'mock-v1.0',
            'processing_time_ms': 150
        }
    }

@pytest.fixture
def sample_text_result():
    """Fixture providing sample text extraction result"""
    return {
        'extracted_text': 'UPS 1Z999AA1234567890 FLEET 12345',
        'text_blocks': [
            {
                'text': 'UPS 1Z999AA1234567890',
                'confidence': 0.95,
                'bounding_box': {'x': 50, 'y': 100, 'width': 200, 'height': 30}
            },
            {
                'text': 'FLEET 12345',
                'confidence': 0.90,
                'bounding_box': {'x': 50, 'y': 140, 'width': 120, 'height': 25}
            }
        ],
        'processing_metadata': {
            'api_provider': 'mock_backend',
            'text_confidence': 0.925,
            'processing_time_ms': 120
        }
    }

@pytest.fixture
def mock_lambda_context():
    """Fixture providing mock Lambda context"""
    class MockContext:
        def __init__(self):
            self.aws_request_id = 'test-request-id-12345'
            self.function_name = 'test-function'
            self.function_version = '$LATEST'
            self.invoked_function_arn = 'arn:aws:lambda:us-west-2:123456789012:function:test-function'
            self.memory_limit_in_mb = 128
            self.remaining_time_in_millis = lambda: 30000
    
    return MockContext()

@pytest.fixture
def mock_s3_event():
    """Fixture providing mock S3 event data"""
    return {
        'image_key': 'test-images/sample.jpg',
        'bucket_name': 'test-image-bucket'
    }

@pytest.fixture
def mock_step_function_parallel_results():
    """Fixture providing mock Step Functions parallel execution results"""
    return [
        {
            'body': {
                'image_key': 'processed/test.jpg',
                'classifications': [
                    {
                        'category': 'vehicle',
                        'subcategory': 'truck',
                        'confidence': 0.92,
                        'brand': 'UPS'
                    }
                ],
                'detected_objects': [],
                'confidence_scores': {'truck': 0.92},
                'processing_metadata': {
                    'api_provider': 'mock_backend',
                    'processing_time_ms': 150
                }
            }
        },
        {
            'body': {
                'image_key': 'processed/test.jpg',
                'extracted_text': 'UPS 1Z999AA1234567890 FLEET 12345',
                'text_blocks': [],
                'structured_identifiers': {
                    'container_ids': [],
                    'fleet_numbers': ['12345'],
                    'license_plates': []
                },
                'processing_metadata': {
                    'api_provider': 'mock_backend',
                    'text_confidence': 0.95,
                    'processing_time_ms': 120
                }
            }
        }
    ]
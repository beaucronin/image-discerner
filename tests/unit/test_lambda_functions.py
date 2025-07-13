import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

class TestPreprocessLambda:
    """Unit tests for preprocess Lambda function"""
    
    def setup_method(self):
        # Mock the Lambda context
        self.context = Mock()
        self.context.aws_request_id = 'test-request-id'
    
    def test_preprocess_handler_missing_parameters(self):
        """Test preprocess handler with missing parameters"""
        from lambdas.preprocess import handler
        
        # Test missing image_key
        event = {'bucket_name': 'test-bucket'}
        result = handler(event, self.context)
        
        assert result['statusCode'] == 400
        assert 'Missing required parameters' in result['body']['error']
        
        # Test missing bucket_name
        event = {'image_key': 'test-image.jpg'}
        result = handler(event, self.context)
        
        assert result['statusCode'] == 400
        assert 'Missing required parameters' in result['body']['error']
    
    def test_preprocess_handler_success(self):
        """Test preprocess handler success case"""
        from lambdas.preprocess import handler
        
        event = {
            'image_key': 'test-image.jpg',
            'bucket_name': 'test-bucket'
        }
        
        result = handler(event, self.context)
        
        assert result['statusCode'] == 200
        body = result['body']
        assert body['original_image_key'] == 'test-image.jpg'
        assert body['processed_image_key'] == 'processed/test-image.jpg'
        assert body['bucket_name'] == 'test-bucket'
        assert 'processing_metadata' in body

class TestClassifyLambda:
    """Unit tests for classify Lambda function"""
    
    def setup_method(self):
        self.context = Mock()
        self.context.aws_request_id = 'test-request-id'
        
        # Mock CV backend
        self.mock_backend = Mock()
        self.mock_backend.classify_image.return_value = {
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
    
    def test_classify_handler_missing_parameters(self):
        """Test classify handler with missing parameters"""
        with patch('lambdas.classify.get_cv_backend', return_value=self.mock_backend):
            from lambdas.classify import handler
            
            event = {'bucket_name': 'test-bucket'}
            result = handler(event, self.context)
            
            assert result['statusCode'] == 400
            assert 'Missing required parameters' in result['body']['error']
    
    @patch('lambdas.classify.s3_client')
    def test_classify_handler_s3_error(self, mock_s3):
        """Test classify handler with S3 download error"""
        mock_s3.get_object.side_effect = Exception("S3 error")
        
        with patch('lambdas.classify.get_cv_backend', return_value=self.mock_backend):
            from lambdas.classify import handler
            
            event = {
                'processed_image_key': 'processed/test.jpg',
                'bucket_name': 'test-bucket'
            }
            
            result = handler(event, self.context)
            
            assert result['statusCode'] == 404
            assert 'Failed to download image from S3' in result['body']['error']
    
    @patch('lambdas.classify.s3_client')
    def test_classify_handler_success(self, mock_s3):
        """Test classify handler success case"""
        # Mock S3 response
        mock_body = Mock()
        mock_body.read.return_value = b'fake_image_data'
        mock_response = {'Body': mock_body}
        mock_s3.get_object.return_value = mock_response
        
        with patch('lambdas.classify.get_cv_backend', return_value=self.mock_backend):
            from lambdas.classify import handler
            
            event = {
                'processed_image_key': 'processed/test.jpg',
                'bucket_name': 'test-bucket'
            }
            
            result = handler(event, self.context)
            
            assert result['statusCode'] == 200
            body = result['body']
            assert body['image_key'] == 'processed/test.jpg'
            assert len(body['classifications']) == 1
            assert body['classifications'][0]['category'] == 'vehicle'
            
            # Verify S3 was called correctly
            mock_s3.get_object.assert_called_once_with(
                Bucket='test-bucket',
                Key='processed/test.jpg'
            )
            
            # Verify backend was called correctly
            self.mock_backend.classify_image.assert_called_once_with(b'fake_image_data')

class TestExtractTextLambda:
    """Unit tests for extract_text Lambda function"""
    
    def setup_method(self):
        self.context = Mock()
        self.context.aws_request_id = 'test-request-id'
        
        # Mock CV backend
        self.mock_backend = Mock()
        self.mock_backend.extract_text.return_value = {
            'extracted_text': 'UPS 1Z999AA1234567890 FLEET 12345',
            'text_blocks': [
                {
                    'text': 'UPS 1Z999AA1234567890',
                    'confidence': 0.95,
                    'bounding_box': {'x': 50, 'y': 100, 'width': 200, 'height': 30}
                }
            ],
            'processing_metadata': {
                'api_provider': 'mock_backend',
                'text_confidence': 0.95,
                'processing_time_ms': 120
            }
        }
    
    @patch('lambdas.extract_text.s3_client')
    def test_extract_text_handler_success(self, mock_s3):
        """Test extract_text handler success case"""
        # Mock S3 response
        mock_body = Mock()
        mock_body.read.return_value = b'fake_image_data'
        mock_response = {'Body': mock_body}
        mock_s3.get_object.return_value = mock_response
        
        with patch('lambdas.extract_text.get_cv_backend', return_value=self.mock_backend):
            from lambdas.extract_text import handler
            
            event = {
                'processed_image_key': 'processed/test.jpg',
                'bucket_name': 'test-bucket'
            }
            
            result = handler(event, self.context)
            
            assert result['statusCode'] == 200
            body = result['body']
            assert body['image_key'] == 'processed/test.jpg'
            assert body['extracted_text'] == 'UPS 1Z999AA1234567890 FLEET 12345'
            
            # Check structured identifiers were parsed
            identifiers = body['structured_identifiers']
            assert 'container_ids' in identifiers
            assert 'fleet_numbers' in identifiers
            assert 'license_plates' in identifiers
            
            # Verify backend was called correctly
            self.mock_backend.extract_text.assert_called_once_with(b'fake_image_data')
    
    def test_extract_text_parsing_functions(self):
        """Test the text parsing utility functions"""
        from lambdas.extract_text import extract_container_ids, extract_fleet_numbers, extract_license_plates
        
        # Test container ID extraction
        text_with_container = "Container MSCU7654321 is ready"
        container_ids = extract_container_ids(text_with_container)
        assert len(container_ids) == 1
        assert 'MSCU7654321' in container_ids[0]
        
        # Test fleet number extraction
        text_with_fleet = "FLEET 12345 departing"
        fleet_numbers = extract_fleet_numbers(text_with_fleet)
        assert len(fleet_numbers) > 0
        
        # Test license plate extraction
        text_with_plate = "ABC 123 license plate"
        plates = extract_license_plates(text_with_plate)
        assert len(plates) > 0

class TestAggregateLambda:
    """Unit tests for aggregate Lambda function"""
    
    def setup_method(self):
        self.context = Mock()
        self.context.aws_request_id = 'test-request-id'
    
    def test_aggregate_handler_missing_results(self):
        """Test aggregate handler with missing parallel results"""
        from lambdas.aggregate import handler
        
        event = {'body': []}  # Empty results
        result = handler(event, self.context)
        
        assert result['statusCode'] == 400
        assert 'Expected 2 parallel results' in result['body']['error']
    
    def test_aggregate_handler_success(self):
        """Test aggregate handler with valid parallel results"""
        from lambdas.aggregate import handler
        
        # Mock parallel results from Step Functions
        event = {
            'body': [
                {
                    'body': {
                        'classifications': [
                            {
                                'category': 'vehicle',
                                'subcategory': 'truck',
                                'confidence': 0.92,
                                'brand': 'UPS'
                            }
                        ],
                        'confidence_scores': {'truck': 0.92},
                        'processing_metadata': {
                            'api_provider': 'mock_backend',
                            'processing_time_ms': 150
                        },
                        'image_key': 'processed/test.jpg'
                    }
                },
                {
                    'body': {
                        'extracted_text': 'UPS 1Z999AA1234567890 FLEET 12345',
                        'structured_identifiers': {
                            'container_ids': [],
                            'fleet_numbers': ['12345'],
                            'license_plates': []
                        },
                        'processing_metadata': {
                            'api_provider': 'mock_backend',
                            'text_confidence': 0.95,
                            'processing_time_ms': 120
                        },
                        'image_key': 'processed/test.jpg'
                    }
                }
            ]
        }
        
        result = handler(event, self.context)
        
        assert result['statusCode'] == 200
        body = result['body']
        assert body['analysis_complete'] is True
        assert 'timestamp' in body
        assert 'image_classification' in body
        assert 'text_analysis' in body
        assert isinstance(body['confidence_score'], float)
        
        # Check that fleet numbers were merged with truck classification
        detected_items = body['image_classification']['detected_items']
        assert len(detected_items) > 0
        truck_item = detected_items[0]
        assert truck_item['category'] == 'vehicle'
        assert 'fleet_numbers' in truck_item
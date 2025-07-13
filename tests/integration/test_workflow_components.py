import pytest
import json
import boto3
from moto import mock_aws
from unittest.mock import patch, Mock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

@pytest.mark.integration
class TestWorkflowComponents:
    """Integration tests for workflow components"""
    
    @mock_aws
    def test_end_to_end_mock_workflow(self):
        """Test end-to-end workflow with mock CV backend"""
        # Set up S3
        s3_client = boto3.client('s3', region_name='us-west-2')
        bucket_name = 'test-image-bucket'
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        
        # Upload test image
        test_image_key = 'test-image.jpg'
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_image_key,
            Body=b'fake_image_data'
        )
        
        # Test the complete workflow step by step
        with patch.dict(os.environ, {'CV_BACKEND': 'mock'}):
            
            # Step 1: Preprocess
            from lambdas.preprocess import handler as preprocess_handler
            preprocess_event = {
                'image_key': test_image_key,
                'bucket_name': bucket_name
            }
            preprocess_result = preprocess_handler(preprocess_event, Mock())
            
            assert preprocess_result['statusCode'] == 200
            processed_key = preprocess_result['body']['processed_image_key']
            
            # Upload the "processed" image for next steps
            s3_client.put_object(
                Bucket=bucket_name,
                Key=processed_key,
                Body=b'fake_processed_image_data'
            )
            
            # Step 2: Parallel processing - Classification
            with patch('lambdas.classify.s3_client', s3_client):
                from lambdas.classify import handler as classify_handler
                classify_event = {
                    'processed_image_key': processed_key,
                    'bucket_name': bucket_name
                }
                classify_result = classify_handler(classify_event, Mock())
            
            assert classify_result['statusCode'] == 200
            assert len(classify_result['body']['classifications']) > 0
            
            # Step 3: Parallel processing - Text extraction
            with patch('lambdas.extract_text.s3_client', s3_client):
                from lambdas.extract_text import handler as extract_text_handler
                extract_text_event = {
                    'processed_image_key': processed_key,
                    'bucket_name': bucket_name
                }
                extract_text_result = extract_text_handler(extract_text_event, Mock())
            
            assert extract_text_result['statusCode'] == 200
            assert len(extract_text_result['body']['extracted_text']) > 0
            
            # Step 4: Aggregate results
            from lambdas.aggregate import handler as aggregate_handler
            aggregate_event = {
                'body': [classify_result, extract_text_result]
            }
            aggregate_result = aggregate_handler(aggregate_event, Mock())
            
            assert aggregate_result['statusCode'] == 200
            assert aggregate_result['body']['analysis_complete'] is True
            assert 'image_classification' in aggregate_result['body']
            assert 'text_analysis' in aggregate_result['body']
            assert isinstance(aggregate_result['body']['confidence_score'], float)
    
    def test_cv_backend_integration(self):
        """Test CV backend integration with factory pattern"""
        with patch.dict(os.environ, {'CV_BACKEND': 'mock'}):
            from cv_backends.factory import get_cv_backend
            
            backend = get_cv_backend()
            
            # Test classification
            classify_result = backend.classify_image(b'fake_image_data')
            assert 'classifications' in classify_result
            assert 'processing_metadata' in classify_result
            assert classify_result['processing_metadata']['api_provider'] == 'mock_backend'
            
            # Test text extraction
            text_result = backend.extract_text(b'fake_image_data')
            assert 'extracted_text' in text_result
            assert 'processing_metadata' in text_result
            assert text_result['processing_metadata']['api_provider'] == 'mock_backend'
    
    def test_text_parsing_integration(self):
        """Test text parsing functions with realistic data"""
        from lambdas.extract_text import extract_container_ids, extract_fleet_numbers, extract_license_plates
        
        # Test with realistic commercial text
        sample_text = """
        UPS TRUCK
        FLEET NUMBER: 12345
        LICENSE: ABC 123
        CONTAINER MSCU7654321
        VEHICLE ID: VH-9876
        """
        
        # Test container ID extraction
        container_ids = extract_container_ids(sample_text)
        assert len(container_ids) > 0
        assert any('MSCU7654321' in cid for cid in container_ids)
        
        # Test fleet number extraction
        fleet_numbers = extract_fleet_numbers(sample_text)
        assert len(fleet_numbers) > 0
        
        # Test license plate extraction
        license_plates = extract_license_plates(sample_text)
        assert len(license_plates) > 0
    
    def test_result_aggregation_logic(self):
        """Test result aggregation and enhancement logic"""
        from lambdas.aggregate import merge_identifiers_with_classifications, calculate_overall_confidence
        
        # Test data
        classifications = [
            {
                'category': 'vehicle',
                'subcategory': 'truck',
                'confidence': 0.92,
                'brand': 'UPS'
            }
        ]
        
        text_identifiers = {
            'container_ids': [],
            'fleet_numbers': ['12345'],
            'license_plates': ['ABC123']
        }
        
        # Test merging
        enhanced = merge_identifiers_with_classifications(classifications, text_identifiers)
        assert len(enhanced) == 1
        truck_item = enhanced[0]
        assert truck_item['category'] == 'vehicle'
        assert 'fleet_numbers' in truck_item
        assert 'license_plates' in truck_item
        
        # Test confidence calculation
        classification_results = {'confidence_scores': {'truck': 0.92}}
        text_results = {'processing_metadata': {'text_confidence': 0.95}}
        
        confidence = calculate_overall_confidence(classification_results, text_results)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.8  # Should be high given good input data
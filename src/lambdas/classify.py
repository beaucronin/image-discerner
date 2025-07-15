import json
import boto3
import os
import sys

# Add the cv_backends module to the path
sys.path.append('/opt/python')
sys.path.append('.')

from cv_backends.factory import get_classification_backend

s3_client = boto3.client('s3')

def handler(event, context):
    """
    Classifies images using configurable CV backend.
    
    - Loads image from S3
    - Calls CV backend for object detection and classification
    - Identifies commercial/industrial vehicles and infrastructure
    """
    try:
        processed_image_key = event.get('processed_image_key')
        bucket_name = event.get('bucket_name')
        image_dimensions = event.get('image_dimensions')
        
        if not processed_image_key or not bucket_name:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Missing required parameters: processed_image_key, bucket_name'
                }
            }
        
        # Get classification backend (mock, gcp_vision, or gcp_automl)
        cv_backend = get_classification_backend()
        
        # Download image from S3 (try processed first, fallback to original)
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=processed_image_key)
            image_data = response['Body'].read()
        except Exception as e:
            # Fallback to original image if processed doesn't exist
            try:
                original_key = event.get('original_image_key', processed_image_key.replace('processed/', ''))
                response = s3_client.get_object(Bucket=bucket_name, Key=original_key)
                image_data = response['Body'].read()
            except Exception as e2:
                return {
                    'statusCode': 404,
                    'body': {
                        'error': f'Failed to download image from S3: {str(e2)}'
                    }
                }
        
        # Classify image using CV backend with image dimensions
        classification_result = cv_backend.classify_image(image_data, image_dimensions=image_dimensions)
        
        return {
            'statusCode': 200,
            'body': {
                'image_key': processed_image_key,
                'classifications': classification_result.get('classifications', []),
                'detected_objects': classification_result.get('detected_objects', []),
                'confidence_scores': classification_result.get('confidence_scores', {}),
                'processing_metadata': classification_result.get('processing_metadata', {})
            }
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'error': f'Classification failed: {str(e)}'
            }
        }
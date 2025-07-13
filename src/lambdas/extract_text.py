import json
import boto3
import re
import os
import sys

# Add the cv_backends module to the path
sys.path.append('/opt/python')
sys.path.append('.')

from cv_backends.factory import get_cv_backend

s3_client = boto3.client('s3')

def extract_container_ids(text):
    """Extract shipping container IDs using standard format patterns"""
    # Standard container ID format: 4 letters + 6-7 digits + check digit
    container_pattern = r'\b[A-Z]{4}\s?[0-9]{6,7}\s?[0-9]\b'
    return re.findall(container_pattern, text, re.IGNORECASE)

def extract_fleet_numbers(text):
    """Extract fleet/vehicle numbers from various formats"""
    # Common patterns for fleet numbers
    patterns = [
        r'\b(?:FLEET|VEHICLE|UNIT)\s*[#:]?\s*([A-Z0-9]+)\b',
        r'\b[A-Z]{2,4}\s*[0-9]{3,6}\b',  # Generic alphanumeric IDs
    ]
    
    fleet_numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        fleet_numbers.extend(matches)
    
    return fleet_numbers

def extract_license_plates(text):
    """Extract license plate numbers"""
    # US license plate patterns (simplified)
    plate_patterns = [
        r'\b[A-Z0-9]{2,3}\s*[A-Z0-9]{3,4}\b',
        r'\b[A-Z]{3}\s*[0-9]{3,4}\b',
        r'\b[0-9]{3}\s*[A-Z]{3}\b'
    ]
    
    plates = []
    for pattern in plate_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        plates.extend(matches)
    
    return plates

def handler(event, context):
    """
    Extracts text and structured identifiers from images using configurable CV backend.
    
    - Loads image from S3
    - Performs OCR using CV backend
    - Parses text for specific patterns (container IDs, fleet numbers, etc.)
    """
    try:
        processed_image_key = event.get('processed_image_key')
        bucket_name = event.get('bucket_name')
        
        if not processed_image_key or not bucket_name:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Missing required parameters: processed_image_key, bucket_name'
                }
            }
        
        # Get CV backend (mock or real)
        cv_backend = get_cv_backend()
        
        # Download image from S3
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=processed_image_key)
            image_data = response['Body'].read()
        except Exception as e:
            return {
                'statusCode': 404,
                'body': {
                    'error': f'Failed to download image from S3: {str(e)}'
                }
            }
        
        # Extract text using CV backend
        text_result = cv_backend.extract_text(image_data)
        extracted_text = text_result.get('extracted_text', '')
        
        # Parse structured identifiers from extracted text
        container_ids = extract_container_ids(extracted_text)
        fleet_numbers = extract_fleet_numbers(extracted_text)
        license_plates = extract_license_plates(extracted_text)
        
        return {
            'statusCode': 200,
            'body': {
                'image_key': processed_image_key,
                'extracted_text': extracted_text,
                'text_blocks': text_result.get('text_blocks', []),
                'structured_identifiers': {
                    'container_ids': container_ids,
                    'fleet_numbers': fleet_numbers,
                    'license_plates': license_plates,
                    'other_codes': []
                },
                'processing_metadata': text_result.get('processing_metadata', {})
            }
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'error': f'Text extraction failed: {str(e)}'
            }
        }
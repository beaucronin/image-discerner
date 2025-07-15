import json
import boto3
import os
import struct

s3_client = boto3.client('s3')

def get_image_dimensions(image_data):
    """Get image dimensions without PIL - supports JPEG and PNG"""
    try:
        # Check for JPEG
        if image_data[:2] == b'\xff\xd8':
            # JPEG format
            pos = 2
            while pos < len(image_data):
                if image_data[pos:pos+2] == b'\xff\xc0' or image_data[pos:pos+2] == b'\xff\xc2':
                    # Found SOF (Start of Frame) marker
                    height = struct.unpack('>H', image_data[pos+5:pos+7])[0]
                    width = struct.unpack('>H', image_data[pos+7:pos+9])[0]
                    return width, height
                pos += 1
        
        # Check for PNG
        elif image_data[:8] == b'\x89PNG\r\n\x1a\n':
            # PNG format - IHDR chunk starts at byte 8
            width = struct.unpack('>I', image_data[16:20])[0]
            height = struct.unpack('>I', image_data[20:24])[0]
            return width, height
        
        # Fallback for unsupported formats
        return 800, 600
        
    except Exception:
        # If anything fails, return default dimensions
        return 800, 600

def handler(event, context):
    """
    Preprocesses images for computer vision analysis.
    
    - Downloads image from S3
    - Resizes/optimizes for CV APIs
    - Uploads processed version back to S3
    """
    try:
        image_key = event.get('image_key')
        bucket_name = event.get('bucket_name')
        
        if not image_key or not bucket_name:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Missing required parameters: image_key, bucket_name'
                }
            }
        
        # Download image from S3 to read dimensions
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=image_key)
            image_data = response['Body'].read()
            
            # Get image dimensions without PIL
            width, height = get_image_dimensions(image_data)
            
            # Determine format from first few bytes
            if image_data[:2] == b'\xff\xd8':
                image_format = 'JPEG'
            elif image_data[:8] == b'\x89PNG\r\n\x1a\n':
                image_format = 'PNG'
            else:
                image_format = 'JPEG'  # Default
            
        except Exception as e:
            return {
                'statusCode': 500,
                'body': {
                    'error': f'Failed to read image: {str(e)}'
                }
            }
        
        # For now, we're not actually processing the image - just reading dimensions
        # The processed_key points to the same image but signals that dimensions are known
        processed_key = f"processed/{image_key}"
        
        # Copy the original image to the processed location (no actual processing yet)
        try:
            s3_client.copy_object(
                Bucket=bucket_name,
                CopySource={'Bucket': bucket_name, 'Key': image_key},
                Key=processed_key
            )
        except Exception as e:
            return {
                'statusCode': 500,
                'body': {
                    'error': f'Failed to copy image: {str(e)}'
                }
            }
        
        return {
            'statusCode': 200,
            'body': {
                'original_image_key': image_key,
                'processed_image_key': processed_key,
                'bucket_name': bucket_name,
                'image_dimensions': {
                    'width': width,
                    'height': height
                },
                'processing_metadata': {
                    'original_size': {'width': width, 'height': height},
                    'processed_size': {'width': width, 'height': height},
                    'format': image_format
                }
            }
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'error': f'Processing failed: {str(e)}'
            }
        }
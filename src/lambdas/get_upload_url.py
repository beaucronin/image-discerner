import boto3
import json
import uuid
from datetime import datetime, timezone

s3_client = boto3.client('s3')

def handler(event, context):
    """
    Generate pre-signed URLs for direct S3 uploads from mobile apps.
    
    This provides secure, time-limited upload access without exposing
    permanent AWS credentials to mobile devices.
    """
    try:
        # Parse request body if it's a string
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Get file extension (default to jpg)
        file_extension = body.get('file_extension', 'jpg').lower()
        
        # Validate file extension
        allowed_extensions = ['jpg', 'jpeg', 'png', 'heic', 'heif']
        if file_extension not in allowed_extensions:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': f'Invalid file extension. Allowed: {", ".join(allowed_extensions)}'
                })
            }
        
        # Generate unique filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        filename = f"uploads/{timestamp}-{unique_id}.{file_extension}"
        
        # Get bucket name from environment
        bucket_name = 'image-discerner-dev'  # Could be from env var
        
        # Generate pre-signed URL for PUT operation (15 minute expiry)
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': filename,
                'ContentType': f'image/{file_extension}',
                'ServerSideEncryption': 'AES256'
            },
            ExpiresIn=900  # 15 minutes
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({
                'upload_url': presigned_url,
                'image_key': filename,
                'bucket_name': bucket_name,
                'expires_in': 900,
                'content_type': f'image/{file_extension}'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': f'Failed to generate upload URL: {str(e)}'
            })
        }
import json
import boto3
import os
from datetime import datetime, timezone

stepfunctions = boto3.client('stepfunctions')

def handler(event, context):
    """
    API Gateway handler that triggers Step Functions workflow.
    
    Accepts HTTP POST requests with image analysis parameters and starts
    the Step Functions execution for image processing pipeline.
    """
    try:
        # Parse the request
        if event.get('body'):
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        # Validate required fields
        if not body.get('image_key') or not body.get('bucket_name'):
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Missing required fields: image_key, bucket_name',
                    'example': {
                        'image_key': 'images/truck-photo.jpg',
                        'bucket_name': 'image-discerner-dev'
                    }
                })
            }
        
        # Execute Step Functions synchronously
        execution_name = f"analysis-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        
        # Start execution
        start_response = stepfunctions.start_execution(
            stateMachineArn=os.environ['STEP_FUNCTION_ARN'],
            name=execution_name,
            input=json.dumps(body)
        )
        
        execution_arn = start_response['executionArn']
        
        # Wait for execution to complete and get results
        import time
        max_wait_time = 300  # 5 minutes timeout
        poll_interval = 2    # Check every 2 seconds
        waited_time = 0
        
        while waited_time < max_wait_time:
            describe_response = stepfunctions.describe_execution(
                executionArn=execution_arn
            )
            
            status = describe_response['status']
            
            if status == 'SUCCEEDED':
                # Parse and return the final result
                output = json.loads(describe_response['output'])
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'success': True,
                        'execution_arn': execution_arn,
                        'execution_name': execution_name,
                        'analysis_result': output,
                        'processing_time_seconds': waited_time
                    })
                }
            elif status == 'FAILED':
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'success': False,
                        'error': 'Step Functions execution failed',
                        'execution_arn': execution_arn,
                        'cause': describe_response.get('cause', 'Unknown error')
                    })
                }
            elif status in ['ABORTED', 'TIMED_OUT']:
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'success': False,
                        'error': f'Step Functions execution {status.lower()}',
                        'execution_arn': execution_arn
                    })
                }
            
            # Still running, wait and check again
            time.sleep(poll_interval)
            waited_time += poll_interval
        
        # Timeout reached
        return {
            'statusCode': 504,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': False,
                'error': 'Request timeout - analysis took longer than expected',
                'execution_arn': execution_arn,
                'timeout_seconds': max_wait_time
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': f'Failed to start analysis: {str(e)}'
            })
        }
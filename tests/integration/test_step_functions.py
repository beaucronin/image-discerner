import pytest
import json
import boto3
from moto import mock_aws
from unittest.mock import patch, Mock

@pytest.mark.integration
class TestStepFunctionsWorkflow:
    """Integration tests for the complete Step Functions workflow"""
    
    def _create_step_function(self, stepfunctions_client, iam_client):
        """Create the Step Functions state machine"""
        # Create IAM role for Step Functions
        iam_client.create_role(
            RoleName='test-stepfunctions-role',
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "states.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }
                ]
            })
        )
        
        # Use mock ARNs since we're not actually creating Lambda functions
        preprocess_arn = 'arn:aws:lambda:us-west-2:123456789012:function:preprocess'
        classify_arn = 'arn:aws:lambda:us-west-2:123456789012:function:classify'
        extract_text_arn = 'arn:aws:lambda:us-west-2:123456789012:function:extract_text'
        aggregate_arn = 'arn:aws:lambda:us-west-2:123456789012:function:aggregate'
        
        definition = {
            "Comment": "Image analysis pipeline",
            "StartAt": "PreprocessImage",
            "States": {
                "PreprocessImage": {
                    "Type": "Task",
                    "Resource": preprocess_arn,
                    "Next": "ParallelAnalysis"
                },
                "ParallelAnalysis": {
                    "Type": "Parallel",
                    "Branches": [
                        {
                            "StartAt": "ClassifyImage",
                            "States": {
                                "ClassifyImage": {
                                    "Type": "Task",
                                    "Resource": classify_arn,
                                    "End": True
                                }
                            }
                        },
                        {
                            "StartAt": "ExtractText",
                            "States": {
                                "ExtractText": {
                                    "Type": "Task",
                                    "Resource": extract_text_arn,
                                    "End": True
                                }
                            }
                        }
                    ],
                    "Next": "AggregateResults"
                },
                "AggregateResults": {
                    "Type": "Task",
                    "Resource": aggregate_arn,
                    "End": True
                }
            }
        }
        
        response = stepfunctions_client.create_state_machine(
            name='test-image-analysis-pipeline',
            definition=json.dumps(definition),
            roleArn='arn:aws:iam::123456789012:role/test-stepfunctions-role'
        )
        return response['stateMachineArn']
    
    @mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
    def test_step_function_creation(self):
        """Test Step Functions state machine creation"""
        stepfunctions_client = boto3.client('stepfunctions', region_name='us-west-2')
        iam_client = boto3.client('iam', region_name='us-west-2')
        
        state_machine_arn = self._create_step_function(stepfunctions_client, iam_client)
        
        # Verify state machine was created
        response = stepfunctions_client.describe_state_machine(
            stateMachineArn=state_machine_arn
        )
        
        assert response['name'] == 'test-image-analysis-pipeline'
        assert 'definition' in response
        
        # Parse definition to verify structure
        definition = json.loads(response['definition'])
        assert definition['StartAt'] == 'PreprocessImage'
        assert 'States' in definition
        assert 'PreprocessImage' in definition['States']
        assert 'ParallelAnalysis' in definition['States']
        assert 'AggregateResults' in definition['States']
    
    @mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
    def test_step_function_execution_start(self):
        """Test starting Step Functions execution"""
        stepfunctions_client = boto3.client('stepfunctions', region_name='us-west-2')
        iam_client = boto3.client('iam', region_name='us-west-2')
        s3_client = boto3.client('s3', region_name='us-west-2')
        
        # Create S3 bucket
        bucket_name = 'test-image-bucket'
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        
        state_machine_arn = self._create_step_function(stepfunctions_client, iam_client)
        
        # Upload a test image to S3
        test_image_key = 'test-image.jpg'
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_image_key,
            Body=b'fake_image_data'
        )
        
        # Start Step Functions execution
        input_data = {
            'image_key': test_image_key,
            'bucket_name': bucket_name
        }
        
        response = stepfunctions_client.start_execution(
            stateMachineArn=state_machine_arn,
            name='test-execution',
            input=json.dumps(input_data)
        )
        
        execution_arn = response['executionArn']
        assert execution_arn.startswith('arn:aws:states:')
        
        # Describe execution
        execution = stepfunctions_client.describe_execution(executionArn=execution_arn)
        
        # Verify execution details
        assert execution['stateMachineArn'] == state_machine_arn
        assert execution['name'] == 'test-execution'
        
        # Verify the input was passed correctly
        input_parsed = json.loads(execution['input'])
        assert input_parsed['image_key'] == test_image_key
        assert input_parsed['bucket_name'] == bucket_name
    
    @mock_aws(config={"stepfunctions": {"execute_state_machine": True}})
    def test_step_function_list_executions(self):
        """Test listing Step Functions executions"""
        stepfunctions_client = boto3.client('stepfunctions', region_name='us-west-2')
        iam_client = boto3.client('iam', region_name='us-west-2')
        
        bucket_name = 'test-image-bucket'
        state_machine_arn = self._create_step_function(stepfunctions_client, iam_client)
        
        # Start multiple executions
        for i in range(3):
            input_data = {
                'image_key': f'test-image-{i}.jpg',
                'bucket_name': bucket_name
            }
            
            stepfunctions_client.start_execution(
                stateMachineArn=state_machine_arn,
                name=f'test-execution-{i}',
                input=json.dumps(input_data)
            )
        
        # List executions
        response = stepfunctions_client.list_executions(
            stateMachineArn=state_machine_arn
        )
        
        executions = response['executions']
        assert len(executions) == 3
        
        # Verify execution names
        execution_names = [exec['name'] for exec in executions]
        assert 'test-execution-0' in execution_names
        assert 'test-execution-1' in execution_names
        assert 'test-execution-2' in execution_names
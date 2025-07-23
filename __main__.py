"""
Image Discerner - Serverless image analysis service
"""
import pulumi
import pulumi_aws as aws
import pulumi_gcp as gcp
import json

# Configuration
config = pulumi.Config()
aws_region = config.get("aws:region") or "us-west-2"

# GCP configuration
gcp_config = pulumi.Config("gcp")
gcp_project = gcp_config.require("project")
gcp_region = gcp_config.get("region") or "us-central1"

# S3 bucket for image storage
image_bucket = aws.s3.Bucket(
    "image-discerner-bucket",
    bucket=f"image-discerner-{pulumi.get_stack()}",
    versioning=aws.s3.BucketVersioningArgs(enabled=True),
    server_side_encryption_configuration=aws.s3.BucketServerSideEncryptionConfigurationArgs(
        rule=aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
            apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                sse_algorithm="AES256"
            )
        )
    )
)

# S3 bucket CORS configuration
bucket_cors = aws.s3.BucketCorsConfigurationV2(
    "image-discerner-bucket-cors",
    bucket=image_bucket.id,
    cors_rules=[
        aws.s3.BucketCorsConfigurationV2CorsRuleArgs(
            allowed_headers=["*"],
            allowed_methods=["GET", "PUT", "POST", "DELETE", "HEAD"],
            allowed_origins=[
                "http://localhost:5173",
                "https://layers-collector-svelte.vercel.app",
                "https://layers-collector-svelte-*-beaus-projects-59f320cd.vercel.app"
            ],
            expose_headers=["ETag"],
            max_age_seconds=3000
        )
    ]
)

# IAM role for Lambda functions
lambda_role = aws.iam.Role(
    "lambda-execution-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"}
        }]
    })
)

# IAM role for Step Functions
step_function_role = aws.iam.Role(
    "step-function-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {"Service": "states.amazonaws.com"}
        }]
    })
)

# Lambda basic execution policy
aws.iam.RolePolicyAttachment(
    "lambda-basic-execution",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
)

# S3 access policy for Lambda
s3_policy = aws.iam.RolePolicy(
    "lambda-s3-policy",
    role=lambda_role.id,
    policy=pulumi.Output.all(image_bucket.arn).apply(
        lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject"
                ],
                "Resource": f"{args[0]}/*"
            }, {
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket"
                ],
                "Resource": args[0]
            }, {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": "arn:aws:secretsmanager:*:*:secret:gcp-credentials-*"
            }]
        })
    )
)

# Step Functions execution policy
step_function_policy = aws.iam.RolePolicy(
    "step-function-policy",
    role=step_function_role.id,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": "*"
        }]
    })
)

# Secrets Manager for GCP credentials
gcp_credentials_secret = aws.secretsmanager.Secret(
    "gcp-credentials",
    description="GCP service account credentials for Vision API"
)

# Lambda function: Image Preprocessor
preprocess_lambda = aws.lambda_.Function(
    "image-preprocessor",
    runtime="python3.11",
    handler="preprocess.handler",
    role=lambda_role.arn,
    code=pulumi.AssetArchive({
        "preprocess.py": pulumi.FileAsset("src/lambdas/preprocess.py"),
        "./": pulumi.FileArchive("lambda_packages")
    }),
    timeout=60,
    memory_size=512
)

# Lambda function: Image Classifier
classifier_lambda = aws.lambda_.Function(
    "image-classifier",
    runtime="python3.11",
    handler="classify.handler",
    role=lambda_role.arn,
    code=pulumi.AssetArchive({
        "classify.py": pulumi.FileAsset("src/lambdas/classify.py"),
        "cv_backends/": pulumi.FileArchive("src/cv_backends"),
        "./": pulumi.FileArchive("lambda_packages")
    }),
    timeout=60,
    memory_size=256,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "CV_BACKEND": "mock",  # Fallback backend
            "CLASSIFICATION_BACKEND": "gcp_vision_rest",  # Use GCP Vision REST API for object detection
            "GCP_CREDENTIALS_SECRET_NAME": gcp_credentials_secret.name
        }
    )
)

# Lambda function: Text Extractor
text_extractor_lambda = aws.lambda_.Function(
    "text-extractor",
    runtime="python3.11",
    handler="extract_text.handler",
    role=lambda_role.arn,
    code=pulumi.AssetArchive({
        "extract_text.py": pulumi.FileAsset("src/lambdas/extract_text.py"),
        "cv_backends/": pulumi.FileArchive("src/cv_backends"),
        "./": pulumi.FileArchive("lambda_packages")
    }),
    timeout=60,
    memory_size=256,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "CV_BACKEND": "mock",  # Fallback backend
            "TEXT_EXTRACTION_BACKEND": "gcp_vision_rest",  # Use GCP Vision REST API
            "GCP_CREDENTIALS_SECRET_NAME": gcp_credentials_secret.name
        }
    )
)

# Lambda function: Result Aggregator
aggregator_lambda = aws.lambda_.Function(
    "result-aggregator",
    runtime="python3.11",
    handler="aggregate.handler",
    role=lambda_role.arn,
    code=pulumi.AssetArchive({
        "aggregate.py": pulumi.FileAsset("src/lambdas/aggregate.py"),
        "inference_engine.py": pulumi.FileAsset("src/lambdas/inference_engine.py")
    }),
    timeout=30,
    memory_size=128
)

# Step Functions state machine
step_function_definition = pulumi.Output.all(
    preprocess_lambda.arn,
    classifier_lambda.arn,
    text_extractor_lambda.arn,
    aggregator_lambda.arn
).apply(lambda arns: json.dumps({
    "Comment": "Image analysis pipeline",
    "StartAt": "PreprocessImage",
    "States": {
        "PreprocessImage": {
            "Type": "Task",
            "Resource": arns[0],
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
                            "Resource": arns[1],
                            "Parameters": {
                                "processed_image_key.$": "$.body.processed_image_key",
                                "bucket_name.$": "$.body.bucket_name",
                                "original_image_key.$": "$.body.original_image_key",
                                "image_dimensions.$": "$.body.image_dimensions"
                            },
                            "End": True
                        }
                    }
                },
                {
                    "StartAt": "ExtractText",
                    "States": {
                        "ExtractText": {
                            "Type": "Task",
                            "Resource": arns[2],
                            "Parameters": {
                                "processed_image_key.$": "$.body.processed_image_key",
                                "bucket_name.$": "$.body.bucket_name",
                                "original_image_key.$": "$.body.original_image_key",
                                "image_dimensions.$": "$.body.image_dimensions"
                            },
                            "End": True
                        }
                    }
                }
            ],
            "Next": "AggregateResults"
        },
        "AggregateResults": {
            "Type": "Task",
            "Resource": arns[3],
            "End": True
        }
    }
}))

step_function = aws.sfn.StateMachine(
    "image-analysis-pipeline",
    role_arn=step_function_role.arn,
    definition=step_function_definition
)

# API Gateway Lambda function to trigger Step Functions
api_lambda = aws.lambda_.Function(
    "api-handler",
    runtime="python3.11",
    handler="api_handler.handler",
    role=lambda_role.arn,
    code=pulumi.AssetArchive({
        "api_handler.py": pulumi.FileAsset("src/lambdas/api_handler.py")
    }),
    timeout=330,
    memory_size=128,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "STEP_FUNCTION_ARN": step_function.arn
        }
    )
)

# Add Step Functions execution permission to API Lambda
step_function_invoke_policy = aws.iam.RolePolicy(
    "api-lambda-stepfunctions-policy",
    role=lambda_role.id,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "states:StartExecution",
                "states:DescribeExecution"
            ],
            "Resource": "*"
        }]
    })
)

# API Gateway
api_gateway = aws.apigatewayv2.Api(
    "image-discerner-api",
    protocol_type="HTTP",
    cors_configuration=aws.apigatewayv2.ApiCorsConfigurationArgs(
        allow_origins=["*"],
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["content-type", "authorization"]
    )
)

# API Gateway Integration
api_integration = aws.apigatewayv2.Integration(
    "api-integration",
    api_id=api_gateway.id,
    integration_type="AWS_PROXY",
    integration_uri=api_lambda.arn,
    integration_method="POST"
)

# API Gateway Route
api_route = aws.apigatewayv2.Route(
    "analyze-route",
    api_id=api_gateway.id,
    route_key="POST /analyze",
    target=api_integration.id.apply(lambda id: f"integrations/{id}")
)

# Lambda permission for API Gateway
api_permission = aws.lambda_.Permission(
    "api-gateway-lambda-permission",
    action="lambda:InvokeFunction",
    function=api_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=api_gateway.execution_arn.apply(lambda arn: f"{arn}/*/*")
)

# API Gateway Stage (required for HTTP API to work)
api_stage = aws.apigatewayv2.Stage(
    "api-stage",
    api_id=api_gateway.id,
    name="$default",
    auto_deploy=True
)

# Cognito Identity Pool for mobile app access
identity_pool = aws.cognito.IdentityPool(
    "image-discerner-identity-pool",
    identity_pool_name="ImageDiscernerApp",
    allow_unauthenticated_identities=True,
    allow_classic_flow=False
)

# IAM role for unauthenticated users (mobile app uploads)
mobile_upload_role = aws.iam.Role(
    "mobile-upload-role",
    assume_role_policy=pulumi.Output.all(identity_pool.id).apply(
        lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Federated": "cognito-identity.amazonaws.com"
                    },
                    "Action": "sts:AssumeRoleWithWebIdentity",
                    "Condition": {
                        "StringEquals": {
                            "cognito-identity.amazonaws.com:aud": args[0]
                        },
                        "ForAnyValue:StringLike": {
                            "cognito-identity.amazonaws.com:amr": "unauthenticated"
                        }
                    }
                }
            ]
        })
    )
)

# S3 upload policy for mobile users
mobile_upload_policy = aws.iam.RolePolicy(
    "mobile-upload-policy",
    role=mobile_upload_role.id,
    policy=pulumi.Output.all(image_bucket.arn).apply(
        lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:PutObjectAcl"
                    ],
                    "Resource": f"{args[0]}/uploads/*"
                }
            ]
        })
    )
)

# Attach the role to the identity pool
identity_pool_role_attachment = aws.cognito.IdentityPoolRoleAttachment(
    "identity-pool-role-attachment",
    identity_pool_id=identity_pool.id,
    roles={
        "unauthenticated": mobile_upload_role.arn
    }
)

# Lambda function: Upload URL Generator
upload_url_lambda = aws.lambda_.Function(
    "upload-url-generator",
    runtime="python3.11",
    handler="get_upload_url.handler",
    role=lambda_role.arn,
    code=pulumi.AssetArchive({
        "get_upload_url.py": pulumi.FileAsset("src/lambdas/get_upload_url.py")
    }),
    timeout=30,
    memory_size=128
)

# API Gateway Route for upload URL endpoint
upload_url_integration = aws.apigatewayv2.Integration(
    "upload-url-integration",
    api_id=api_gateway.id,
    integration_type="AWS_PROXY",
    integration_uri=upload_url_lambda.arn,
    integration_method="POST"
)

upload_url_route = aws.apigatewayv2.Route(
    "upload-url-route",
    api_id=api_gateway.id,
    route_key="POST /upload-url",
    target=upload_url_integration.id.apply(lambda id: f"integrations/{id}")
)

# Lambda permission for API Gateway (upload URL endpoint)
upload_url_permission = aws.lambda_.Permission(
    "upload-url-lambda-permission",
    action="lambda:InvokeFunction",
    function=upload_url_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=api_gateway.execution_arn.apply(lambda arn: f"{arn}/*/*")
)

# Exports
pulumi.export("bucket_name", image_bucket.bucket)
pulumi.export("step_function_arn", step_function.arn)
pulumi.export("api_gateway_url", api_gateway.api_endpoint)
pulumi.export("upload_url_endpoint", api_gateway.api_endpoint.apply(lambda url: f"{url}/upload-url"))
pulumi.export("analyze_endpoint", api_gateway.api_endpoint.apply(lambda url: f"{url}/analyze"))
pulumi.export("cognito_identity_pool_id", identity_pool.id)
pulumi.export("preprocess_lambda_arn", preprocess_lambda.arn)
pulumi.export("classifier_lambda_arn", classifier_lambda.arn)
pulumi.export("text_extractor_lambda_arn", text_extractor_lambda.arn)
pulumi.export("aggregator_lambda_arn", aggregator_lambda.arn)
pulumi.export("upload_url_lambda_arn", upload_url_lambda.arn)
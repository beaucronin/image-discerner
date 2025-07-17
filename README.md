# Image Discerner

A serverless image analysis service that identifies commercial and industrial vehicles, infrastructure assets, and extracts key text identifiers from images. Features contextual inference engine that combines visual detection with text analysis to identify specific vehicle types and fleet information. Built with AWS Lambda, Step Functions, and GCP Vision API.

## Architecture

The service uses a Step Functions workflow to orchestrate image processing:

1. **Preprocess** - Resize and optimize images for CV APIs
2. **Parallel Analysis** - Simultaneously run:
   - **Classification** - Identify vehicles, containers, infrastructure 
   - **Text Extraction** - Extract fleet numbers, container IDs, license plates
3. **Aggregation** - Combine results with contextual inference engine

### Tech Stack

- **AWS Lambda** - Serverless compute for each pipeline stage
- **AWS Step Functions** - Workflow orchestration with parallel processing
- **AWS S3** - Image storage with versioning
- **GCP Vision API** - Computer vision and OCR (pluggable backend)
- **Pulumi** - Infrastructure as code with Python
- **pytest + moto** - Comprehensive testing with AWS service mocking

## Quick Start

### Prerequisites

- Python 3.11+
- AWS CLI configured
- Pulumi CLI installed
- GCP project with Vision API enabled (for production)

### Development Setup

```bash
# Clone and setup
git clone https://github.com/beaucronin/image-discerner.git
cd image-discerner

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
make dev-setup

# Run tests
make test
```

### Configuration

Before deploying, configure Pulumi:

```bash
# Required: Set your GCP project ID
pulumi config set gcp:project YOUR_GCP_PROJECT_ID

# Optional: Change regions (defaults shown)
pulumi config set aws:region us-west-2
pulumi config set gcp:region us-central1
```

### Deployment

```bash
# Deploy infrastructure
make deploy

# View deployed resources
pulumi stack output
```

## Development

### Testing

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests  
make test-integration

# Code quality checks
make lint
make format
```

### CV Backend Configuration

The service uses a multi-backend system with task-specific configuration:

```bash
# Task-specific backends (recommended)
export CLASSIFICATION_BACKEND=gcp_vision_rest    # Object detection
export TEXT_EXTRACTION_BACKEND=gcp_vision_rest   # OCR and text extraction

# Legacy single backend (fallback)
export CV_BACKEND=mock                            # Development/testing default

# Available backends: mock, gcp_vision_rest
```

### Project Structure

```
src/
├── cv_backends/              # Pluggable computer vision backends
│   ├── mock_backend.py       # Development/testing backend
│   ├── gcp_rest_backend.py   # GCP Vision REST API implementation
│   ├── gcp_backend.py        # GCP Vision gRPC (deprecated)
│   └── factory.py            # Multi-backend selection logic
└── lambdas/                  # AWS Lambda functions
    ├── preprocess.py         # Image preprocessing
    ├── classify.py           # Object classification
    ├── extract_text.py       # OCR and text parsing
    ├── aggregate.py          # Result combination + contextual inference
    ├── inference_engine.py   # Vehicle type pattern matching
    ├── api_handler.py        # Step Functions API gateway integration
    └── get_upload_url.py     # Pre-signed URL generation for mobile uploads

tests/
├── unit/                 # Unit tests for individual components
└── integration/          # End-to-end workflow tests
```

## Key Features

### Contextual Inference Engine
The service includes an intelligent inference system that combines visual object detection with text analysis to identify specific vehicle types:

- **Postal Delivery**: Detects USPS vehicles using "usps.com" text + 7-digit fleet numbers
- **Commercial Delivery**: Identifies FedEx, UPS, Amazon vehicles with branding patterns
- **Shipping Containers**: ISO container ID recognition (4 letters + 6 digits + 1 digit)  
- **Emergency Vehicles**: Police, fire, ambulance identification

**Example Output**:
```json
{
  "entities": [
    {
      "type": "commercial_vehicle:van",
      "operator": "USPS",
      "identifiers": [
        "fleet:8424021",
        "license_plate:unknown:ABC123"
      ],
      "confidence": 0.87,
      "properties": {}
    }
  ]
}
```

## API Usage

The service provides **synchronous HTTP APIs** for both analysis and secure mobile uploads.

### Analysis API
**Endpoint**: `POST https://pcgwxp6v9a.execute-api.us-west-2.amazonaws.com/analyze`

**Input Format**:
```json
{
  "image_key": "images/truck-photo.jpg", 
  "bucket_name": "image-discerner-dev"
}
```

### Mobile Upload API
**Endpoint**: `POST https://pcgwxp6v9a.execute-api.us-west-2.amazonaws.com/upload-url`

Generates secure, time-limited pre-signed URLs for direct S3 uploads from mobile apps without exposing AWS credentials.

**Input Format**:
```json
{
  "file_extension": "jpg"
}
```

**Response**:
```json
{
  "upload_url": "https://s3-presigned-url...",
  "image_key": "uploads/20250715-123456-abc123.jpg",
  "bucket_name": "image-discerner-dev",
  "expires_in": 900,
  "content_type": "image/jpg"
}
```

**Supported File Types**: jpg, jpeg, png, heic, heif

### Output Format

```json
{
  "success": true,
  "execution_arn": "arn:aws:states:us-west-2:584058910789:execution:...",
  "execution_name": "analysis-20250717-185556", 
  "analysis_result": {
    "statusCode": 200,
    "body": {
      "analysis_complete": true,
      "timestamp": "2025-07-17T18:55:57.806492+00:00",
      
      "entities": [
        {
          "type": "commercial_vehicle:van",
          "operator": "USPS",
          "identifiers": [
            "fleet:8424021",
            "license_plate:unknown:ABC123"
          ],
          "confidence": 0.87,
          "properties": {}
        }
      ],
      
      "processing_metadata": {
        "total_processing_time_ms": 8000,
        "response_format_version": "3.0"
      }
    }
  },
  "processing_time_seconds": 8
}
```

## Supported Identifiers

The service recognizes and extracts structured identifiers:

- **fleet:ID** - Vehicle fleet identifiers (e.g., `fleet:8424021`)
- **license_plate:jurisdiction:number** - License plates with jurisdiction (e.g., `license_plate:california:ABC123`)
- **container_id:ISO_ID** - Standard shipping container format (e.g., `container_id:MSKU1234567`)
- **tail_id:ID** - Aircraft tail numbers (e.g., `tail_id:N123AB`)
- **other_id:ID** - Other identification numbers

**Operators Automatically Detected**: UPS, FedEx, USPS, Amazon, DHL, Maersk, Evergreen, COSCO, MSC, Police, Fire, Ambulance

## Security

- **Mobile App Security**: Cognito Identity Pools provide temporary AWS credentials
- **Pre-signed URLs**: Time-limited (15 minutes) upload access with no permanent credentials
- **GCP Credentials**: Service account credentials stored in AWS Secrets Manager
- **S3 Encryption**: Buckets encrypted with AES256
- **IAM Policies**: Least privilege principle with scoped S3 access (uploads/* prefix only)
- **No Secrets**: No credentials committed to repository

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run the test suite: `make test`
5. Check code quality: `make lint`
6. Commit and push changes
7. Create a pull request

### Development Guidelines

- Write tests for new functionality
- Follow existing code patterns and conventions
- Update documentation for API changes
- Ensure all tests pass before submitting PRs

## Deployment Status

- **Current**: Entities format v3.0 with target definitions compliance
- **Features**: Multi-entity detection, structured identifiers, contextual inference engine, mobile upload infrastructure
- **Infrastructure**: Step Functions + Lambda architecture with Cognito Identity Pools
- **Next**: Aircraft detection, jurisdiction-specific license plate recognition, properties metadata

## Cost Considerations

- **AWS Lambda** - Pay per invocation (typically $0.20 per 1M requests)
- **Step Functions** - $0.025 per 1K state transitions
- **S3 Storage** - ~$0.023/GB/month
- **GCP Vision API** - $1.50 per 1K images for object detection + OCR

## Support

- Check existing [GitHub Issues](https://github.com/beaucronin/image-discerner/issues)
- Review the [CLAUDE.md](./CLAUDE.md) file for development context
- Run `make help` for available commands
# Image Discerner

A serverless image analysis service that identifies commercial and industrial vehicles, infrastructure assets, and extracts key text identifiers from images. Built with AWS Lambda, Step Functions, and GCP Vision API.

## Architecture

The service uses a Step Functions workflow to orchestrate image processing:

1. **Preprocess** - Resize and optimize images for CV APIs
2. **Parallel Analysis** - Simultaneously run:
   - **Classification** - Identify vehicles, containers, infrastructure 
   - **Text Extraction** - Extract fleet numbers, container IDs, license plates
3. **Aggregation** - Combine results and enhance with business logic

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

### CV Backend Switching

The service uses a pluggable CV backend system:

```bash
# Use mock backend for development/testing (default)
export CV_BACKEND=mock

# Use GCP Vision API for production
export CV_BACKEND=gcp
```

### Project Structure

```
src/
├── cv_backends/          # Pluggable computer vision backends
│   ├── mock_backend.py   # Development/testing backend
│   ├── gcp_backend.py    # GCP Vision API implementation
│   └── factory.py        # Backend selection logic
└── lambdas/              # AWS Lambda functions
    ├── preprocess.py     # Image preprocessing
    ├── classify.py       # Object classification
    ├── extract_text.py   # OCR and text parsing
    └── aggregate.py      # Result combination

tests/
├── unit/                 # Unit tests for individual components
└── integration/          # End-to-end workflow tests
```

## API Usage

The service processes images through S3 and Step Functions:

### Input Format

```json
{
  "image_key": "images/truck-photo.jpg",
  "bucket_name": "image-discerner-bucket"
}
```

### Output Format

```json
{
  "analysis_complete": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "image_classification": {
    "detected_items": [
      {
        "category": "vehicle",
        "subcategory": "truck", 
        "confidence": 0.92,
        "brand": "UPS",
        "fleet_numbers": ["12345"]
      }
    ]
  },
  "text_analysis": {
    "extracted_text": "UPS FLEET 12345",
    "structured_identifiers": {
      "container_ids": [],
      "fleet_numbers": ["12345"],
      "license_plates": []
    }
  },
  "confidence_score": 0.89
}
```

## Supported Identifiers

The service recognizes and extracts:

- **Container IDs** - Standard shipping container format (4 letters + 6-7 digits)
- **Fleet Numbers** - Vehicle fleet identifiers 
- **License Plates** - Various US license plate formats
- **Commercial Brands** - UPS, FedEx, etc. (visual classification)

## Security

- GCP service account credentials stored in AWS Secrets Manager
- S3 buckets encrypted with AES256
- IAM roles follow least privilege principle
- No secrets or keys committed to repository

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

## Deployment Environments

- **Development** - Use mock CV backend for fast iteration
- **Staging** - Deploy with GCP Vision API for realistic testing  
- **Production** - Full deployment with monitoring and error handling

## Cost Considerations

- **AWS Lambda** - Pay per invocation (typically $0.20 per 1M requests)
- **Step Functions** - $0.025 per 1K state transitions
- **S3 Storage** - ~$0.023/GB/month
- **GCP Vision API** - $1.50 per 1K images for object detection + OCR

## Support

- Check existing [GitHub Issues](https://github.com/beaucronin/image-discerner/issues)
- Review the [CLAUDE.md](./CLAUDE.md) file for development context
- Run `make help` for available commands
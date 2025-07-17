# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Image Discerner is a serverless image analysis service that identifies commercial/industrial vehicles, infrastructure assets, and extracts key text identifiers from images. Uses AWS for orchestration and GCP Vision API for computer vision. Features contextual inference engine that combines visual detection with text analysis to identify specific vehicle types and fleet information.

## Architecture

- **AWS Step Functions** orchestrate the pipeline: Preprocess → Parallel (Classify + Extract Text) → Aggregate → Inference
- **Lambda Functions**: 5 separate functions for each pipeline stage including contextual inference
- **Storage**: S3 for image storage with versioning
- **APIs**: Pluggable CV backend design (GCP Vision REST API integrated)
- **Inference Engine**: Pattern-based contextual analysis combining visual + text evidence
- **Infrastructure**: Pulumi with Python for multi-cloud deployment

## Development Commands

**Working deployment command**: `pulumi up` (confirmed working from Makefile)

## Recent Changes (Session 2025-07-17)

**Status**: Major API upgrade to entities format completed and deployed successfully

**MAJOR UPGRADE: Entities Format (v3.0) - Target Definitions Implementation**:
1. **Multi-Entity Support** - API now returns array of entities instead of single primary subject
2. **Structured Identifiers** - Implemented `type:jurisdiction:number` format for all identifiers
3. **Enhanced Type System** - Using colon syntax for categories: `commercial_vehicle:van`
4. **Target Definitions Compliance** - Full alignment with `docs/target-definitions.md` specifications
5. **Clean Architecture** - Simplified response format focused on entities only

**API Response Format (v3.0)**:
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
      "confidence": 0.85,
      "properties": {}
    }
  ],
  "processing_metadata": {
    "response_format_version": "3.0"
  }
}
```

**Technical Implementation (v3.0)**:
- **Multi-entity detection**: Ready for images with multiple commercial vehicles/containers
- **Structured identifiers**: `fleet:ID`, `license_plate:jurisdiction:number`, `container_id:ISO_ID`
- **Enhanced categorization**: Colon syntax supports extensible taxonomy
- **Operator detection**: Automatic recognition of UPS, FedEx, USPS, Amazon, shipping lines, etc.
- **Properties framework**: Ready for entity-specific metadata (size codes, ratings, etc.)
- **Clean API**: Simplified response structure focused on entities

**Test Results**:
- Successfully deployed and tested with mock USPS vehicle data
- Correctly generates entities with structured identifiers
- Response processing time: ~5 seconds
- All Lambda functions operating without errors
- Clean API structure validated

```bash
# Setup development environment
make dev-setup

# Run tests
make test              # All tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only

# Code quality
make lint              # Run linting checks
make format            # Format code

# Infrastructure
make deploy            # Deploy with Pulumi
make destroy           # Destroy infrastructure

# Install dependencies manually
pip install -r requirements.txt      # Production deps
pip install -r requirements-dev.txt  # Development deps
```

## Save Progress Workflow

Claude Code supports an intelligent "save progress" workflow that automatically:

1. **Runs tests** and analyzes results for any failures or issues
2. **Updates documentation** (CLAUDE.md, README.md) based on current project state and recent changes
3. **Generates meaningful commit messages** that accurately describe what changed
4. **Commits and pushes** changes with proper error handling

### Usage
Simply say **"save progress"** to trigger this workflow.

### What it does intelligently:
- Analyzes current project state and recent modifications
- Updates documentation to reflect new features, architecture changes, or status updates
- Handles test failures and provides actionable feedback
- Creates contextual commit messages based on actual changes made
- Manages git operations including conflict resolution

This workflow preserves development momentum by automatically capturing and documenting progress without manual overhead.

## Configuration Required

Before deployment, set these Pulumi config values:
```bash
pulumi config set gcp:project YOUR_GCP_PROJECT_ID
pulumi config set aws:region us-west-2  # optional, defaults shown
pulumi config set gcp:region us-central1  # optional
```

## Lambda Function Structure

Current implementation status:
- `image-preprocessor`: ✅ HTTP response format, error handling improved
- `image-classifier`: ✅ GCP Vision REST API integrated, multi-backend support  
- `text-extractor`: ✅ GCP Vision REST API integrated, multi-backend support
- `result-aggregator`: ✅ Contextual inference engine with vehicle pattern matching
- `api-handler`: ✅ Synchronous API endpoint working
- `inference-engine`: ✅ Pattern-based vehicle type identification system
- `upload-url-generator`: ✅ Secure pre-signed URL generation for mobile uploads

## API Endpoints

**Analysis API**: https://pcgwxp6v9a.execute-api.us-west-2.amazonaws.com/analyze
**Upload URL API**: https://pcgwxp6v9a.execute-api.us-west-2.amazonaws.com/upload-url

The service provides both synchronous image analysis and secure mobile upload capabilities. Analysis integrates with GCP Vision API for real computer vision and includes contextual inference to identify vehicle types and fleet information.

## Mobile App Integration

**Cognito Identity Pool ID**: us-west-2:3fdc01e7-9f4c-486f-8566-ddbc27e73e22

The service supports secure iOS/Android app integration through:
- AWS Cognito Identity Pools for temporary credentials
- Pre-signed S3 upload URLs (15-minute expiry)
- Scoped IAM permissions (uploads/* prefix only)
- Complete Swift integration guide available in `docs/ios-integration.md`

## Security Notes

- GCP service account credentials stored in AWS Secrets Manager
- S3 bucket encrypted with AES256
- IAM roles follow least privilege principle

## Pulumi Deployment Notes

- Standard Pulumi deployment command includes:
  - Activating virtual environment
  - Setting Pulumi binary path
  - Setting Pulumi config passphrase
  - Running deployment with auto-approval
```bash
source venv/bin/activate && export PATH=$PATH:/Users/beau/.pulumi/bin && export PULUMI_CONFIG_PASSPHRASE=test123 && pulumi up --yes
```

## CV Backend Configuration

The service supports multiple backend configurations for different tasks:

### Single Backend (Legacy)
```bash
# Use same backend for all tasks
export CV_BACKEND=mock  # or gcp
```

### Multi-Backend (Recommended) 
```bash
# Task-specific backends
export CLASSIFICATION_BACKEND=mock        # Object detection: mock, gcp_vision, gcp_automl
export TEXT_EXTRACTION_BACKEND=mock      # OCR: mock, gcp_vision, gcp_document_ai
export CV_BACKEND=mock                   # Fallback for unspecified tasks
```

### Available Backend Options
- **mock**: Mock backend with realistic fake data
- **gcp_vision_rest**: GCP Vision API REST (general object detection + OCR) ✅ IMPLEMENTED
- **gcp_vision**: GCP Vision API gRPC (general object detection + OCR) - Deprecated due to Lambda compatibility
- **gcp_automl**: GCP AutoML Vision (custom object detection) - TODO
- **gcp_document_ai**: GCP Document AI (advanced OCR) - TODO

## Contextual Inference Engine

The service includes an inference engine that combines visual object detection with text analysis to identify specific vehicle types:

### Supported Vehicle Patterns
- **Postal Delivery**: Detects USPS vehicles using visual detection + "usps.com" text + 7-digit fleet numbers
- **Commercial Delivery**: Identifies FedEx, UPS, Amazon vehicles 
- **Shipping Containers**: ISO container ID detection
- **Emergency Vehicles**: Police, fire, ambulance identification

### Example Results
```json
{
  "contextual_inferences": [
    {
      "vehicle_type": "postal_delivery",
      "confidence": 0.87,
      "description": "Postal delivery vehicle with fleet ID 8424021",
      "fleet_identifiers": ["8424021"],
      "evidence": ["detected_car", "text_pattern_usps\\.com", "text_pattern_\\d{7}"]
    }
  ]
}
```

## API Backward Compatibility

- We don't need to maintain backward compatibility in the api until informed otherwise
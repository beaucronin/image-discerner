# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Image Discerner is a serverless image analysis service that identifies commercial/industrial vehicles, infrastructure assets, and extracts key text identifiers from images. Uses AWS for orchestration and GCP Vision API for computer vision.

## Architecture

- **AWS Step Functions** orchestrate the pipeline: Preprocess → Parallel (Classify + Extract Text) → Aggregate
- **Lambda Functions**: 4 separate functions for each pipeline stage
- **Storage**: S3 for image storage with versioning
- **APIs**: Pluggable CV backend design (starting with GCP Vision API)
- **Infrastructure**: Pulumi with Python for multi-cloud deployment

## Development Commands

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

## Configuration Required

Before deployment, set these Pulumi config values:
```bash
pulumi config set gcp:project YOUR_GCP_PROJECT_ID
pulumi config set aws:region us-east-1  # optional, defaults shown
pulumi config set gcp:region us-central1  # optional
```

## Lambda Function Structure

Each Lambda has placeholder implementation that needs completion:
- `image-preprocessor`: Resize/optimize images for CV APIs
- `image-classifier`: GCP Vision API classification 
- `text-extractor`: OCR and structured ID parsing
- `result-aggregator`: Combine and format final response

## Security Notes

- GCP service account credentials stored in AWS Secrets Manager
- S3 bucket encrypted with AES256
- IAM roles follow least privilege principle
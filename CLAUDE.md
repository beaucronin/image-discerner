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
pulumi config set aws:region us-west-2  # optional, defaults shown
pulumi config set gcp:region us-central1  # optional
```

## Lambda Function Structure

Current implementation status:
- `image-preprocessor`: ✅ Basic data flow (no actual image processing yet)
- `image-classifier`: ✅ Mock backend working, GCP integration pending
- `text-extractor`: ✅ Mock backend working, GCP integration pending  
- `result-aggregator`: ✅ Functional result combination and formatting
- `api-handler`: ✅ Synchronous API endpoint working

## Current API Endpoint

**Production URL**: https://pcgwxp6v9a.execute-api.us-west-2.amazonaws.com/analyze

The API currently returns mock data from the CV backends. Real computer vision integration pending.

## Security Notes

- GCP service account credentials stored in AWS Secrets Manager
- S3 bucket encrypted with AES256
- IAM roles follow least privilege principle

## AWS Access

- Remember that this is how we access aws

## Pulumi Deployment Notes

- Standard Pulumi deployment command includes:
  - Activating virtual environment
  - Setting Pulumi binary path
  - Setting Pulumi config passphrase
  - Running deployment with auto-approval
```bash
source venv/bin/activate && export PATH=$PATH:/Users/beau/.pulumi/bin && export PULUMI_CONFIG_PASSPHRASE=test123 && pulumi up --yes
```
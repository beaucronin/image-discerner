# Image Discerner API Reference

## Overview

The Image Discerner API provides intelligent image analysis for commercial vehicles, infrastructure assets, and cargo containers. It returns structured information about the primary subject identified in uploaded images.

## API Endpoints

### Base URL
```
https://pcgwxp6v9a.execute-api.us-west-2.amazonaws.com
```

### Authentication
The API uses AWS Cognito Identity Pools for secure, temporary credentials. No permanent API keys required.

---

## Upload URL Endpoint

### `POST /upload-url`

Generate a secure, time-limited URL for direct S3 image uploads.

#### Request Body
```json
{
  "file_extension": "jpg"
}
```

#### Response
```json
{
  "upload_url": "https://...",
  "image_key": "uploads/20250715-123456-abc123.jpg",
  "bucket_name": "image-discerner-dev",
  "expires_in": 900,
  "content_type": "image/jpg"
}
```

---

## Analysis Endpoint

### `POST /analyze`

Analyze an uploaded image and return structured information about the primary subject.

#### Request Body
```json
{
  "image_key": "uploads/20250715-123456-abc123.jpg",
  "bucket_name": "image-discerner-dev"
}
```

#### Response Format (Version 2.0)

The API returns a structured summary of the primary subject, with detailed analysis available for advanced use cases.

```json
{
  "analysis_complete": true,
  "timestamp": "2025-07-15T18:25:19.725642+00:00",
  
  "primary_subject": {
    "category": "commercial_vehicle",
    "subcategory": "delivery_van",
    "operator": "UPS",
    "fleet_id": "1Z2345",
    "confidence": 0.87,
    "additional_details": {
      "license_plate": "ABC123",
      "text_identifiers": ["1Z2345", "UPS"],
      "description": "UPS delivery vehicle with fleet ID 1Z2345"
    }
  },
  
  "detailed_analysis": {
    "image_classification": { ... },
    "text_analysis": { ... },
    "contextual_inferences": [ ... ],
    "confidence_score": 0.87
  },
  
  "processing_metadata": {
    "total_processing_time_ms": 8000,
    "classification_provider": "gcp_vision_rest",
    "text_provider": "gcp_vision_rest",
    "image_key": "processed/uploads/20250715-123456-abc123.jpg",
    "response_format_version": "2.0"
  }
}
```

---

## Primary Subject Structure

### Categories and Subcategories

#### Commercial Vehicle
- `delivery_van` - Package delivery vehicles (UPS, FedEx, Amazon)
- `postal_van` - Mail delivery vehicles (USPS)
- `service_truck` - Utility and service vehicles
- `cargo_truck` - Large freight vehicles

#### Emergency Vehicle  
- `emergency_response` - Police, fire, ambulance vehicles

#### Cargo Container
- `shipping_container` - ISO shipping containers
- `storage_container` - Temporary storage units

#### Infrastructure
- `building` - Commercial/industrial buildings
- `warehouse` - Storage facilities
- `loading_dock` - Cargo loading areas

#### Other
- `unknown` - Unidentified subjects
- `person` - Human subjects
- `street_scene` - General street/traffic scenes

### Operators

Common operators automatically identified:
- **Delivery**: UPS, FedEx, Amazon, DHL
- **Postal**: USPS
- **Shipping**: Maersk, Evergreen, COSCO, MSC
- **Emergency**: Police, Fire, Ambulance

### Fleet Identifiers

The API extracts various fleet identification patterns:
- **7-digit numbers** (common for USPS: `8424021`)
- **Container IDs** (ISO format: `MSKU1234567`)
- **License plates** (various state formats)
- **Company tracking numbers**

---

## Example Responses

### UPS Delivery Truck
```json
{
  "primary_subject": {
    "category": "commercial_vehicle",
    "subcategory": "delivery_van",
    "operator": "UPS",
    "fleet_id": "1Z2345",
    "confidence": 0.91,
    "additional_details": {
      "license_plate": "BRN123",
      "text_identifiers": ["1Z2345", "UPS"],
      "description": "UPS delivery vehicle with fleet ID 1Z2345"
    }
  }
}
```

### USPS Mail Truck
```json
{
  "primary_subject": {
    "category": "commercial_vehicle", 
    "subcategory": "postal_van",
    "operator": "USPS",
    "fleet_id": "8424021",
    "confidence": 0.87,
    "additional_details": {
      "license_plate": null,
      "text_identifiers": ["8424021", "usps.com"],
      "description": "Postal delivery vehicle with fleet ID 8424021"
    }
  }
}
```

### Shipping Container
```json
{
  "primary_subject": {
    "category": "cargo_container",
    "subcategory": "shipping_container", 
    "operator": "Maersk",
    "fleet_id": "MSKU1234567",
    "confidence": 0.94,
    "additional_details": {
      "license_plate": null,
      "text_identifiers": ["MSKU1234567"],
      "description": "Maersk shipping container MSKU1234567"
    }
  }
}
```

### Unknown Subject
```json
{
  "primary_subject": {
    "category": "unknown",
    "subcategory": "unidentified",
    "operator": null,
    "fleet_id": null,
    "confidence": 0.0,
    "additional_details": {
      "license_plate": null,
      "text_identifiers": [],
      "description": "Unable to identify primary subject"
    }
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "error": "Missing required parameters: image_key, bucket_name"
}
```

### 404 Not Found
```json
{
  "success": false,
  "error": "Image not found in specified bucket"
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Step Functions execution failed",
  "execution_arn": "arn:aws:states:...",
  "cause": "..."
}
```

---

## Confidence Scoring

Confidence scores range from 0.0 to 1.0:
- **0.9-1.0**: Very high confidence (strong visual + text evidence)
- **0.7-0.89**: High confidence (good visual evidence + some text)
- **0.5-0.69**: Medium confidence (visual evidence, limited text)
- **0.3-0.49**: Low confidence (weak evidence)
- **0.0-0.29**: Very low confidence (insufficient evidence)

---

## Rate Limits

- **Upload URL**: 100 requests/minute
- **Analysis**: 50 requests/minute  
- **Processing time**: ~8 seconds average

---

## Integration Notes

1. **Upload Flow**: Get upload URL → Upload image → Analyze image
2. **Image formats**: JPEG, PNG supported
3. **Image size**: Up to 10MB recommended
4. **Retention**: Images stored for 30 days
5. **Security**: All uploads encrypted with AES256

For mobile app integration examples, see [iOS Integration Guide](ios-integration.md).
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

#### Response Format (Version 3.0)

The API returns an array of entities found in the image.

```json
{
  "analysis_complete": true,
  "timestamp": "2025-07-17T18:45:19.725642+00:00",
  
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
    "total_processing_time_ms": 8000,
    "classification_provider": "gcp_vision_rest",
    "text_provider": "gcp_vision_rest",
    "image_key": "processed/uploads/20250715-123456-abc123.jpg",
    "response_format_version": "3.0"
  }
}
```

---

## Entities Structure (Version 3.0)

The new entities format provides a more structured approach to identifying multiple objects in images.

### Entity Format

```json
{
  "type": "commercial_vehicle:van",
  "operator": "USPS",
  "identifiers": [
    "fleet:8424021",
    "license_plate:california:ABC123"
  ],
  "confidence": 0.85,
  "properties": {}
}
```

### Entity Types

Uses colon syntax for hierarchical categorization:

- **commercial_vehicle:van** - Delivery and service vans
- **commercial_vehicle:step_van** - Step vans for delivery
- **commercial_vehicle:panel_truck** - Panel trucks
- **commercial_vehicle:tractor_trailer** - Large freight vehicles
- **commercial_vehicle:propeller_aircraft** - Propeller aircraft
- **commercial_vehicle:jet_aircraft** - Jet aircraft
- **cargo_container** - Shipping containers
- **emergency_vehicle:response** - Police, fire, ambulance vehicles

### Structured Identifiers

All identifiers use a structured format:

- **fleet:ID** - Fleet identification numbers (e.g., `fleet:8424021`)
- **license_plate:jurisdiction:number** - License plates (e.g., `license_plate:california:ABC123`)
- **container_id:ISO_ID** - Container identifiers (e.g., `container_id:MSKU1234567`)
- **tail_id:ID** - Aircraft tail numbers (e.g., `tail_id:N123AB`)
- **other_id:ID** - Other identification numbers

### Properties

Entity-specific metadata (extensible for future use):

```json
{
  "properties": {
    "size_code": "45G1",
    "rating_kva": 50
  }
}
```


---

## Example Responses

### UPS Delivery Truck
```json
{
  "entities": [
    {
      "type": "commercial_vehicle:van",
      "operator": "UPS",
      "identifiers": [
        "fleet:1Z2345",
        "license_plate:unknown:BRN123"
      ],
      "confidence": 0.91,
      "properties": {}
    }
  ]
}
```

### USPS Mail Truck
```json
{
  "entities": [
    {
      "type": "commercial_vehicle:van",
      "operator": "USPS",
      "identifiers": [
        "fleet:8424021"
      ],
      "confidence": 0.87,
      "properties": {}
    }
  ]
}
```

### Shipping Container
```json
{
  "entities": [
    {
      "type": "cargo_container",
      "operator": "Maersk",
      "identifiers": [
        "container_id:MSKU1234567"
      ],
      "confidence": 0.94,
      "properties": {
        "size_code": "45G1"
      }
    }
  ]
}
```

### Multiple Entities Example
```json
{
  "entities": [
    {
      "type": "commercial_vehicle:tractor_trailer",
      "operator": "FedEx",
      "identifiers": [
        "fleet:FX1234",
        "license_plate:california:ABC123"
      ],
      "confidence": 0.89,
      "properties": {}
    },
    {
      "type": "cargo_container",
      "operator": "MSC",
      "identifiers": [
        "container_id:MSCU7654321"
      ],
      "confidence": 0.92,
      "properties": {
        "size_code": "20G1"
      }
    }
  ]
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
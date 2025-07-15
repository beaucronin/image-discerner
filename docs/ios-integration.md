# iOS App Integration Guide

This guide shows how to integrate your iOS app with the Image Discerner service for secure image uploads and analysis.

## Overview

The service provides a secure upload flow using AWS Cognito Identity Pools and pre-signed URLs:

1. **Get Upload URL** - Request a secure, time-limited upload URL
2. **Upload Image** - Upload directly to S3 using the pre-signed URL  
3. **Analyze Image** - Request analysis of the uploaded image
4. **Get Results** - Receive vehicle identification and contextual insights

## Configuration

### Service Endpoints
```swift
let uploadURLEndpoint = "https://pcgwxp6v9a.execute-api.us-west-2.amazonaws.com/upload-url"
let analyzeEndpoint = "https://pcgwxp6v9a.execute-api.us-west-2.amazonaws.com/analyze"
```

### Cognito Identity Pool
```swift
let cognitoIdentityPoolId = "us-west-2:3fdc01e7-9f4c-486f-8566-ddbc27e73e22"
let region = AWSRegionType.USWest2
```

## Implementation

### 1. Swift Models (Version 2.0)

#### Upload URL Models
```swift
struct UploadURLResponse: Codable {
    let uploadURL: String
    let imageKey: String
    let bucketName: String
    let expiresIn: Int
    let contentType: String
    
    enum CodingKeys: String, CodingKey {
        case uploadURL = "upload_url"
        case imageKey = "image_key"
        case bucketName = "bucket_name"
        case expiresIn = "expires_in"
        case contentType = "content_type"
    }
}
```

#### Analysis Request/Response Models
```swift
struct AnalysisRequest: Codable {
    let imageKey: String
    let bucketName: String
    
    enum CodingKeys: String, CodingKey {
        case imageKey = "image_key"
        case bucketName = "bucket_name"
    }
}

struct AnalysisResult: Codable {
    let success: Bool
    let analysisResult: AnalysisData
    
    enum CodingKeys: String, CodingKey {
        case success
        case analysisResult = "analysis_result"
    }
}

struct AnalysisData: Codable {
    let statusCode: Int
    let body: AnalysisResponse
}

// NEW: Simplified response structure focused on primary subject
struct AnalysisResponse: Codable {
    let analysisComplete: Bool
    let timestamp: String
    let primarySubject: PrimarySubject
    let processingMetadata: ProcessingMetadata
    
    enum CodingKeys: String, CodingKey {
        case analysisComplete = "analysis_complete"
        case timestamp
        case primarySubject = "primary_subject"
        case processingMetadata = "processing_metadata"
    }
}

struct PrimarySubject: Codable {
    let category: String
    let subcategory: String
    let operator: String?
    let fleetId: String?
    let confidence: Double
    let additionalDetails: AdditionalDetails
    
    enum CodingKeys: String, CodingKey {
        case category
        case subcategory
        case operator
        case fleetId = "fleet_id"
        case confidence
        case additionalDetails = "additional_details"
    }
}

struct AdditionalDetails: Codable {
    let licensePlate: String?
    let textIdentifiers: [String]
    let description: String
    
    enum CodingKeys: String, CodingKey {
        case licensePlate = "license_plate"
        case textIdentifiers = "text_identifiers"
        case description
    }
}

struct ProcessingMetadata: Codable {
    let totalProcessingTimeMs: Int
    let responseFormatVersion: String
    
    enum CodingKeys: String, CodingKey {
        case totalProcessingTimeMs = "total_processing_time_ms"
        case responseFormatVersion = "response_format_version"
}
```

### 2. Image Analysis Service

```swift
import Foundation
import UIKit

class ImageAnalysisService {
    private let uploadURLEndpoint = "https://pcgwxp6v9a.execute-api.us-west-2.amazonaws.com/upload-url"
    private let analyzeEndpoint = "https://pcgwxp6v9a.execute-api.us-west-2.amazonaws.com/analyze"
    
    func analyzeImage(_ image: UIImage) async throws -> AnalysisResult {
        // Step 1: Get upload URL
        let uploadResponse = try await getUploadURL(fileExtension: "jpg")
        
        // Step 2: Upload image
        guard let imageData = image.jpegData(compressionQuality: 0.8) else {
            throw ImageAnalysisError.imageConversionFailed
        }
        
        try await uploadImage(imageData, to: uploadResponse.uploadURL, contentType: uploadResponse.contentType)
        
        // Step 3: Analyze uploaded image
        let analysisResult = try await analyzeUploadedImage(
            imageKey: uploadResponse.imageKey,
            bucketName: uploadResponse.bucketName
        )
        
        return analysisResult
    }
    
    private func getUploadURL(fileExtension: String) async throws -> UploadURLResponse {
        let url = URL(string: uploadURLEndpoint)!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let requestBody = ["file_extension": fileExtension]
        request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw ImageAnalysisError.uploadURLRequestFailed
        }
        
        return try JSONDecoder().decode(UploadURLResponse.self, from: data)
    }
    
    private func uploadImage(_ imageData: Data, to uploadURL: String, contentType: String) async throws {
        let url = URL(string: uploadURL)!
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        request.httpBody = imageData
        
        let (_, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw ImageAnalysisError.imageUploadFailed
        }
    }
    
    private func analyzeUploadedImage(imageKey: String, bucketName: String) async throws -> AnalysisResult {
        let url = URL(string: analyzeEndpoint)!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let requestBody = AnalysisRequest(imageKey: imageKey, bucketName: bucketName)
        request.httpBody = try JSONEncoder().encode(requestBody)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw ImageAnalysisError.analysisRequestFailed
        }
        
        return try JSONDecoder().decode(AnalysisResult.self, from: data)
    }
}

enum ImageAnalysisError: Error {
    case imageConversionFailed
    case uploadURLRequestFailed
    case imageUploadFailed
    case analysisRequestFailed
}
```

### 3. Usage Example

```swift
import SwiftUI

struct ContentView: View {
    @State private var selectedImage: UIImage?
    @State private var analysisResult: AnalysisResult?
    @State private var isLoading = false
    @State private var showImagePicker = false
    
    private let imageAnalysisService = ImageAnalysisService()
    
    var body: some View {
        VStack(spacing: 20) {
            if let image = selectedImage {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFit()
                    .frame(maxHeight: 300)
            }
            
            Button("Select Image") {
                showImagePicker = true
            }
            
            if let image = selectedImage {
                Button("Analyze Image") {
                    analyzeImage(image)
                }
                .disabled(isLoading)
            }
            
            if isLoading {
                ProgressView("Analyzing...")
            }
            
            if let result = analysisResult {
                AnalysisResultView(result: result)
            }
        }
        .padding()
        .sheet(isPresented: $showImagePicker) {
            ImagePicker(image: $selectedImage)
        }
    }
    
    private func analyzeImage(_ image: UIImage) {
        isLoading = true
        
        Task {
            do {
                let result = try await imageAnalysisService.analyzeImage(image)
                
                await MainActor.run {
                    self.analysisResult = result
                    self.isLoading = false
                }
            } catch {
                await MainActor.run {
                    self.isLoading = false
                    // Handle error
                    print("Analysis failed: \\(error)")
                }
            }
        }
    }
}

struct AnalysisResultView: View {
    let result: AnalysisResult
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Analysis Results")
                .font(.headline)
            
            // NEW: Display primary subject information
            let primarySubject = result.analysisResult.body.primarySubject
            
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Type:")
                        .fontWeight(.medium)
                    Text("\(primarySubject.category) - \(primarySubject.subcategory)")
                }
                
                if let operator = primarySubject.operator {
                    HStack {
                        Text("Operator:")
                            .fontWeight(.medium)
                        Text(operator)
                    }
                }
                
                if let fleetId = primarySubject.fleetId {
                    HStack {
                        Text("Fleet ID:")
                            .fontWeight(.medium)
                        Text(fleetId)
                    }
                }
                
                HStack {
                    Text("Confidence:")
                        .fontWeight(.medium)
                    Text("\(Int(primarySubject.confidence * 100))%")
                }
                
                if let licensePlate = primarySubject.additionalDetails.licensePlate {
                    HStack {
                        Text("License Plate:")
                            .fontWeight(.medium)
                        Text(licensePlate)
                    }
                }
                
                Text("Description:")
                    .fontWeight(.medium)
                Text(primarySubject.additionalDetails.description)
                    .foregroundColor(.secondary)
            }
            .padding()
            .background(Color.gray.opacity(0.1))
            .cornerRadius(8)
        }
    }
}
```

### 4. Example Response Handling

```swift
// Example: Handle different vehicle types
func handleAnalysisResult(_ result: AnalysisResult) {
    let primarySubject = result.analysisResult.body.primarySubject
    
    switch primarySubject.category {
    case "commercial_vehicle":
        if primarySubject.operator == "UPS" {
            print("UPS delivery vehicle detected with fleet ID: \(primarySubject.fleetId ?? "unknown")")
        } else if primarySubject.operator == "USPS" {
            print("USPS postal vehicle detected")
        }
        
    case "emergency_vehicle":
        print("Emergency vehicle detected: \(primarySubject.additionalDetails.description)")
        
    case "cargo_container":
        print("Shipping container detected: \(primarySubject.fleetId ?? "unknown")")
        
    default:
        print("Unknown subject: \(primarySubject.additionalDetails.description)")
    }
}
```

## Response Examples

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

For complete API documentation including all response formats and error handling, see the [API Reference](api-reference.md).

## Security Features

1. **No permanent AWS credentials** in your mobile app
2. **Time-limited upload URLs** (15 minutes expiry)
3. **Scoped S3 permissions** (uploads/* prefix only)
4. **Cognito Identity Pool** manages temporary credentials automatically
5. **HTTPS encryption** for all API calls

## Error Handling

The service provides detailed error responses:

```json
{
  "statusCode": 400,
  "body": {
    "error": "Invalid file extension. Allowed: jpg, jpeg, png, heic, heif"
  }
}
```

Common error scenarios:
- Invalid file extensions
- Upload URL expiry (15 minutes)
- Network connectivity issues
- Analysis processing failures

## Testing

You can test the endpoints using curl:

```bash
# Get upload URL
curl -X POST -H "Content-Type: application/json" \\
  -d '{"file_extension": "jpg"}' \\
  https://pcgwxp6v9a.execute-api.us-west-2.amazonaws.com/upload-url

# Analyze image (after upload)
curl -X POST -H "Content-Type: application/json" \\
  -d '{"image_key": "uploads/your-image.jpg", "bucket_name": "image-discerner-dev"}' \\
  https://pcgwxp6v9a.execute-api.us-west-2.amazonaws.com/analyze
```
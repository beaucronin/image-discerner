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

### 1. Swift Models

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
    let body: AnalysisBody
}

struct AnalysisBody: Codable {
    let analysisComplete: Bool
    let imageClassification: ImageClassification
    let textAnalysis: TextAnalysis
    let contextualInferences: [ContextualInference]
    
    enum CodingKeys: String, CodingKey {
        case analysisComplete = "analysis_complete"
        case imageClassification = "image_classification"
        case textAnalysis = "text_analysis"
        case contextualInferences = "contextual_inferences"
    }
}

struct ContextualInference: Codable {
    let vehicleType: String
    let confidence: Double
    let description: String
    let fleetIdentifiers: [String]
    let evidence: [String]
    
    enum CodingKeys: String, CodingKey {
        case vehicleType = "vehicle_type"
        case confidence
        case description
        case fleetIdentifiers = "fleet_identifiers"
        case evidence
    }
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
            
            ForEach(result.analysisResult.body.contextualInferences, id: \.vehicleType) { inference in
                VStack(alignment: .leading) {
                    Text(inference.description)
                        .font(.body)
                        .fontWeight(.medium)
                    
                    Text("Confidence: \\(Int(inference.confidence * 100))%")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding()
                .background(Color.gray.opacity(0.1))
                .cornerRadius(8)
            }
        }
    }
}
```

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
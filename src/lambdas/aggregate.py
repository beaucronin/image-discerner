import json
from datetime import datetime, timezone
from inference_engine import infer_vehicle_context

def merge_identifiers_with_classifications(classifications, text_identifiers):
    """
    Merge text identifiers with visual classifications to create enhanced results.
    
    For example, if we classify something as a "truck" and extract a fleet number,
    we can create a more complete identification.
    """
    enhanced_results = []
    
    for classification in classifications:
        enhanced_item = classification.copy()
        
        # Add relevant identifiers based on classification type
        if classification.get('category') == 'vehicle':
            if 'truck' in classification.get('subcategory', '').lower():
                enhanced_item['fleet_numbers'] = text_identifiers.get('fleet_numbers', [])
                enhanced_item['license_plates'] = text_identifiers.get('license_plates', [])
        
        elif classification.get('category') == 'container':
            enhanced_item['container_ids'] = text_identifiers.get('container_ids', [])
        
        enhanced_results.append(enhanced_item)
    
    return enhanced_results

def calculate_overall_confidence(classification_results, text_results):
    """Calculate overall confidence score based on both classification and text extraction"""
    classification_confidence = classification_results.get('confidence_scores', {})
    text_confidence = text_results.get('processing_metadata', {}).get('text_confidence', 0.0)
    
    # Simple weighted average - can be made more sophisticated
    if classification_confidence:
        avg_classification_confidence = sum(classification_confidence.values()) / len(classification_confidence)
        return (avg_classification_confidence * 0.7) + (text_confidence * 0.3)
    else:
        return text_confidence * 0.5  # Lower confidence if no classification

def handler(event, context):
    """
    Aggregates and combines results from classification and text extraction.
    
    - Merges parallel processing results
    - Applies business logic to enhance identifications
    - Formats final response structure
    """
    try:
        # Extract results from Step Functions parallel execution
        # Step Functions passes parallel results as a list directly in the event
        parallel_results = event if isinstance(event, list) else event.get('body', [])
        
        # Debug: log the actual event structure
        print(f"DEBUG: Event type: {type(event)}")
        print(f"DEBUG: Event content: {json.dumps(event, default=str)[:1000]}...")
        print(f"DEBUG: Parallel results count: {len(parallel_results)}")
        
        if len(parallel_results) != 2:
            return {
                'statusCode': 400,
                'body': {
                    'error': f'Expected 2 parallel results, got {len(parallel_results)}. Event: {json.dumps(event, default=str)[:500]}'
                }
            }
        
        # Parse results from parallel branches
        classification_results = None
        text_results = None
        
        for result in parallel_results:
            result_body = result.get('body', {})
            if 'classifications' in result_body:
                classification_results = result_body
            elif 'extracted_text' in result_body:
                text_results = result_body
        
        if not classification_results or not text_results:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Could not parse classification and text extraction results'
                }
            }
        
        # Merge and enhance results
        enhanced_classifications = merge_identifiers_with_classifications(
            classification_results.get('classifications', []),
            text_results.get('structured_identifiers', {})
        )
        
        # Apply contextual inference
        contextual_inferences = infer_vehicle_context(
            classification_results.get('classifications', []),
            text_results
        )
        
        # Calculate overall confidence
        overall_confidence = calculate_overall_confidence(classification_results, text_results)
        
        # Calculate total processing time
        classification_time = classification_results.get('processing_metadata', {}).get('processing_time_ms', 0)
        text_time = text_results.get('processing_metadata', {}).get('processing_time_ms', 0)
        total_processing_time = classification_time + text_time
        
        return {
            'statusCode': 200,
            'body': {
                'analysis_complete': True,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'image_classification': {
                    'detected_items': enhanced_classifications,
                    'raw_classifications': classification_results.get('classifications', []),
                    'detected_objects': classification_results.get('detected_objects', [])
                },
                'text_analysis': {
                    'extracted_text': text_results.get('extracted_text', ''),
                    'structured_identifiers': text_results.get('structured_identifiers', {}),
                    'text_blocks': text_results.get('text_blocks', [])
                },
                'contextual_inferences': contextual_inferences,
                'confidence_score': overall_confidence,
                'processing_metadata': {
                    'total_processing_time_ms': total_processing_time,
                    'classification_provider': classification_results.get('processing_metadata', {}).get('api_provider'),
                    'text_provider': text_results.get('processing_metadata', {}).get('api_provider'),
                    'image_key': classification_results.get('image_key') or text_results.get('image_key')
                }
            }
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'error': f'Result aggregation failed: {str(e)}',
                'analysis_complete': False
            }
        }
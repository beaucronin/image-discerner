import re
from typing import List, Dict, Any, Optional

# Vehicle type patterns combining visual + text evidence
VEHICLE_PATTERNS = {
    'postal_delivery': {
        'visual_requirements': ['van', 'truck', 'car'],
        'text_patterns': [
            r'usps\.com',
            r'\d{7}',  # 7-digit fleet numbers common for USPS
            r'priority',
            r'express',
            r'mail'
        ],
        'context_clues': ['parking_signs', 'residential_area'],
        'confidence_base': 0.8
    },
    'commercial_delivery': {
        'visual_requirements': ['truck', 'van'],
        'text_patterns': [
            r'fedex',
            r'ups',
            r'amazon',
            r'dhl',
            r'\d{4}-\d{4}',  # Common commercial fleet pattern
            r'delivery'
        ],
        'context_clues': ['commercial_area'],
        'confidence_base': 0.7
    },
    'shipping_container': {
        'visual_requirements': ['container', 'truck'],
        'text_patterns': [
            r'[A-Z]{4}\s?\d{6}\s?\d',  # Standard container ID format
            r'maersk',
            r'evergreen', 
            r'cosco',
            r'msc'
        ],
        'context_clues': ['port', 'industrial'],
        'confidence_base': 0.9
    },
    'emergency_vehicle': {
        'visual_requirements': ['car', 'truck', 'van'],
        'text_patterns': [
            r'police',
            r'fire',
            r'ambulance',
            r'ems',
            r'sheriff',
            r'\d{3}',  # Unit numbers
        ],
        'context_clues': ['emergency_lights', 'sirens'],
        'confidence_base': 0.85
    }
}

def extract_fleet_identifiers(text_blocks: List[Dict], extracted_text: str) -> List[Dict]:
    """Extract potential fleet identifiers from text"""
    fleet_ids = []
    
    # Look for 7-digit numbers (common USPS pattern)
    seven_digit_pattern = re.compile(r'\b\d{7}\b')
    for match in seven_digit_pattern.finditer(extracted_text):
        fleet_ids.append({
            'value': match.group(),
            'type': 'fleet_number',
            'pattern': '7_digit',
            'confidence': 0.8
        })
    
    # Look for container IDs (4 letters + 6 digits + 1 digit)
    container_pattern = re.compile(r'\b[A-Z]{4}\s?\d{6}\s?\d\b')
    for match in container_pattern.finditer(extracted_text):
        fleet_ids.append({
            'value': match.group().replace(' ', ''),
            'type': 'container_id',
            'pattern': 'iso_container',
            'confidence': 0.9
        })
    
    return fleet_ids

def calculate_pattern_match_score(pattern_config: Dict, classifications: List[Dict], 
                                extracted_text: str, text_blocks: List[Dict]) -> float:
    """Calculate how well the detected content matches a vehicle pattern"""
    score = 0.0
    evidence_count = 0
    
    # Check visual requirements (object detection)
    visual_matches = 0
    for classification in classifications:
        subcategory = classification.get('subcategory', '').lower()
        if subcategory in pattern_config['visual_requirements']:
            visual_matches += 1
            score += classification.get('confidence', 0) * 0.4
    
    if visual_matches == 0:
        return 0.0  # Must have visual evidence
    
    evidence_count += visual_matches
    
    # Check text patterns
    text_lower = extracted_text.lower()
    text_matches = 0
    for pattern in pattern_config['text_patterns']:
        if re.search(pattern, text_lower):
            text_matches += 1
            score += 0.3
    
    evidence_count += text_matches
    
    # Bonus for multiple text matches
    if text_matches > 1:
        score += 0.1
    
    # Normalize score by evidence count to prevent inflation
    if evidence_count > 0:
        score = min(score / evidence_count, 1.0)
    
    return score

def infer_vehicle_context(classifications: List[Dict], text_analysis: Dict) -> List[Dict]:
    """
    Apply contextual inference to determine vehicle types and purposes.
    
    Args:
        classifications: List of detected objects/vehicles
        text_analysis: Extracted text and structured identifiers
    
    Returns:
        List of contextual inferences with confidence scores
    """
    inferences = []
    extracted_text = text_analysis.get('extracted_text', '')
    text_blocks = text_analysis.get('text_blocks', [])
    
    # Extract fleet identifiers
    fleet_ids = extract_fleet_identifiers(text_blocks, extracted_text)
    
    # Test each vehicle pattern
    for vehicle_type, pattern_config in VEHICLE_PATTERNS.items():
        match_score = calculate_pattern_match_score(
            pattern_config, classifications, extracted_text, text_blocks
        )
        
        if match_score > 0.3:  # Minimum threshold for inference
            # Calculate final confidence
            base_confidence = pattern_config['confidence_base']
            final_confidence = min(match_score * base_confidence, 0.95)
            
            # Build evidence list
            evidence = []
            
            # Visual evidence
            for classification in classifications:
                subcategory = classification.get('subcategory', '').lower()
                if subcategory in pattern_config['visual_requirements']:
                    evidence.append(f"detected_{subcategory}")
            
            # Text evidence
            text_lower = extracted_text.lower()
            for pattern in pattern_config['text_patterns']:
                if re.search(pattern, text_lower):
                    evidence.append(f"text_pattern_{pattern}")
            
            # Add fleet IDs if found
            relevant_fleet_ids = []
            for fleet_id in fleet_ids:
                if vehicle_type == 'postal_delivery' and fleet_id['pattern'] == '7_digit':
                    relevant_fleet_ids.append(fleet_id['value'])
                elif vehicle_type == 'shipping_container' and fleet_id['pattern'] == 'iso_container':
                    relevant_fleet_ids.append(fleet_id['value'])
            
            inference = {
                'vehicle_type': vehicle_type,
                'confidence': final_confidence,
                'evidence': evidence,
                'fleet_identifiers': relevant_fleet_ids,
                'description': generate_description(vehicle_type, relevant_fleet_ids)
            }
            
            inferences.append(inference)
    
    # Sort by confidence and return top matches
    inferences.sort(key=lambda x: x['confidence'], reverse=True)
    return inferences

def generate_description(vehicle_type: str, fleet_ids: List[str]) -> str:
    """Generate human-readable description of the inference"""
    descriptions = {
        'postal_delivery': 'Postal delivery vehicle',
        'commercial_delivery': 'Commercial delivery vehicle', 
        'shipping_container': 'Shipping container',
        'emergency_vehicle': 'Emergency vehicle'
    }
    
    base_desc = descriptions.get(vehicle_type, f'{vehicle_type} vehicle')
    
    if fleet_ids:
        if len(fleet_ids) == 1:
            return f"{base_desc} with fleet ID {fleet_ids[0]}"
        else:
            return f"{base_desc} with fleet IDs {', '.join(fleet_ids)}"
    
    return base_desc
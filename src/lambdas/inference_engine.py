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

def extract_structured_identifiers(text_blocks: List[Dict], extracted_text: str) -> List[str]:
    """Extract structured identifiers in the format type:jurisdiction:number or type:number"""
    identifiers = []
    
    # Extract license plates with jurisdiction detection
    license_plates = extract_license_plates_with_jurisdiction(extracted_text)
    identifiers.extend(license_plates)
    
    # Extract fleet identifiers
    fleet_ids = extract_fleet_ids(extracted_text)
    identifiers.extend(fleet_ids)
    
    # Extract container IDs
    container_ids = extract_container_ids(extracted_text)
    identifiers.extend(container_ids)
    
    return identifiers

def extract_license_plates_with_jurisdiction(extracted_text: str) -> List[str]:
    """Extract license plates with jurisdiction detection"""
    plates = []
    
    # Common license plate patterns with basic jurisdiction detection
    # This is a simplified version - can be expanded with state-specific patterns
    patterns = [
        (r'\b[A-Z0-9]{2,3}\s?[A-Z0-9]{3,4}\b', 'unknown'),  # Standard format
        (r'\b[A-Z]{3}\s?\d{3,4}\b', 'unknown'),              # Letters + numbers
        (r'\b\d{3}\s?[A-Z]{3}\b', 'unknown')                 # Numbers + letters
    ]
    
    for pattern, default_jurisdiction in patterns:
        matches = re.findall(pattern, extracted_text.upper())
        for match in matches:
            clean_plate = match.replace(' ', '')
            # For now, use unknown jurisdiction - can be enhanced with state detection
            plates.append(f"license_plate:unknown:{clean_plate}")
    
    return plates

def extract_fleet_ids(extracted_text: str) -> List[str]:
    """Extract fleet identifiers"""
    fleet_ids = []
    
    # Look for 7-digit numbers (common USPS pattern)
    seven_digit_pattern = re.compile(r'\b\d{7}\b')
    for match in seven_digit_pattern.finditer(extracted_text):
        fleet_ids.append(f"fleet:{match.group()}")
    
    # Look for other fleet patterns
    fleet_patterns = [
        r'\b\d{4}-\d{4}\b',  # Common commercial fleet pattern
        r'\b[A-Z]{2}\d{4,6}\b'  # Letter prefix + numbers
    ]
    
    for pattern in fleet_patterns:
        matches = re.findall(pattern, extracted_text.upper())
        for match in matches:
            fleet_ids.append(f"fleet:{match}")
    
    return fleet_ids

def extract_container_ids(extracted_text: str) -> List[str]:
    """Extract container IDs in structured format"""
    container_ids = []
    
    # Look for container IDs (4 letters + 6 digits + 1 digit)
    # More restrictive pattern to avoid false positives
    container_pattern = re.compile(r'\b[A-Z]{4}\s?\d{6}\s?\d\b')
    for match in container_pattern.finditer(extracted_text.upper()):
        clean_id = match.group().replace(' ', '')
        # Skip if it looks like other patterns (e.g., starts with known operators)
        if not any(clean_id.startswith(op) for op in ['USPS', 'FEDX', 'UPSX']):
            container_ids.append(f"container_id:{clean_id}")
    
    return container_ids

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
    
    # Extract structured identifiers
    structured_identifiers = extract_structured_identifiers(text_blocks, extracted_text)
    
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
            
            # Filter relevant identifiers for this vehicle type
            relevant_identifiers = []
            for identifier in structured_identifiers:
                if vehicle_type == 'postal_delivery' and identifier.startswith('fleet:'):
                    relevant_identifiers.append(identifier)
                elif vehicle_type == 'shipping_container' and identifier.startswith('container_id:'):
                    relevant_identifiers.append(identifier)
                elif identifier.startswith('license_plate:'):
                    relevant_identifiers.append(identifier)
            
            inference = {
                'vehicle_type': vehicle_type,
                'confidence': final_confidence,
                'evidence': evidence,
                'structured_identifiers': relevant_identifiers,
                'description': generate_description(vehicle_type, relevant_identifiers)
            }
            
            inferences.append(inference)
    
    # Sort by confidence and return top matches
    inferences.sort(key=lambda x: x['confidence'], reverse=True)
    return inferences

def generate_description(vehicle_type: str, identifiers: List[str]) -> str:
    """Generate human-readable description of the inference"""
    descriptions = {
        'postal_delivery': 'Postal delivery vehicle',
        'commercial_delivery': 'Commercial delivery vehicle', 
        'shipping_container': 'Shipping container',
        'emergency_vehicle': 'Emergency vehicle'
    }
    
    base_desc = descriptions.get(vehicle_type, f'{vehicle_type} vehicle')
    
    if identifiers:
        # Extract key identifiers for description
        fleet_ids = [id.split(':')[-1] for id in identifiers if id.startswith('fleet:')]
        container_ids = [id.split(':')[-1] for id in identifiers if id.startswith('container_id:')]
        license_plates = [id.split(':')[-1] for id in identifiers if id.startswith('license_plate:')]
        
        if fleet_ids:
            if len(fleet_ids) == 1:
                return f"{base_desc} with fleet ID {fleet_ids[0]}"
            else:
                return f"{base_desc} with fleet IDs {', '.join(fleet_ids)}"
        elif container_ids:
            return f"{base_desc} {container_ids[0]}"
        elif license_plates:
            return f"{base_desc} with license plate {license_plates[0]}"
    
    return base_desc

def extract_operator_from_text(extracted_text: str) -> Optional[str]:
    """Extract the primary operator/company from text analysis"""
    text_lower = extracted_text.lower()
    
    # Known operators with their text patterns
    operators = {
        'UPS': [r'\bups\b', r'united parcel'],
        'FedEx': [r'\bfedex\b', r'federal express'],
        'USPS': [r'\busps\b', r'united states postal', r'us postal', r'usps\.com'],
        'Amazon': [r'\bamazon\b', r'prime'],
        'DHL': [r'\bdhl\b'],
        'Maersk': [r'\bmaersk\b'],
        'Evergreen': [r'\bevergreen\b'],
        'COSCO': [r'\bcosco\b'],
        'MSC': [r'\bmsc\b'],
        'Police': [r'\bpolice\b', r'\bpd\b', r'sheriff'],
        'Fire': [r'\bfire\b', r'\bfd\b'],
        'Ambulance': [r'\bambulance\b', r'\bems\b']
    }
    
    for operator, patterns in operators.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return operator
    
    return None


def determine_entities(classifications: List[Dict], text_analysis: Dict, 
                      contextual_inferences: List[Dict]) -> List[Dict[str, Any]]:
    """
    Analyze all available data to determine entities in the image
    and return a list of structured entities.
    """
    entities = []
    extracted_text = text_analysis.get('extracted_text', '')
    
    # Extract all structured identifiers
    structured_identifiers = extract_structured_identifiers(
        text_analysis.get('text_blocks', []), extracted_text
    )
    
    # If we have high-confidence contextual inferences, use them to create entities
    if contextual_inferences:
        for inference in contextual_inferences:
            if inference['confidence'] > 0.3:  # Only include reasonable confidence
                vehicle_type = inference['vehicle_type']
                
                # Map vehicle types to new type format
                type_mapping = {
                    'postal_delivery': 'commercial_vehicle:van',
                    'commercial_delivery': 'commercial_vehicle:van',
                    'shipping_container': 'cargo_container',
                    'emergency_vehicle': 'emergency_vehicle:response'
                }
                
                entity_type = type_mapping.get(vehicle_type, 'unknown')
                
                # Extract operator
                operator = extract_operator_from_text(extracted_text)
                
                # Get relevant identifiers for this entity
                relevant_identifiers = inference.get('structured_identifiers', [])
                
                entity = {
                    'type': entity_type,
                    'operator': operator,
                    'identifiers': relevant_identifiers,
                    'confidence': inference['confidence'],
                    'properties': {}
                }
                
                entities.append(entity)
    
    # Fallback: create entity from classifications if no contextual inferences
    if not entities and classifications:
        # Find the highest confidence classification
        best_classification = max(classifications, key=lambda x: x.get('confidence', 0))
        
        category = best_classification.get('category', 'unknown')
        subcategory = best_classification.get('subcategory', 'unknown')
        
        # Map to new type format
        if category == 'vehicle':
            if subcategory in ['van', 'truck']:
                entity_type = 'commercial_vehicle:van'
            else:
                entity_type = f'commercial_vehicle:{subcategory}'
        elif category == 'container':
            entity_type = 'cargo_container'
        else:
            entity_type = 'unknown'
        
        operator = extract_operator_from_text(extracted_text)
        
        entity = {
            'type': entity_type,
            'operator': operator,
            'identifiers': structured_identifiers,
            'confidence': best_classification.get('confidence', 0.0),
            'properties': {}
        }
        
        entities.append(entity)
    
    # If still no entities, create a minimal unknown entity
    if not entities:
        entity = {
            'type': 'unknown',
            'operator': None,
            'identifiers': structured_identifiers,
            'confidence': 0.0,
            'properties': {}
        }
        entities.append(entity)
    
    return entities


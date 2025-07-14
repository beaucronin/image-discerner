import os
from .base import CVBackend
from .mock_backend import MockCVBackend

def get_cv_backend() -> CVBackend:
    """
    Factory function to get the appropriate CV backend based on configuration.
    
    Uses environment variable CV_BACKEND to determine which backend to use:
    - 'mock' or 'test': MockCVBackend
    - 'gcp': GCPVisionBackend
    - Default: MockCVBackend for safety
    """
    backend_type = os.environ.get('CV_BACKEND', 'mock').lower()
    
    if backend_type in ['mock', 'test']:
        return MockCVBackend()
    elif backend_type == 'gcp':
        from .gcp_backend import GCPVisionBackend
        return GCPVisionBackend()
    else:
        # Default to mock for safety
        print(f"Unknown CV_BACKEND '{backend_type}', defaulting to mock")
        return MockCVBackend()

def get_classification_backend() -> CVBackend:
    """
    Get backend for object detection/classification tasks.
    
    Uses CLASSIFICATION_BACKEND env var, falls back to CV_BACKEND:
    - 'mock': MockCVBackend
    - 'gcp_vision': GCP Vision API (general object detection)
    - 'gcp_automl': GCP AutoML Vision (custom object detection)
    """
    backend_type = os.environ.get('CLASSIFICATION_BACKEND', os.environ.get('CV_BACKEND', 'mock')).lower()
    
    if backend_type in ['mock', 'test']:
        return MockCVBackend()
    elif backend_type in ['gcp', 'gcp_vision']:
        from .gcp_backend import GCPVisionBackend
        return GCPVisionBackend()
    elif backend_type == 'gcp_vision_rest':
        from .gcp_rest_backend import GCPVisionRestBackend
        return GCPVisionRestBackend()
    elif backend_type == 'gcp_automl':
        # TODO: Implement GCPAutoMLBackend
        raise NotImplementedError("GCP AutoML backend not yet implemented")
    else:
        print(f"Unknown CLASSIFICATION_BACKEND '{backend_type}', defaulting to mock")
        return MockCVBackend()

def get_text_extraction_backend() -> CVBackend:
    """
    Get backend for OCR/text extraction tasks.
    
    Uses TEXT_EXTRACTION_BACKEND env var, falls back to CV_BACKEND:
    - 'mock': MockCVBackend
    - 'gcp_vision': GCP Vision API (OCR)
    - 'gcp_document_ai': GCP Document AI (advanced OCR)
    """
    backend_type = os.environ.get('TEXT_EXTRACTION_BACKEND', os.environ.get('CV_BACKEND', 'mock')).lower()
    
    if backend_type in ['mock', 'test']:
        return MockCVBackend()
    elif backend_type in ['gcp', 'gcp_vision']:
        from .gcp_backend import GCPVisionBackend
        return GCPVisionBackend()
    elif backend_type == 'gcp_vision_rest':
        from .gcp_rest_backend import GCPVisionRestBackend
        return GCPVisionRestBackend()
    elif backend_type == 'gcp_document_ai':
        # TODO: Implement GCPDocumentAIBackend
        raise NotImplementedError("GCP Document AI backend not yet implemented")
    else:
        print(f"Unknown TEXT_EXTRACTION_BACKEND '{backend_type}', defaulting to mock")
        return MockCVBackend()
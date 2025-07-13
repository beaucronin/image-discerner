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
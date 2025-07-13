import pytest
from unittest.mock import Mock, patch
import json
import os
from src.cv_backends.mock_backend import MockCVBackend
from src.cv_backends.factory import get_cv_backend

class TestMockCVBackend:
    """Unit tests for MockCVBackend"""
    
    def setup_method(self):
        self.backend = MockCVBackend()
        self.sample_image_data = b"fake_image_data"
    
    def test_classify_image_returns_valid_structure(self):
        """Test that classification returns expected structure"""
        result = self.backend.classify_image(self.sample_image_data)
        
        assert 'classifications' in result
        assert 'detected_objects' in result
        assert 'confidence_scores' in result
        assert 'processing_metadata' in result
        
        # Check processing metadata
        metadata = result['processing_metadata']
        assert metadata['api_provider'] == 'mock_backend'
        assert metadata['model_version'] == 'mock-v1.0'
        assert isinstance(metadata['processing_time_ms'], int)
        assert metadata['processing_time_ms'] > 0
    
    def test_classify_image_returns_valid_classifications(self):
        """Test that classifications have required fields"""
        result = self.backend.classify_image(self.sample_image_data)
        
        classifications = result['classifications']
        assert len(classifications) >= 1
        assert len(classifications) <= 3
        
        for classification in classifications:
            assert 'category' in classification
            assert 'subcategory' in classification
            assert 'confidence' in classification
            assert 'bounding_box' in classification
            
            # Check confidence is reasonable
            assert 0.5 <= classification['confidence'] <= 1.0
            
            # Check bounding box structure
            bbox = classification['bounding_box']
            assert all(key in bbox for key in ['x', 'y', 'width', 'height'])
    
    def test_extract_text_returns_valid_structure(self):
        """Test that text extraction returns expected structure"""
        result = self.backend.extract_text(self.sample_image_data)
        
        assert 'extracted_text' in result
        assert 'text_blocks' in result
        assert 'processing_metadata' in result
        
        # Check processing metadata
        metadata = result['processing_metadata']
        assert metadata['api_provider'] == 'mock_backend'
        assert isinstance(metadata['text_confidence'], float)
        assert isinstance(metadata['processing_time_ms'], int)
    
    def test_extract_text_returns_realistic_data(self):
        """Test that text extraction returns realistic commercial data"""
        result = self.backend.extract_text(self.sample_image_data)
        
        extracted_text = result['extracted_text']
        assert isinstance(extracted_text, str)
        assert len(extracted_text) > 0
        
        # Should contain some realistic commercial identifiers
        text_upper = extracted_text.upper()
        has_commercial_content = any(keyword in text_upper for keyword in 
                                   ['UPS', 'FEDEX', 'FLEET', 'CONTAINER', 'LICENSE', 'TRUCK'])
        assert has_commercial_content
        
        # Check text blocks
        text_blocks = result['text_blocks']
        assert isinstance(text_blocks, list)
        assert len(text_blocks) > 0
        
        for block in text_blocks:
            assert 'text' in block
            assert 'confidence' in block
            assert 'bounding_box' in block
            assert 0.8 <= block['confidence'] <= 1.0
    
    def test_get_provider_name(self):
        """Test provider name is correct"""
        assert self.backend.get_provider_name() == "mock_backend"

class TestCVBackendFactory:
    """Unit tests for CV backend factory"""
    
    def test_factory_returns_mock_by_default(self):
        """Test factory returns mock backend by default"""
        with patch.dict(os.environ, {}, clear=True):
            backend = get_cv_backend()
            assert isinstance(backend, MockCVBackend)
    
    def test_factory_returns_mock_when_specified(self):
        """Test factory returns mock backend when CV_BACKEND=mock"""
        with patch.dict(os.environ, {'CV_BACKEND': 'mock'}):
            backend = get_cv_backend()
            assert isinstance(backend, MockCVBackend)
    
    def test_factory_returns_mock_for_test_backend(self):
        """Test factory returns mock backend when CV_BACKEND=test"""
        with patch.dict(os.environ, {'CV_BACKEND': 'test'}):
            backend = get_cv_backend()
            assert isinstance(backend, MockCVBackend)
    
    def test_factory_falls_back_to_mock_for_unknown_backend(self):
        """Test factory falls back to mock for unknown backend types"""
        with patch.dict(os.environ, {'CV_BACKEND': 'unknown_backend'}):
            backend = get_cv_backend()
            assert isinstance(backend, MockCVBackend)
    
    @patch('src.cv_backends.gcp_backend.GCPVisionBackend')
    def test_factory_returns_gcp_when_specified(self, mock_gcp_class):
        """Test factory returns GCP backend when CV_BACKEND=gcp"""
        mock_instance = Mock()
        mock_gcp_class.return_value = mock_instance
        
        with patch.dict(os.environ, {'CV_BACKEND': 'gcp'}):
            backend = get_cv_backend()
            assert backend == mock_instance
            mock_gcp_class.assert_called_once()

class TestGCPVisionBackend:
    """Unit tests for GCPVisionBackend (mocked)"""
    
    @patch('src.cv_backends.gcp_backend.boto3.client')
    @patch('src.cv_backends.gcp_backend.vision.ImageAnnotatorClient.from_service_account_info')
    def test_gcp_backend_initialization(self, mock_vision_client, mock_boto_client):
        """Test GCP backend initializes correctly with credentials"""
        # Mock AWS Secrets Manager
        mock_secrets = Mock()
        mock_secrets.get_secret_value.return_value = {
            'SecretString': json.dumps({'type': 'service_account', 'project_id': 'test'})
        }
        mock_boto_client.return_value = mock_secrets
        
        # Mock Vision client
        mock_vision_instance = Mock()
        mock_vision_client.return_value = mock_vision_instance
        
        with patch.dict(os.environ, {'GCP_CREDENTIALS_SECRET_NAME': 'test-secret'}):
            from src.cv_backends.gcp_backend import GCPVisionBackend
            backend = GCPVisionBackend()
            
            assert backend.vision_client == mock_vision_instance
            mock_secrets.get_secret_value.assert_called_once_with(SecretId='test-secret')
            mock_vision_client.assert_called_once()
    
    @patch('src.cv_backends.gcp_backend.boto3.client')
    def test_gcp_backend_handles_missing_secret_name(self, mock_boto_client):
        """Test GCP backend handles missing secret name gracefully"""
        with patch.dict(os.environ, {}, clear=True):
            from src.cv_backends.gcp_backend import GCPVisionBackend
            backend = GCPVisionBackend()
            
            assert backend.vision_client is None
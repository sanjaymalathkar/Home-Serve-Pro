"""
OCR Service for HomeServe Pro.
Handles document text extraction and validation for vendor KYC.
"""

import re
import base64
import requests
from PIL import Image
import pytesseract
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple


class OCRService:
    """Service for OCR and document validation."""
    
    # Document patterns for validation
    PATTERNS = {
        'pan_card': r'[A-Z]{5}[0-9]{4}[A-Z]{1}',
        'aadhaar': r'\d{4}\s?\d{4}\s?\d{4}',
        'gstin': r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}',
        'ifsc': r'[A-Z]{4}0[A-Z0-9]{6}',
        'phone': r'[6-9]\d{9}',
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    }
    
    @staticmethod
    def preprocess_image(image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR results.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            np.ndarray: Preprocessed image
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.medianBlur(gray, 3)
            
            # Apply thresholding
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Apply morphological operations
            kernel = np.ones((1, 1), np.uint8)
            processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return processed
            
        except Exception as e:
            print(f"Error preprocessing image: {str(e)}")
            return cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    @staticmethod
    def extract_text(image_path: str) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str: Extracted text
        """
        try:
            # Preprocess image
            processed_image = OCRService.preprocess_image(image_path)
            
            # Configure tesseract
            config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz '
            
            # Extract text
            text = pytesseract.image_to_string(processed_image, config=config)
            
            return text.strip()
            
        except Exception as e:
            print(f"Error extracting text: {str(e)}")
            return ""
    
    @staticmethod
    def validate_document(doc_type: str, extracted_text: str) -> Dict:
        """
        Validate document based on type and extracted text.
        
        Args:
            doc_type (str): Type of document
            extracted_text (str): Text extracted from document
            
        Returns:
            Dict: Validation results
        """
        result = {
            'is_valid': False,
            'confidence': 0.0,
            'extracted_data': {},
            'errors': []
        }
        
        try:
            if doc_type == 'id_proof':
                result = OCRService._validate_id_proof(extracted_text)
            elif doc_type == 'address_proof':
                result = OCRService._validate_address_proof(extracted_text)
            elif doc_type == 'business_license':
                result = OCRService._validate_business_license(extracted_text)
            elif doc_type == 'bank_details':
                result = OCRService._validate_bank_details(extracted_text)
            else:
                result['errors'].append(f'Unknown document type: {doc_type}')
                
        except Exception as e:
            result['errors'].append(f'Validation error: {str(e)}')
        
        return result
    
    @staticmethod
    def _validate_id_proof(text: str) -> Dict:
        """Validate ID proof documents (PAN, Aadhaar)."""
        result = {
            'is_valid': False,
            'confidence': 0.0,
            'extracted_data': {},
            'errors': []
        }
        
        # Check for PAN card
        pan_matches = re.findall(OCRService.PATTERNS['pan_card'], text.upper())
        if pan_matches:
            result['extracted_data']['pan_number'] = pan_matches[0]
            result['confidence'] += 0.4
        
        # Check for Aadhaar
        aadhaar_matches = re.findall(OCRService.PATTERNS['aadhaar'], text)
        if aadhaar_matches:
            result['extracted_data']['aadhaar_number'] = aadhaar_matches[0]
            result['confidence'] += 0.4
        
        # Check for name
        lines = text.split('\n')
        for line in lines:
            if len(line.strip()) > 3 and line.strip().replace(' ', '').isalpha():
                if 'name' not in result['extracted_data']:
                    result['extracted_data']['name'] = line.strip()
                    result['confidence'] += 0.2
                    break
        
        result['is_valid'] = result['confidence'] >= 0.6
        
        if not result['is_valid']:
            result['errors'].append('Could not extract sufficient information from ID proof')
        
        return result
    
    @staticmethod
    def _validate_address_proof(text: str) -> Dict:
        """Validate address proof documents."""
        result = {
            'is_valid': False,
            'confidence': 0.0,
            'extracted_data': {},
            'errors': []
        }
        
        # Look for pincode
        pincode_pattern = r'\b\d{6}\b'
        pincode_matches = re.findall(pincode_pattern, text)
        if pincode_matches:
            result['extracted_data']['pincode'] = pincode_matches[0]
            result['confidence'] += 0.3
        
        # Look for address keywords
        address_keywords = ['address', 'house', 'street', 'road', 'city', 'state']
        found_keywords = sum(1 for keyword in address_keywords if keyword.lower() in text.lower())
        if found_keywords >= 2:
            result['confidence'] += 0.4
        
        # Extract potential address lines
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 5]
        if lines:
            result['extracted_data']['address_lines'] = lines[:3]  # First 3 lines
            result['confidence'] += 0.3
        
        result['is_valid'] = result['confidence'] >= 0.6
        
        if not result['is_valid']:
            result['errors'].append('Could not extract sufficient address information')
        
        return result
    
    @staticmethod
    def _validate_business_license(text: str) -> Dict:
        """Validate business license documents."""
        result = {
            'is_valid': False,
            'confidence': 0.0,
            'extracted_data': {},
            'errors': []
        }
        
        # Check for GSTIN
        gstin_matches = re.findall(OCRService.PATTERNS['gstin'], text.upper())
        if gstin_matches:
            result['extracted_data']['gstin'] = gstin_matches[0]
            result['confidence'] += 0.5
        
        # Look for business keywords
        business_keywords = ['license', 'registration', 'certificate', 'business', 'trade']
        found_keywords = sum(1 for keyword in business_keywords if keyword.lower() in text.lower())
        if found_keywords >= 1:
            result['confidence'] += 0.3
        
        # Look for license number patterns
        license_pattern = r'[A-Z0-9]{6,20}'
        license_matches = re.findall(license_pattern, text.upper())
        if license_matches:
            result['extracted_data']['license_number'] = license_matches[0]
            result['confidence'] += 0.2
        
        result['is_valid'] = result['confidence'] >= 0.5
        
        if not result['is_valid']:
            result['errors'].append('Could not validate business license')
        
        return result
    
    @staticmethod
    def _validate_bank_details(text: str) -> Dict:
        """Validate bank details documents."""
        result = {
            'is_valid': False,
            'confidence': 0.0,
            'extracted_data': {},
            'errors': []
        }
        
        # Check for IFSC code
        ifsc_matches = re.findall(OCRService.PATTERNS['ifsc'], text.upper())
        if ifsc_matches:
            result['extracted_data']['ifsc_code'] = ifsc_matches[0]
            result['confidence'] += 0.4
        
        # Look for account number (8-18 digits)
        account_pattern = r'\b\d{8,18}\b'
        account_matches = re.findall(account_pattern, text)
        if account_matches:
            result['extracted_data']['account_number'] = account_matches[0]
            result['confidence'] += 0.4
        
        # Look for bank keywords
        bank_keywords = ['bank', 'account', 'branch', 'ifsc']
        found_keywords = sum(1 for keyword in bank_keywords if keyword.lower() in text.lower())
        if found_keywords >= 2:
            result['confidence'] += 0.2
        
        result['is_valid'] = result['confidence'] >= 0.6
        
        if not result['is_valid']:
            result['errors'].append('Could not extract sufficient bank details')
        
        return result
    
    @staticmethod
    def process_document(image_path: str, doc_type: str) -> Dict:
        """
        Complete document processing pipeline.
        
        Args:
            image_path (str): Path to the document image
            doc_type (str): Type of document
            
        Returns:
            Dict: Processing results
        """
        try:
            # Extract text
            extracted_text = OCRService.extract_text(image_path)
            
            if not extracted_text:
                return {
                    'success': False,
                    'error': 'Could not extract text from document',
                    'extracted_text': '',
                    'validation': {}
                }
            
            # Validate document
            validation = OCRService.validate_document(doc_type, extracted_text)
            
            return {
                'success': True,
                'extracted_text': extracted_text,
                'validation': validation,
                'doc_type': doc_type
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'extracted_text': '',
                'validation': {}
            }

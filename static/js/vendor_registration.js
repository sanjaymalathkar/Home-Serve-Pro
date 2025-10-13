/**
 * Vendor Registration JavaScript
 * Handles multi-step registration form with validation and file uploads
 */

class VendorRegistration {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 5;
        this.uploadedFiles = {};
        this.services = [];
        
        this.init();
    }
    
    init() {
        this.loadServices();
        this.setupEventListeners();
        this.setupFileUploads();
        this.updateUI();
    }
    
    setupEventListeners() {
        // Navigation buttons
        document.getElementById('nextBtn').addEventListener('click', () => this.nextStep());
        document.getElementById('prevBtn').addEventListener('click', () => this.prevStep());
        document.getElementById('submitBtn').addEventListener('click', (e) => this.submitRegistration(e));
        
        // Form validation
        document.getElementById('registrationForm').addEventListener('input', (e) => this.validateField(e.target));
    }
    
    setupFileUploads() {
        const uploadAreas = document.querySelectorAll('.document-upload');
        
        uploadAreas.forEach(area => {
            const input = area.querySelector('input[type="file"]');
            const docType = area.dataset.docType;
            
            // Click to upload
            area.addEventListener('click', () => input.click());
            
            // Drag and drop
            area.addEventListener('dragover', (e) => {
                e.preventDefault();
                area.classList.add('dragover');
            });
            
            area.addEventListener('dragleave', () => {
                area.classList.remove('dragover');
            });
            
            area.addEventListener('drop', (e) => {
                e.preventDefault();
                area.classList.remove('dragover');
                this.handleFileUpload(e.dataTransfer.files, docType);
            });
            
            // File input change
            input.addEventListener('change', (e) => {
                this.handleFileUpload(e.target.files, docType);
            });
        });
    }
    
    async loadServices() {
        try {
            const response = await fetch('/api/services');
            const data = await response.json();
            
            if (data.success) {
                this.services = data.data.services;
                this.renderServices();
            }
        } catch (error) {
            console.error('Failed to load services:', error);
        }
    }
    
    renderServices() {
        const container = document.getElementById('servicesContainer');
        const servicesByCategory = {};
        
        // Group services by category
        this.services.forEach(service => {
            const category = service.category || 'Other';
            if (!servicesByCategory[category]) {
                servicesByCategory[category] = [];
            }
            servicesByCategory[category].push(service);
        });
        
        // Render services
        let html = '';
        Object.keys(servicesByCategory).forEach(category => {
            html += `
                <div class="mb-3">
                    <h6 class="text-primary">${category}</h6>
                    <div class="row">
            `;
            
            servicesByCategory[category].forEach(service => {
                html += `
                    <div class="col-md-6 col-lg-4 mb-2">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="services" 
                                   value="${service.name}" id="service_${service.id}">
                            <label class="form-check-label" for="service_${service.id}">
                                ${service.name}
                            </label>
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    handleFileUpload(files, docType) {
        if (!this.uploadedFiles[docType]) {
            this.uploadedFiles[docType] = [];
        }
        
        Array.from(files).forEach(file => {
            // Validate file
            if (!this.validateFile(file)) {
                return;
            }
            
            // Add to uploaded files
            this.uploadedFiles[docType].push(file);
            
            // Show uploaded file
            this.showUploadedFile(file, docType);
        });
    }
    
    validateFile(file) {
        const maxSize = 5 * 1024 * 1024; // 5MB
        const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf'];
        
        if (file.size > maxSize) {
            this.showAlert('File size should not exceed 5MB', 'error');
            return false;
        }
        
        if (!allowedTypes.includes(file.type)) {
            this.showAlert('Only JPEG, PNG, and PDF files are allowed', 'error');
            return false;
        }
        
        return true;
    }
    
    showUploadedFile(file, docType) {
        const container = document.getElementById(`${docType}_files`);
        const fileDiv = document.createElement('div');
        fileDiv.className = 'uploaded-file';
        fileDiv.innerHTML = `
            <div>
                <i class="fas fa-file-alt text-primary me-2"></i>
                <span>${file.name}</span>
                <small class="text-muted ms-2">(${this.formatFileSize(file.size)})</small>
            </div>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        container.appendChild(fileDiv);
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        
        // Remove existing validation classes
        field.classList.remove('is-valid', 'is-invalid');
        
        // Required field validation
        if (field.hasAttribute('required') && !value) {
            isValid = false;
        }
        
        // Specific field validations
        switch (field.name) {
            case 'phone':
                isValid = /^[6-9]\d{9}$/.test(value);
                break;
            case 'pincode':
                isValid = /^\d{6}$/.test(value);
                break;
            case 'ifsc_code':
                isValid = /^[A-Z]{4}0[A-Z0-9]{6}$/.test(value.toUpperCase());
                break;
            case 'account_number':
                isValid = /^\d{8,18}$/.test(value);
                break;
        }
        
        // Apply validation classes
        if (value) {
            field.classList.add(isValid ? 'is-valid' : 'is-invalid');
        }
        
        return isValid;
    }
    
    validateStep(step) {
        const section = document.querySelector(`[data-step="${step}"]`);
        const requiredFields = section.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        // Special validations
        if (step === 3) {
            const selectedServices = section.querySelectorAll('input[name="services"]:checked');
            if (selectedServices.length === 0) {
                this.showAlert('Please select at least one service', 'error');
                isValid = false;
            }
        }
        
        if (step === 4) {
            const requiredDocs = ['id_proof', 'address_proof'];
            for (const docType of requiredDocs) {
                if (!this.uploadedFiles[docType] || this.uploadedFiles[docType].length === 0) {
                    this.showAlert(`Please upload ${docType.replace('_', ' ')}`, 'error');
                    isValid = false;
                }
            }
        }
        
        return isValid;
    }
    
    nextStep() {
        if (!this.validateStep(this.currentStep)) {
            return;
        }
        
        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            this.updateUI();
        }
    }
    
    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateUI();
        }
    }
    
    updateUI() {
        // Update step indicators
        document.querySelectorAll('.step').forEach((step, index) => {
            const stepNum = index + 1;
            step.classList.remove('active', 'completed');
            
            if (stepNum < this.currentStep) {
                step.classList.add('completed');
            } else if (stepNum === this.currentStep) {
                step.classList.add('active');
            }
        });
        
        // Update form sections
        document.querySelectorAll('.form-section').forEach(section => {
            section.classList.remove('active');
        });
        document.querySelector(`[data-step="${this.currentStep}"]`).classList.add('active');
        
        // Update progress bar
        const progress = (this.currentStep / this.totalSteps) * 100;
        document.getElementById('progressBar').style.width = `${progress}%`;
        
        // Update navigation buttons
        document.getElementById('prevBtn').style.display = this.currentStep > 1 ? 'block' : 'none';
        document.getElementById('nextBtn').style.display = this.currentStep < this.totalSteps ? 'block' : 'none';
        document.getElementById('submitBtn').style.display = this.currentStep === this.totalSteps ? 'block' : 'none';
    }
    
    async submitRegistration(e) {
        e.preventDefault();
        
        if (!this.validateStep(this.currentStep)) {
            return;
        }
        
        // Show loading modal
        const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
        loadingModal.show();
        
        try {
            // Collect form data
            const formData = this.collectFormData();
            
            // Submit registration in steps
            await this.submitStep1(formData);
            await this.submitStep2(formData);
            await this.submitStep3(formData);
            await this.submitStep4();
            await this.submitStep5(formData);
            
            // Success
            loadingModal.hide();
            this.showAlert('Registration completed successfully! Your profile is under review.', 'success');
            
            // Redirect after delay
            setTimeout(() => {
                window.location.href = '/vendor/dashboard';
            }, 3000);
            
        } catch (error) {
            loadingModal.hide();
            this.showAlert(`Registration failed: ${error.message}`, 'error');
        }
    }
    
    collectFormData() {
        const form = document.getElementById('registrationForm');
        const formData = new FormData(form);
        const data = {};
        
        // Convert FormData to object
        for (const [key, value] of formData.entries()) {
            if (data[key]) {
                if (Array.isArray(data[key])) {
                    data[key].push(value);
                } else {
                    data[key] = [data[key], value];
                }
            } else {
                data[key] = value;
            }
        }
        
        // Handle checkboxes
        const checkboxes = form.querySelectorAll('input[type="checkbox"]:checked');
        const services = [];
        const languages = [];
        
        checkboxes.forEach(cb => {
            if (cb.name === 'services') {
                services.push(cb.value);
            } else if (cb.name === 'languages') {
                languages.push(cb.value);
            }
        });
        
        data.services = services;
        data.languages = languages;
        
        return data;
    }
    
    async submitStep1(data) {
        const response = await fetch('/api/vendor/register/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                name: data.name,
                phone: data.phone,
                address: data.address,
                pincode: data.pincode
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Step 1 failed');
        }
    }
    
    async submitStep2(data) {
        const response = await fetch('/api/vendor/register/business', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                business_type: data.business_type,
                business_name: data.business_name,
                business_address: data.business_address,
                business_registration_number: data.business_registration_number,
                tax_id: data.tax_id,
                experience_years: parseInt(data.experience_years) || 0,
                languages: data.languages
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Step 2 failed');
        }
    }
    
    async submitStep3(data) {
        const response = await fetch('/api/vendor/register/services', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                services: data.services,
                service_areas: data.service_areas ? data.service_areas.split(',').map(s => s.trim()) : [],
                specializations: data.specializations ? data.specializations.split(',').map(s => s.trim()) : []
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Step 3 failed');
        }
    }
    
    async submitStep4() {
        const formData = new FormData();
        const docTypes = [];
        
        // Add uploaded files
        Object.keys(this.uploadedFiles).forEach(docType => {
            this.uploadedFiles[docType].forEach(file => {
                formData.append('documents', file);
                docTypes.push(docType);
            });
        });
        
        // Add document types
        docTypes.forEach(type => {
            formData.append('doc_types', type);
        });
        
        const response = await fetch('/api/vendor/register/documents', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Step 4 failed');
        }
    }
    
    async submitStep5(data) {
        const response = await fetch('/api/vendor/register/bank-details', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                account_holder_name: data.account_holder_name,
                account_number: data.account_number,
                ifsc_code: data.ifsc_code.toUpperCase(),
                bank_name: data.bank_name,
                branch_name: data.branch_name,
                account_type: data.account_type,
                upi_id: data.upi_id
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Step 5 failed');
        }
    }
    
    showAlert(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.insertBefore(alertDiv, document.body.firstChild);
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new VendorRegistration();
});

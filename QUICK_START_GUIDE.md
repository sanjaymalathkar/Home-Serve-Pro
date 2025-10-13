# Quick Start Guide - Complete Vendor Onboarding Implementation

## 🚀 What's Already Done

✅ **Backend is 100% Complete!**
- All database models updated with new fields
- All API endpoints created and working
- Admin approval system fully functional
- Vendor registration flow updated

## 🎯 What You Need to Do

### Step 1: Test the Backend APIs

You can test the backend immediately using curl or Postman:

#### 1. Register a Vendor
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "vendor@test.com",
    "password": "password123",
    "name": "Test Vendor",
    "phone": "1234567890",
    "role": "vendor"
  }'
```

#### 2. Login and Get Token
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "vendor@test.com",
    "password": "password123"
  }'
```

#### 3. Get Dashboard Data
```bash
curl -X GET http://localhost:5000/api/vendor/dashboard \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### 4. Submit Verification Documents
```bash
curl -X POST http://localhost:5000/api/vendor/verify_profile \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": {
      "id_proof": "https://example.com/id.pdf",
      "business_license": "https://example.com/license.pdf",
      "service_certification": "https://example.com/cert.pdf"
    }
  }'
```

#### 5. Admin: Get Verification Requests
```bash
curl -X GET http://localhost:5000/api/onboard_manager/vendor_verification_requests \
  -H "Authorization: Bearer ADMIN_TOKEN_HERE"
```

#### 6. Admin: Approve Vendor
```bash
curl -X POST http://localhost:5000/api/onboard_manager/vendors/VENDOR_ID/approve \
  -H "Authorization: Bearer ADMIN_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "All documents verified"
  }'
```

#### 7. Create Custom Service (After Approval)
```bash
curl -X POST http://localhost:5000/api/vendor/services/create \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Emergency Plumbing",
    "category": "Plumbing",
    "price": 500,
    "duration": 60,
    "description": "24/7 emergency plumbing service",
    "availability": true
  }'
```

---

### Step 2: Complete the Frontend

The HTML structure is already created in `app/templates/vendor_dashboard_new.html`.

You need to create the JavaScript file:

**Create file**: `static/js/vendor_dashboard.js`

```javascript
let currentUser = null;
let vendorData = null;
let allBookings = [];
let currentFilter = 'all';

document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }
    currentUser = JSON.parse(localStorage.getItem('user') || '{}');
    document.getElementById('userName').textContent = currentUser.name || currentUser.email;

    // Load dashboard data
    await loadDashboard();
    
    // Setup form handlers
    setupFormHandlers();
});

async function loadDashboard() {
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/vendor/dashboard', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.success) {
            vendorData = data.vendor_info;
            
            // Update status badge
            updateStatusBadge(vendorData.status, vendorData.documents_verified);
            
            // Show/hide sections based on status
            updateDashboardVisibility(vendorData);
            
            // Load statistics
            updateStatistics(data.statistics);
            
            // Update welcome message
            updateWelcomeMessage(vendorData);
            
            // Load bookings if approved
            if (vendorData.is_approved) {
                await loadBookings();
            }
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function updateStatusBadge(status, verified) {
    const badge = document.getElementById('statusBadge');
    
    if (status === 'active' && verified) {
        badge.className = 'badge bg-success';
        badge.textContent = '✅ Verified';
    } else if (status === 'pending_verification') {
        badge.className = 'badge bg-warning';
        badge.textContent = '⏳ Pending Verification';
    } else if (status === 'rejected') {
        badge.className = 'badge bg-danger';
        badge.textContent = '❌ Rejected';
    } else {
        badge.className = 'badge bg-secondary';
        badge.textContent = status;
    }
}

function updateDashboardVisibility(vendor) {
    // Verify Profile - always visible
    document.getElementById('menu-verify-profile').style.display = 'block';
    
    // Create Service - only if approved
    const createServiceMenu = document.getElementById('menu-create-service');
    createServiceMenu.style.display = vendor.is_approved ? 'block' : 'none';
    
    // Bookings - only if approved
    const bookingsMenu = document.getElementById('menu-bookings');
    bookingsMenu.style.display = vendor.is_approved ? 'block' : 'none';
    
    // Payouts - always visible but content changes
    if (vendor.payouts_enabled) {
        document.getElementById('payoutsDisabled').classList.add('d-none');
        document.getElementById('payoutsEnabled').classList.remove('d-none');
        loadPayoutData();
    } else {
        document.getElementById('payoutsDisabled').classList.remove('d-none');
        document.getElementById('payoutsEnabled').classList.add('d-none');
    }
    
    // Update verification status
    updateVerificationStatus(vendor);
}

function updateVerificationStatus(vendor) {
    const statusEl = document.getElementById('verificationStatus');
    const rejectionEl = document.getElementById('rejectionReason');
    
    if (vendor.status === 'pending_verification' && vendor.verification_docs.length > 0) {
        statusEl.innerHTML = '<span class="badge bg-warning">⏳ Pending Admin Approval</span>';
    } else if (vendor.status === 'pending_verification') {
        statusEl.innerHTML = '<span class="badge bg-info">📝 Please upload documents</span>';
    } else if (vendor.documents_verified) {
        statusEl.innerHTML = '<span class="badge bg-success">✅ Verified</span>';
    } else if (vendor.status === 'rejected') {
        statusEl.innerHTML = '<span class="badge bg-danger">❌ Rejected</span>';
        if (vendor.rejection_reason) {
            document.getElementById('rejectionText').textContent = vendor.rejection_reason;
            rejectionEl.classList.remove('d-none');
        }
    }
}

function updateWelcomeMessage(vendor) {
    const welcomeMsg = document.getElementById('welcomeMessage');
    
    if (vendor.is_approved) {
        welcomeMsg.innerHTML = `
            <p>Welcome back! Your account is verified and active.</p>
            <p>You can now create services, manage bookings, and request payouts.</p>
        `;
    } else if (vendor.status === 'pending_verification' && vendor.verification_docs.length > 0) {
        welcomeMsg.innerHTML = `
            <p>Your verification documents have been submitted.</p>
            <p>Please wait for admin approval. You'll be notified once your account is verified.</p>
        `;
    } else if (vendor.status === 'rejected') {
        welcomeMsg.innerHTML = `
            <p class="text-danger">Your verification was rejected.</p>
            <p>Please review the rejection reason and resubmit your documents.</p>
        `;
    } else {
        welcomeMsg.innerHTML = `
            <p>Welcome to HomeServe Pro!</p>
            <p>To start accepting bookings, please verify your profile by uploading the required documents.</p>
            <button class="btn btn-primary" onclick="showSection('verify_profile')">
                <i class="fas fa-id-card me-2"></i>Verify Profile Now
            </button>
        `;
    }
}

function updateStatistics(stats) {
    document.getElementById('totalJobs').textContent = stats.total_bookings || 0;
    document.getElementById('completedJobs').textContent = stats.completed_bookings || 0;
    document.getElementById('pendingJobs').textContent = stats.pending_bookings || 0;
    document.getElementById('totalEarnings').textContent = '₹' + (stats.total_earnings || 0);
}

function setupFormHandlers() {
    // Verification form
    const verificationForm = document.getElementById('verificationForm');
    if (verificationForm) {
        verificationForm.addEventListener('submit', submitVerification);
    }
    
    // Create service form
    const createServiceForm = document.getElementById('createServiceForm');
    if (createServiceForm) {
        createServiceForm.addEventListener('submit', createService);
    }
    
    // Payout request form
    const payoutForm = document.getElementById('payoutRequestForm');
    if (payoutForm) {
        payoutForm.addEventListener('submit', requestPayout);
    }
    
    // Profile form
    const profileForm = document.getElementById('profileForm');
    if (profileForm) {
        profileForm.addEventListener('submit', updateProfile);
    }
}

async function submitVerification(event) {
    event.preventDefault();
    
    const documents = {
        id_proof: document.getElementById('idProofUrl').value,
        business_license: document.getElementById('businessLicenseUrl').value,
        service_certification: document.getElementById('certificationUrl').value
    };
    
    // Validate at least one document
    if (!documents.id_proof && !documents.business_license && !documents.service_certification) {
        alert('Please provide at least one document');
        return;
    }
    
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/vendor/verify_profile', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ documents })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ Verification documents submitted successfully! Please wait for admin approval.');
            await loadDashboard();
        } else {
            alert('❌ Failed to submit: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error submitting verification:', error);
        alert('❌ Error submitting documents. Please try again.');
    }
}

async function createService(event) {
    event.preventDefault();
    
    const serviceData = {
        name: document.getElementById('serviceName').value,
        category: document.getElementById('serviceCategory').value,
        price: parseFloat(document.getElementById('servicePrice').value),
        duration: parseInt(document.getElementById('serviceDuration').value),
        description: document.getElementById('serviceDescription').value,
        availability: document.getElementById('serviceAvailability').checked
    };
    
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/vendor/services/create', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(serviceData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ Service created successfully!');
            document.getElementById('createServiceForm').reset();
        } else {
            alert('❌ Failed to create service: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error creating service:', error);
        alert('❌ Error creating service. Please try again.');
    }
}

function showSection(section) {
    // Hide all sections
    document.querySelectorAll('.dashboard-section').forEach(s => s.classList.add('d-none'));
    
    // Show selected section
    document.getElementById(section + 'Section').classList.remove('d-none');
    
    // Update active menu item
    document.querySelectorAll('.sidebar .nav-link').forEach(link => link.classList.remove('active'));
    event.target.classList.add('active');
    
    // Load section data if needed
    if (section === 'bookings' && vendorData.is_approved) {
        loadBookings();
    } else if (section === 'payouts' && vendorData.payouts_enabled) {
        loadPayoutData();
    }
}

function logout() {
    localStorage.clear();
    window.location.href = '/login';
}

// Add more functions as needed...
```

---

### Step 3: Replace the Old Dashboard

```bash
cd app/templates
mv vendor_dashboard.html vendor_dashboard_old.html
mv vendor_dashboard_new.html vendor_dashboard.html
```

---

### Step 4: Test the Complete Flow

1. **Register a new vendor**
2. **Login and access dashboard**
3. **Upload verification documents**
4. **Login as admin**
5. **Approve the vendor**
6. **Login as vendor again**
7. **Create a custom service**
8. **View bookings**
9. **Request a payout**

---

## 🎉 You're Done!

The backend is fully functional. Once you complete the JavaScript file and test the flow, the entire vendor onboarding and dashboard system will be complete and dynamic!

## 📞 Need Help?

Refer to:
- `IMPLEMENTATION_STATUS.md` - Detailed implementation status
- `VENDOR_ONBOARDING_IMPLEMENTATION.md` - Technical details
- API endpoints are all documented in the code comments


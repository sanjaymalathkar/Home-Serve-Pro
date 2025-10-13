# Vendor Onboarding and Dashboard Implementation Summary

## ✅ Completed Backend Changes

### 1. Vendor Model Updates (`app/models/vendor.py`)
- ✅ Added new status constants:
  - `STATUS_PENDING_VERIFICATION = 'pending_verification'`
  - `STATUS_ACTIVE = 'active'`
- ✅ Added new fields to vendor model:
  - `is_approved` (boolean) - Whether vendor is approved by admin
  - `documents_verified` (boolean) - Whether documents are verified
  - `payouts_enabled` (boolean) - Whether payouts are enabled
  - `verification_docs` (array) - Array of uploaded verification documents
- ✅ Updated `to_dict()` method to include all new fields

### 2. Vendor API Endpoints (`app/routes/vendor.py`)

#### ✅ POST `/api/vendor/verify_profile`
- Accepts verification documents (ID proof, business license, service certification)
- Updates vendor status to `pending_verification`
- Creates admin verification request in `admin_verification_requests` collection
- Sends notification to admins

#### ✅ POST `/api/vendor/services/create`
- Allows approved vendors to create custom services
- Validates vendor approval status
- Stores custom service with name, category, price, duration, description, availability
- Logs service creation in audit log

#### ✅ GET `/api/vendor/dashboard`
- Enhanced to return new status flags:
  - `is_approved`
  - `documents_verified`
  - `payouts_enabled`
  - `verification_docs`
  - `rejection_reason`
  - `bank_details`

### 3. Admin Approval Endpoints (`app/routes/onboard_manager.py`)

#### ✅ GET `/api/onboard_manager/vendor_verification_requests`
- Lists all pending vendor verification requests
- Returns vendor details with uploaded documents
- Paginated results

#### ✅ POST `/api/onboard_manager/vendors/<vendor_id>/approve`
- Updated to set all approval flags:
  - `onboarding_status` → `active`
  - `is_approved` → `true`
  - `documents_verified` → `true`
  - `payouts_enabled` → `true`
- Clears rejection reason
- Sends approval notification to vendor

#### ✅ POST `/api/onboard_manager/vendors/<vendor_id>/reject`
- Updated to set rejection flags:
  - `onboarding_status` → `rejected`
  - `is_approved` → `false`
  - `documents_verified` → `false`
  - `payouts_enabled` → `false`
  - `rejection_reason` → provided reason
- Sends rejection notification to vendor

### 4. Auth Registration Flow (`app/routes/auth.py`)
- ✅ Updated vendor registration to set initial status as `pending_verification`
- ✅ Sets all approval flags to `false` by default
- ✅ Vendor can access dashboard immediately after registration

## 🚧 Frontend Implementation Required

### Vendor Dashboard HTML (`app/templates/vendor_dashboard.html`)

The dashboard needs to be created with the following dynamic sections:

#### 1. **Verify Profile Section**
- Shows verification status badge:
  - ⏳ "Pending Admin Approval" (yellow) - when status is `pending_verification`
  - ✅ "Verified" (green) - when `documents_verified` is true
  - ❌ "Rejected" (red) - when status is `rejected`
- Document upload form with fields:
  - ID Proof (required)
  - Business License (optional)
  - Service Certification (optional)
- Shows rejection reason if rejected
- **Visibility**: Always visible

#### 2. **Create Service Section**
- Form to create custom services:
  - Service Name
  - Category (dropdown)
  - Price (₹)
  - Duration (minutes)
  - Description
  - Availability toggle
- List of created custom services
- **Visibility**: Only when `is_approved === true`

#### 3. **Get Service Bookings Section**
- Displays all bookings assigned to vendor
- Filter tabs: All, Pending, Accepted, In Progress, Completed
- Booking cards with action buttons
- **Visibility**: Only when `is_approved === true`

#### 4. **Secure Payouts Section**
- Shows earnings summary:
  - Total Earnings
  - Available Balance
  - Total Payouts
- Bank details display
- Payout request form
- **Visibility**: 
  - Shows "Payouts will be enabled after verification approval" when `payouts_enabled === false`
  - Shows full payout interface when `payouts_enabled === true`

### JavaScript Logic Required (`static/js/vendor_dashboard.js`)

```javascript
async function loadDashboard() {
    const response = await fetch('/api/vendor/dashboard', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    
    if (data.success) {
        vendorData = data.vendor_info;
        
        // Update status badge
        updateStatusBadge(vendorData.status);
        
        // Show/hide sections based on status
        updateDashboardVisibility(vendorData);
        
        // Load statistics
        updateStatistics(data.statistics);
        
        // Load bookings if approved
        if (vendorData.is_approved) {
            await loadBookings();
        }
    }
}

function updateDashboardVisibility(vendor) {
    // Verify Profile - always visible
    document.getElementById('menu-verify-profile').style.display = 'block';
    
    // Create Service - only if approved
    document.getElementById('menu-create-service').style.display = 
        vendor.is_approved ? 'block' : 'none';
    
    // Bookings - only if approved
    document.getElementById('menu-bookings').style.display = 
        vendor.is_approved ? 'block' : 'none';
    
    // Payouts - always visible but content changes
    document.getElementById('menu-payouts').style.display = 'block';
    
    // Update payout section content
    if (vendor.payouts_enabled) {
        document.getElementById('payoutsDisabled').classList.add('d-none');
        document.getElementById('payoutsEnabled').classList.remove('d-none');
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
    
    if (vendor.status === 'pending_verification') {
        statusEl.innerHTML = '<span class="badge bg-warning">⏳ Pending Admin Approval</span>';
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

async function submitVerification(event) {
    event.preventDefault();
    
    const documents = {
        id_proof: document.getElementById('idProofUrl').value,
        business_license: document.getElementById('businessLicenseUrl').value,
        service_certification: document.getElementById('certificationUrl').value
    };
    
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
        alert('✅ Verification documents submitted successfully!');
        await loadDashboard();
    } else {
        alert('❌ Failed to submit: ' + data.message);
    }
}

async function createService(event) {
    event.preventDefault();
    
    const serviceData = {
        name: document.getElementById('serviceName').value,
        category: document.getElementById('serviceCategory').value,
        price: document.getElementById('servicePrice').value,
        duration: document.getElementById('serviceDuration').value,
        description: document.getElementById('serviceDescription').value,
        availability: document.getElementById('serviceAvailability').checked
    };
    
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
        alert('❌ Failed to create service: ' + data.message);
    }
}
```

## 📊 Dashboard Flow Logic

### Vendor Status → Dashboard Modules Visible

| Vendor Status | Verify Profile | Create Service | Bookings | Payouts |
|--------------|----------------|----------------|----------|---------|
| `pending_verification` | ✅ Show form | ❌ Hidden | ❌ Hidden | ⚠️ Disabled message |
| `pending_verification` (submitted) | ✅ Show "Pending" | ❌ Hidden | ❌ Hidden | ⚠️ Disabled message |
| `active` (approved) | ✅ Show "Verified" | ✅ Enabled | ✅ Enabled | ✅ Enabled |
| `rejected` | ✅ Show "Rejected" + reason | ❌ Hidden | ❌ Hidden | ⚠️ Disabled message |

## 🔄 Complete User Flow

1. **Vendor Registration**
   - Vendor registers → Status set to `pending_verification`
   - Redirected to vendor dashboard immediately

2. **Dashboard Access (Not Verified)**
   - Sees "Verify Profile" section
   - Can upload documents
   - Other sections hidden/disabled

3. **Document Submission**
   - Vendor uploads ID proof, business license, certification
   - Status remains `pending_verification`
   - Admin notification created

4. **Admin Review**
   - Admin sees verification request in admin dashboard
   - Can view uploaded documents
   - Approves or rejects

5. **After Approval**
   - Status → `active`
   - `is_approved` → `true`
   - `documents_verified` → `true`
   - `payouts_enabled` → `true`
   - All dashboard sections become available

6. **After Rejection**
   - Status → `rejected`
   - Rejection reason displayed
   - Vendor can resubmit documents

## 🧪 Testing Checklist

- [ ] Vendor can register and access dashboard immediately
- [ ] Verify Profile section is visible for all vendors
- [ ] Document submission creates admin verification request
- [ ] Admin can see pending verification requests
- [ ] Admin approval sets all flags correctly
- [ ] Admin rejection shows reason to vendor
- [ ] Create Service section only visible when approved
- [ ] Bookings section only visible when approved
- [ ] Payouts section shows correct message based on status
- [ ] Approved vendors can create custom services
- [ ] Approved vendors can see their bookings
- [ ] Approved vendors can request payouts

## 📝 Next Steps

1. Complete the vendor dashboard HTML file with all sections
2. Create the JavaScript file with all event handlers
3. Test the complete flow end-to-end
4. Add admin dashboard section for verification requests
5. Add file upload functionality for documents (currently using URLs)


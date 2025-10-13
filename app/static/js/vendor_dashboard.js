/**
 * Vendor Dashboard JavaScript
 * Handles all vendor dashboard functionality including verification, services, bookings, and payouts
 */

let currentUser = null;
let vendorData = null;
let allBookings = [];
let currentFilter = 'all';

document.addEventListener('DOMContentLoaded', async () => {
    console.log('Vendor Dashboard JS loaded');

    const token = localStorage.getItem('access_token');
    if (!token) {
        console.log('No token found, redirecting to login');
        window.location.href = '/login';
        return;
    }

    try {
        currentUser = JSON.parse(localStorage.getItem('user') || '{}');
        const userNameEl = document.getElementById('userName');
        if (userNameEl) {
            userNameEl.textContent = currentUser.name || currentUser.email;
        }

        // Load dashboard data
        await loadDashboard();

        // Setup form handlers
        setupFormHandlers();

        console.log('Dashboard initialization complete');
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        alert('Error loading dashboard. Please refresh the page.');
    }
});

async function loadDashboard() {
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/vendor/dashboard', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Dashboard data:', data);

        if (data.success) {
            const payload = data.data || {};
            vendorData = payload.vendor_info || data.vendor_info || null;

            if (!vendorData) {
                throw new Error('Malformed response: missing vendor_info');
            }

            // Update status badge
            updateStatusBadge(vendorData.status, vendorData.documents_verified);

            // Show/hide sections based on status
            updateDashboardVisibility(vendorData);

            // Load statistics
            updateStatistics(payload.statistics || data.statistics || {});

            // Update welcome message
            updateWelcomeMessage(vendorData);

            // Load bookings if approved
            if (vendorData.is_approved) {
                await loadBookings();
            }
        } else {
            console.error('Dashboard load failed:', data.message);
            alert('Failed to load dashboard: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
        alert('Failed to load dashboard. Please refresh the page. Error: ' + error.message);
    }
}

function updateStatusBadge(status, verified) {
    const badge = document.getElementById('statusBadge');
    if (!badge) {
        console.warn('Status badge element not found');
        return;
    }

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
        badge.textContent = status || 'Unknown';
    }
}

function updateDashboardVisibility(vendor) {
    // Verify Profile - always visible
    document.getElementById('menu-verify-profile').style.display = 'block';
    
    // Create Service - only if approved
    const createServiceMenu = document.getElementById('menu-create-service');
    if (createServiceMenu) {
        createServiceMenu.style.display = vendor.is_approved ? 'block' : 'none';
    }
    
    // Bookings - only if approved
    const bookingsMenu = document.getElementById('menu-bookings');
    if (bookingsMenu) {
        bookingsMenu.style.display = vendor.is_approved ? 'block' : 'none';
    }
    
    // Payouts - always visible but content changes
    const payoutsDisabled = document.getElementById('payoutsDisabled');
    const payoutsEnabled = document.getElementById('payoutsEnabled');
    
    if (vendor.payouts_enabled) {
        if (payoutsDisabled) payoutsDisabled.classList.add('d-none');
        if (payoutsEnabled) {
            payoutsEnabled.classList.remove('d-none');
            loadPayoutData();
        }
    } else {
        if (payoutsDisabled) payoutsDisabled.classList.remove('d-none');
        if (payoutsEnabled) payoutsEnabled.classList.add('d-none');
    }
    
    // Update verification status
    updateVerificationStatus(vendor);
}

function updateVerificationStatus(vendor) {
    const statusEl = document.getElementById('verificationStatus');
    const rejectionEl = document.getElementById('rejectionReason');
    
    if (!statusEl) return;
    
    if (vendor.status === 'pending_verification' && vendor.verification_docs && vendor.verification_docs.length > 0) {
        statusEl.innerHTML = '<span class="badge bg-warning">⏳ Pending Admin Approval</span>';
    } else if (vendor.status === 'pending_verification') {
        statusEl.innerHTML = '<span class="badge bg-info">📝 Please upload documents</span>';
    } else if (vendor.documents_verified) {
        statusEl.innerHTML = '<span class="badge bg-success">✅ Verified</span>';
    } else if (vendor.status === 'rejected') {
        statusEl.innerHTML = '<span class="badge bg-danger">❌ Rejected</span>';
        if (vendor.rejection_reason && rejectionEl) {
            document.getElementById('rejectionText').textContent = vendor.rejection_reason;
            rejectionEl.classList.remove('d-none');
        }
    }
}

function updateWelcomeMessage(vendor) {
    const welcomeMsg = document.getElementById('welcomeMessage');
    if (!welcomeMsg) {
        console.warn('Welcome message element not found');
        return;
    }

    if (vendor.is_approved) {
        welcomeMsg.innerHTML = `
            <p>✅ Welcome back! Your account is verified and active.</p>
            <p>You can now create services, manage bookings, and request payouts.</p>
            <div class="mt-3">
                <button class="btn btn-primary me-2" onclick="showSection('create_service', event)">
                    <i class="fas fa-plus-circle me-2"></i>Create Service
                </button>
                <button class="btn btn-success" onclick="showSection('bookings', event)">
                    <i class="fas fa-briefcase me-2"></i>View Bookings
                </button>
            </div>
        `;
    } else if (vendor.status === 'pending_verification' && vendor.verification_docs && vendor.verification_docs.length > 0) {
        welcomeMsg.innerHTML = `
            <p>⏳ Your verification documents have been submitted.</p>
            <p>Please wait for admin approval. You'll be notified once your account is verified.</p>
        `;
    } else if (vendor.status === 'rejected') {
        welcomeMsg.innerHTML = `
            <p class="text-danger">❌ Your verification was rejected.</p>
            <p>Please review the rejection reason and resubmit your documents.</p>
            <button class="btn btn-warning mt-2" onclick="showSection('verify_profile', event)">
                <i class="fas fa-redo me-2"></i>Resubmit Documents
            </button>
        `;
    } else {
        welcomeMsg.innerHTML = `
            <p>👋 Welcome to HomeServe Pro!</p>
            <p>To start accepting bookings, please verify your profile by uploading the required documents.</p>
            <button class="btn btn-primary mt-2" onclick="showSection('verify_profile', event)">
                <i class="fas fa-id-card me-2"></i>Verify Profile Now
            </button>
        `;
    }
}

function updateStatistics(stats) {
    const totalJobs = document.getElementById('totalJobs');
    const completedJobs = document.getElementById('completedJobs');
    const pendingJobs = document.getElementById('pendingJobs');
    const totalEarnings = document.getElementById('totalEarnings');

    if (totalJobs) totalJobs.textContent = stats.total_bookings || 0;
    if (completedJobs) completedJobs.textContent = stats.completed_bookings || 0;
    if (pendingJobs) pendingJobs.textContent = stats.pending_bookings || 0;
    if (totalEarnings) totalEarnings.textContent = '₹' + (stats.total_earnings || 0);
}

function setupFormHandlers() {
    // Verification form
    const verificationForm = document.getElementById('verificationForm');
    if (verificationForm) {
        verificationForm.addEventListener('submit', submitVerification);

        // Document upload inputs
        const idProofFile = document.getElementById('idProofFile');
        if (idProofFile) {
            idProofFile.addEventListener('change', () => handleDocUpload('id_proof', 'idProofFile', 'idProofUrl', 'idProofUploaded'));
        }
        const businessLicenseFile = document.getElementById('businessLicenseFile');
        if (businessLicenseFile) {
            businessLicenseFile.addEventListener('change', () => handleDocUpload('business_license', 'businessLicenseFile', 'businessLicenseUrl', 'businessLicenseUploaded'));
        }
        const certificationFile = document.getElementById('certificationFile');
        if (certificationFile) {
            certificationFile.addEventListener('change', () => handleDocUpload('service_certification', 'certificationFile', 'certificationUrl', 'certificationUploaded'));
        }
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

async function handleDocUpload(docType, fileInputId, urlHiddenId, uploadedBadgeId) {
    const fileInput = document.getElementById(fileInputId);
    const urlHidden = document.getElementById(urlHiddenId);
    const uploadedBadge = document.getElementById(uploadedBadgeId);
    if (!fileInput || fileInput.files.length === 0) return;

    const file = fileInput.files[0];
    if (file.size > 16 * 1024 * 1024) {
        alert('File too large. Max 16MB');
        fileInput.value = '';
        return;
    }

    try {
        const token = localStorage.getItem('access_token');
        const formData = new FormData();
        formData.append('document', file);
        formData.append('doc_type', docType);

        const res = await fetch('/api/vendor/verification/upload', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.message || 'Upload failed');
        }
        const url = data.document?.url || '';
        urlHidden.value = url;
        if (uploadedBadge) uploadedBadge.classList.remove('d-none');
    } catch (err) {
        console.error('Upload error:', err);
        alert('Failed to upload document: ' + err.message);
    }
}

async function ensureUploaded(docType, fileInputId, urlHiddenId, uploadedBadgeId) {
    const urlHidden = document.getElementById(urlHiddenId);
    if (urlHidden && urlHidden.value) return; // already uploaded
    const fileInput = document.getElementById(fileInputId);
    if (fileInput && fileInput.files && fileInput.files.length > 0) {
        await handleDocUpload(docType, fileInputId, urlHiddenId, uploadedBadgeId);
    }
}

async function submitVerification(event) {
    event.preventDefault();

    // Fallback: if user selected files but upload hasn't run yet, upload them now
    await Promise.all([
        ensureUploaded('id_proof', 'idProofFile', 'idProofUrl', 'idProofUploaded'),
        ensureUploaded('business_license', 'businessLicenseFile', 'businessLicenseUrl', 'businessLicenseUploaded'),
        ensureUploaded('service_certification', 'certificationFile', 'certificationUrl', 'certificationUploaded')
    ]);

    const idProof = document.getElementById('idProofUrl').value.trim();
    const businessLicense = document.getElementById('businessLicenseUrl').value.trim();
    const certification = document.getElementById('certificationUrl').value.trim();

    const documents = {};
    if (idProof) documents.id_proof = idProof;
    if (businessLicense) documents.business_license = businessLicense;
    if (certification) documents.service_certification = certification;

    // Validate at least one document
    if (Object.keys(documents).length === 0) {
        alert('⚠️ Please select or upload at least one document');
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
            document.getElementById('verificationForm').reset();
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
            // Optionally reload services list
        } else {
            alert('❌ Failed to create service: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error creating service:', error);
        alert('❌ Error creating service. Please try again.');
    }
}

async function loadBookings() {
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/vendor/bookings', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();

        console.log('Bookings response:', data);

        if (data.success) {
            allBookings = data.data?.bookings || data.bookings || [];
            console.log('Loaded bookings:', allBookings.length);
            displayBookings(allBookings);
        } else {
            console.error('Failed to load bookings:', data.message);
            displayBookings([]);
        }
    } catch (error) {
        console.error('Error loading bookings:', error);
        displayBookings([]);
    }
}

function displayBookings(bookings) {
    const bookingsList = document.getElementById('bookingsList');
    if (!bookingsList) return;

    if (bookings.length === 0) {
        bookingsList.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No bookings available at the moment.
            </div>
        `;
        return;
    }

    let html = '<div class="row g-3">';
    bookings.forEach(booking => {
        const statusBadge = getStatusBadge(booking.status);
        const bookingDate = new Date(booking.service_date || booking.created_at).toLocaleDateString();
        const bookingTime = booking.service_time || new Date(booking.created_at).toLocaleTimeString();

        html += `
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h5 class="mb-0">${booking.service_name || booking.service_type || 'Service'}</h5>
                            ${statusBadge}
                        </div>
                        <p class="text-muted small mb-2">
                            <i class="fas fa-calendar me-1"></i>${bookingDate} at ${bookingTime}
                        </p>
                        <p class="text-muted small mb-2">
                            <i class="fas fa-map-marker-alt me-1"></i>${booking.address || booking.pincode || 'N/A'}
                        </p>
                        <p class="text-muted small mb-2">
                            <i class="fas fa-user me-1"></i>Customer: ${booking.customer_name || booking.user_name || 'N/A'}
                        </p>
                        <p class="mb-2">
                            <strong>Amount:</strong> ₹${booking.amount || booking.total_amount || 0}
                        </p>
                        ${booking.notes ? `<p class=\"text-muted small mb-2\"><i class=\"fas fa-sticky-note me-1\"></i>${booking.notes}</p>` : ''}
                        <div class="mt-2">
                            ${booking.status === 'pending' ? `
                                <button class="btn btn-sm btn-success me-1" onclick="acceptBooking('${booking.id || booking._id}')">
                                    <i class="fas fa-check me-1"></i>Accept
                                </button>
                                <button class="btn btn-sm btn-danger" onclick="rejectBooking('${booking.id || booking._id}')">
                                    <i class="fas fa-times me-1"></i>Reject
                                </button>
                            ` : ''}
                            ${booking.status === 'accepted' ? `
                                <button class="btn btn-sm btn-primary" onclick="startBooking('${booking.id || booking._id}')">
                                    <i class="fas fa-play me-1"></i>Start Job
                                </button>
                            ` : ''}
                            ${booking.status === 'in_progress' ? `
                                <button class="btn btn-sm btn-success" onclick="completeBooking('${booking.id || booking._id}')">
                                    <i class="fas fa-check-circle me-1"></i>Complete
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    bookingsList.innerHTML = html;
}

function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge bg-warning">Pending</span>',
        'accepted': '<span class="badge bg-info">Accepted</span>',
        'in_progress': '<span class="badge bg-primary">In Progress</span>',
        'completed': '<span class="badge bg-success">Completed</span>',
        'cancelled': '<span class="badge bg-danger">Cancelled</span>'
    };
    return badges[status] || '<span class="badge bg-secondary">Unknown</span>';
}

function filterBookings(status, evt) {
    if (evt) evt.preventDefault();
    currentFilter = status;

    // Update active tab (ensure we add .active to the <a> element)
    document.querySelectorAll('.nav-tabs .nav-link').forEach(link => link.classList.remove('active'));
    if (evt) {
        const linkEl = evt.target?.closest('.nav-link');
        if (linkEl) linkEl.classList.add('active');
    }

    // Filter bookings
    let filteredBookings = allBookings;
    if (status !== 'all') {
        filteredBookings = allBookings.filter(b => b.status === status);
    }

    displayBookings(filteredBookings);
}

async function loadPayoutData() {
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/vendor/earnings', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();

        if (data.success && data.summary) {
            const summary = data.summary;
            document.getElementById('payoutTotalEarnings').textContent = '₹' + (summary.total_earnings || 0);
            document.getElementById('payoutAvailableBalance').textContent = '₹' + (summary.available_balance || 0);
            document.getElementById('payoutTotalPayouts').textContent = '₹' + (summary.total_payouts || 0);

            // Display bank details
            if (vendorData.bank_details && Object.keys(vendorData.bank_details).length > 0) {
                const bankDetails = vendorData.bank_details;
                document.getElementById('bankDetailsDisplay').innerHTML = `
                    <p><strong>Account Holder:</strong> ${bankDetails.account_holder_name || 'N/A'}</p>
                    <p><strong>Account Number:</strong> ${bankDetails.account_number ? '****' + bankDetails.account_number.slice(-4) : 'N/A'}</p>
                    <p><strong>IFSC Code:</strong> ${bankDetails.ifsc_code || 'N/A'}</p>
                    <p><strong>Bank Name:</strong> ${bankDetails.bank_name || 'N/A'}</p>
                `;
            }
        }
    } catch (error) {
        console.error('Error loading payout data:', error);
    }
}

async function requestPayout(event) {
    event.preventDefault();

    const amount = parseFloat(document.getElementById('payoutAmount').value);

    if (amount < 500) {
        alert('⚠️ Minimum payout amount is ₹500');
        return;
    }

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/vendor/payouts/request', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ amount, method: 'bank_transfer' })
        });

        const data = await response.json();

        if (data.success) {
            alert('✅ Payout request submitted successfully!');
            document.getElementById('payoutRequestForm').reset();
            await loadPayoutData();
        } else {
            alert('❌ Failed to request payout: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error requesting payout:', error);
        alert('❌ Error requesting payout. Please try again.');
    }
}

async function updateProfile(event) {
    event.preventDefault();

    const profileData = {
        name: document.getElementById('profileName').value,
        phone: document.getElementById('profilePhone').value
    };

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/profile', {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(profileData)
        });

        const data = await response.json();

        if (data.success) {
            alert('✅ Profile updated successfully!');
            currentUser = { ...currentUser, ...profileData };
            localStorage.setItem('user', JSON.stringify(currentUser));
            document.getElementById('userName').textContent = currentUser.name;
        } else {
            alert('❌ Failed to update profile: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error updating profile:', error);
        alert('❌ Error updating profile. Please try again.');
    }
}

function showSection(section, evt) {
    if (evt) evt.preventDefault();

    console.log('Showing section:', section);

    // Hide all sections
    document.querySelectorAll('.dashboard-section').forEach(s => s.classList.add('d-none'));

    // Show selected section
    const sectionEl = document.getElementById(section + 'Section');
    if (sectionEl) {
        sectionEl.classList.remove('d-none');
        console.log('Section displayed:', section);
    } else {
        console.error('Section not found:', section + 'Section');
    }

    // Update active menu item (ensure we add .active to the <a> element, not inner <i> or text)
    document.querySelectorAll('.sidebar .nav-link').forEach(link => link.classList.remove('active'));
    if (evt) {
        const linkEl = evt.target?.closest('.nav-link');
        if (linkEl) linkEl.classList.add('active');
    }

    // Load section data if needed
    if (section === 'bookings' && vendorData && vendorData.is_approved) {
        loadBookings();
    } else if (section === 'payouts' && vendorData && vendorData.payouts_enabled) {
        loadPayoutData();
    } else if (section === 'profile') {
        loadProfileData();
    }
}

function loadProfileData() {
    if (vendorData) {
        document.getElementById('profileName').value = vendorData.name || '';
        document.getElementById('profileEmail').value = vendorData.email || currentUser.email || '';
        document.getElementById('profilePhone').value = vendorData.phone || '';
    }
}

async function acceptBooking(bookingId) {
    if (!confirm('Accept this booking?')) return;

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/vendor/bookings/${bookingId}/accept`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();

        if (data.success) {
            alert('✅ Booking accepted successfully!');
            await loadBookings();
        } else {
            alert('❌ Failed to accept booking: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error accepting booking:', error);
        alert('❌ Error accepting booking. Please try again.');
    }
}

async function rejectBooking(bookingId) {
    const reason = prompt('Please enter rejection reason:');
    if (!reason) return;

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/vendor/bookings/${bookingId}/reject`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ reason })
        });
        const data = await response.json();

        if (data.success) {
            alert('✅ Booking rejected successfully!');
            await loadBookings();
        } else {
            alert('❌ Failed to reject booking: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error rejecting booking:', error);
        alert('❌ Error rejecting booking. Please try again.');
    }
}

async function startBooking(bookingId) {
    if (!confirm('Start this job?')) return;

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/vendor/bookings/${bookingId}/start`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();

        if (data.success) {
            alert('✅ Job started successfully!');
            await loadBookings();
        } else {
            alert('❌ Failed to start job: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error starting job:', error);
        alert('❌ Error starting job. Please try again.');
    }
}

async function completeBooking(bookingId) {
    if (!confirm('Mark this job as complete?')) return;

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/vendor/bookings/${bookingId}/complete`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();

        if (data.success) {
            alert('✅ Job completed successfully!');
            await loadBookings();
            await loadDashboard(); // Refresh dashboard to update earnings
        } else {
            alert('❌ Failed to complete job: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error completing job:', error);
        alert('❌ Error completing job. Please try again.');
    }
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        localStorage.clear();
        window.location.href = '/login';
    }
}

// Make functions globally accessible
window.showSection = showSection;
window.filterBookings = filterBookings;
window.acceptBooking = acceptBooking;
window.rejectBooking = rejectBooking;
window.startBooking = startBooking;
window.completeBooking = completeBooking;
window.logout = logout;


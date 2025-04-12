document.addEventListener('DOMContentLoaded', function() {
    // Initialize datepickers
    initializeDatePickers();
    
    // Setup form validation
    setupFormValidation();
    
    // Setup progress tracking for scraping
    setupProgressTracking();
    
    // Setup export form handling
    setupExportForm();
    
    // Setup card/table view toggle
    setupViewToggle();
});

function initializeDatePickers() {
    // Get the date inputs
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    
    if (startDateInput && endDateInput) {
        // Set default dates (last 30 days)
        const today = new Date();
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(today.getDate() - 30);
        
        // Format dates for input fields
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        // Set default values if not already set
        if (!startDateInput.value) {
            startDateInput.value = formatDate(thirtyDaysAgo);
        }
        
        if (!endDateInput.value) {
            endDateInput.value = formatDate(today);
        }
        
        // Add validation to ensure end date is not before start date
        endDateInput.addEventListener('change', function() {
            if (startDateInput.value && this.value && this.value < startDateInput.value) {
                alert('End date cannot be before start date');
                this.value = startDateInput.value;
            }
        });
        
        startDateInput.addEventListener('change', function() {
            if (endDateInput.value && this.value && this.value > endDateInput.value) {
                endDateInput.value = this.value;
            }
        });
    }
}

function setupFormValidation() {
    const scrapeForm = document.getElementById('scrape-form');
    
    if (scrapeForm) {
        scrapeForm.addEventListener('submit', function(event) {
            const channelUrl = document.getElementById('channel-url').value.trim();
            const apiKey = document.getElementById('api-key').value.trim();
            
            if (!channelUrl) {
                event.preventDefault();
                alert('Please enter a YouTube channel URL');
                return false;
            }
            
            if (!apiKey) {
                event.preventDefault();
                alert('Please enter your YouTube API key');
                return false;
            }
            
            // Simple URL validation
            if (!isValidYouTubeUrl(channelUrl)) {
                event.preventDefault();
                alert('Please enter a valid YouTube channel URL');
                return false;
            }
            
            // Show loading indicator
            showLoadingIndicator();
            
            // Start progress tracking
            startProgressTracking();
        });
    }
}

function isValidYouTubeUrl(url) {
    // Very basic validation - just check if it contains youtube.com or youtu.be
    return url.includes('youtube.com') || url.includes('youtu.be');
}

function showLoadingIndicator() {
    const submitButton = document.querySelector('#scrape-form button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    }
    
    // Show progress container
    const progressContainer = document.getElementById('progress-container');
    if (progressContainer) {
        progressContainer.classList.remove('d-none');
    }
}

function setupProgressTracking() {
    // Initial setup for the progress bar
    const progressBar = document.getElementById('scraping-progress');
    const progressStatus = document.getElementById('progress-status');
    
    if (progressBar && progressStatus) {
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', '0');
        progressStatus.textContent = 'Waiting to start...';
    }
}

function startProgressTracking() {
    // Start polling for progress updates
    const progressInterval = setInterval(checkProgress, 1000);
    
    // Store interval ID in sessionStorage to clear it if the page is reloaded
    sessionStorage.setItem('progressInterval', progressInterval);
    
    function checkProgress() {
        fetch('/progress')
            .then(response => response.json())
            .then(data => {
                updateProgressUI(data);
                
                // If progress is complete, stop polling
                if (data.progress >= 100) {
                    clearInterval(progressInterval);
                    sessionStorage.removeItem('progressInterval');
                }
            })
            .catch(error => {
                console.error('Error checking progress:', error);
            });
    }
}

function updateProgressUI(data) {
    const progressBar = document.getElementById('scraping-progress');
    const progressStatus = document.getElementById('progress-status');
    
    if (progressBar && progressStatus) {
        progressBar.style.width = `${data.progress}%`;
        progressBar.setAttribute('aria-valuenow', data.progress);
        progressStatus.textContent = data.status;
    }
}

function setupExportForm() {
    const exportForm = document.getElementById('export-form');
    
    if (exportForm) {
        exportForm.addEventListener('submit', function() {
            const exportButton = document.querySelector('#export-form button[type="submit"]');
            if (exportButton) {
                exportButton.disabled = true;
                exportButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Exporting...';
                
                // Re-enable after a delay (in case the download takes time)
                setTimeout(() => {
                    exportButton.disabled = false;
                    exportButton.innerHTML = 'Export Data';
                }, 3000);
            }
        });
    }
}

// Clear any existing progress interval when the page loads
document.addEventListener('DOMContentLoaded', function() {
    const existingInterval = sessionStorage.getItem('progressInterval');
    if (existingInterval) {
        clearInterval(existingInterval);
        sessionStorage.removeItem('progressInterval');
    }
});

// Setup card/table view toggle
function setupViewToggle() {
    const cardViewBtn = document.getElementById('cardViewBtn');
    const tableViewBtn = document.getElementById('tableViewBtn');
    const cardView = document.getElementById('cardView');
    const tableView = document.getElementById('tableView');
    
    if (cardViewBtn && tableViewBtn && cardView && tableView) {
        cardViewBtn.addEventListener('click', function() {
            cardView.classList.remove('d-none');
            tableView.classList.add('d-none');
            cardViewBtn.classList.add('active');
            tableViewBtn.classList.remove('active');
        });
        
        tableViewBtn.addEventListener('click', function() {
            cardView.classList.add('d-none');
            tableView.classList.remove('d-none');
            cardViewBtn.classList.remove('active');
            tableViewBtn.classList.add('active');
        });
    }
}

// Add event listener to document ready
document.addEventListener('DOMContentLoaded', function() {
    setupViewToggle();
});

document.addEventListener('DOMContentLoaded', function() {
    setupVideoPlaceholders();
    setupNavigation();
});

function setupVideoPlaceholders() {
    const videoPlaceholders = document.querySelectorAll('.video-placeholder');
    
    videoPlaceholders.forEach(placeholder => {
        placeholder.addEventListener('click', function() {
            const placeholderText = this.querySelector('.placeholder-text').textContent;
            alert(`Video placeholder clicked: ${placeholderText}\nReplace this with your actual video or screenshot.`);
        });
    });
}

function setupNavigation() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
}
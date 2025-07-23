class VideoController {
    constructor() {
        this.videos = new Map();
        this.init();
    }
    
    init() {
        this.setupVideoPlayers();
        this.setupVideoObservers();
        this.bindGlobalEvents();
    }
    
    setupVideoPlayers() {
        const videoElements = document.querySelectorAll('video');
        
        videoElements.forEach((video, index) => {
            const videoId = `video-${index}`;
            video.setAttribute('data-video-id', videoId);
            
            const videoData = {
                element: video,
                id: videoId,
                isPlaying: false,
                hasPlayed: false,
                currentTime: 0,
                duration: 0
            };
            
            this.videos.set(videoId, videoData);
            this.setupVideoEvents(videoData);
            this.setupCustomControls(videoData);
        });
    }
    
    setupVideoEvents(videoData) {
        const { element, id } = videoData;
        
        element.addEventListener('loadstart', () => {
            this.showLoadingState(id);
        });
        
        element.addEventListener('loadedmetadata', () => {
            videoData.duration = element.duration;
            this.hideLoadingState(id);
        });
        
        element.addEventListener('loadeddata', () => {
            this.updateVideoReady(id);
        });
        
        element.addEventListener('play', () => {
            videoData.isPlaying = true;
            videoData.hasPlayed = true;
            this.onVideoPlay(id);
        });
        
        element.addEventListener('pause', () => {
            videoData.isPlaying = false;
            this.onVideoPause(id);
        });
        
        element.addEventListener('ended', () => {
            videoData.isPlaying = false;
            this.onVideoEnd(id);
        });
        
        element.addEventListener('timeupdate', () => {
            videoData.currentTime = element.currentTime;
            this.updateProgress(id);
        });
        
        element.addEventListener('error', (e) => {
            this.handleVideoError(id, e);
        });
        
        element.addEventListener('volumechange', () => {
            this.updateVolumeDisplay(id);
        });
    }
    
    setupCustomControls(videoData) {
        const { element, id } = videoData;
        const container = element.closest('.video-wrapper') || element.parentElement;
        
        const controlsOverlay = document.createElement('div');
        controlsOverlay.className = 'video-controls-overlay';
        controlsOverlay.innerHTML = `
            <div class="video-controls">
                <button class="play-pause-btn" data-video-id="${id}">
                    <svg class="play-icon" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                    <svg class="pause-icon" viewBox="0 0 24 24" style="display: none;">
                        <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                    </svg>
                </button>
                
                <div class="video-progress">
                    <div class="progress-bar" data-video-id="${id}">
                        <div class="progress-fill"></div>
                        <div class="progress-handle"></div>
                    </div>
                    <span class="time-display">0:00 / 0:00</span>
                </div>
                
                <div class="video-volume">
                    <button class="volume-btn" data-video-id="${id}">
                        <svg class="volume-icon" viewBox="0 0 24 24">
                            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
                        </svg>
                    </button>
                    <input type="range" class="volume-slider" min="0" max="1" step="0.1" value="1" data-video-id="${id}">
                </div>
                
                <button class="fullscreen-btn" data-video-id="${id}">
                    <svg viewBox="0 0 24 24">
                        <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                    </svg>
                </button>
            </div>
        `;
        
        container.appendChild(controlsOverlay);
        this.bindControlEvents(id);
    }
    
    bindControlEvents(videoId) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        const container = element.closest('.video-wrapper') || element.parentElement;
        
        // Play/pause button
        const playPauseBtn = container.querySelector('.play-pause-btn');
        playPauseBtn.addEventListener('click', () => {
            this.togglePlayPause(videoId);
        });
        
        // Progress bar
        const progressBar = container.querySelector('.progress-bar');
        progressBar.addEventListener('click', (e) => {
            this.seekToPosition(videoId, e);
        });
        
        // Volume controls
        const volumeBtn = container.querySelector('.volume-btn');
        const volumeSlider = container.querySelector('.volume-slider');
        
        volumeBtn.addEventListener('click', () => {
            this.toggleMute(videoId);
        });
        
        volumeSlider.addEventListener('input', (e) => {
            this.setVolume(videoId, parseFloat(e.target.value));
        });
        
        // Fullscreen button
        const fullscreenBtn = container.querySelector('.fullscreen-btn');
        fullscreenBtn.addEventListener('click', () => {
            this.toggleFullscreen(videoId);
        });
        
        // Keyboard controls
        element.addEventListener('keydown', (e) => {
            this.handleKeyboardControls(videoId, e);
        });
        
        // Hide/show controls on hover
        container.addEventListener('mouseenter', () => {
            container.querySelector('.video-controls-overlay').classList.add('visible');
        });
        
        container.addEventListener('mouseleave', () => {
            container.querySelector('.video-controls-overlay').classList.remove('visible');
        });
    }
    
    togglePlayPause(videoId) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        
        if (element.paused) {
            element.play();
        } else {
            element.pause();
        }
    }
    
    seekToPosition(videoId, event) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        const progressBar = event.currentTarget;
        const rect = progressBar.getBoundingClientRect();
        const clickX = event.clientX - rect.left;
        const percentage = clickX / rect.width;
        const newTime = percentage * element.duration;
        
        element.currentTime = newTime;
    }
    
    setVolume(videoId, volume) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        element.volume = Math.max(0, Math.min(1, volume));
    }
    
    toggleMute(videoId) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        element.muted = !element.muted;
    }
    
    toggleFullscreen(videoId) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        const container = element.closest('.video-wrapper') || element.parentElement;
        
        if (!document.fullscreenElement) {
            container.requestFullscreen().catch(err => {
                console.warn('Could not enter fullscreen:', err);
            });
        } else {
            document.exitFullscreen();
        }
    }
    
    handleKeyboardControls(videoId, event) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        
        switch (event.code) {
            case 'Space':
                event.preventDefault();
                this.togglePlayPause(videoId);
                break;
            case 'ArrowLeft':
                event.preventDefault();
                element.currentTime = Math.max(0, element.currentTime - 10);
                break;
            case 'ArrowRight':
                event.preventDefault();
                element.currentTime = Math.min(element.duration, element.currentTime + 10);
                break;
            case 'ArrowUp':
                event.preventDefault();
                this.setVolume(videoId, element.volume + 0.1);
                break;
            case 'ArrowDown':
                event.preventDefault();
                this.setVolume(videoId, element.volume - 0.1);
                break;
            case 'KeyM':
                event.preventDefault();
                this.toggleMute(videoId);
                break;
            case 'KeyF':
                event.preventDefault();
                this.toggleFullscreen(videoId);
                break;
        }
    }
    
    updateProgress(videoId) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        const container = element.closest('.video-wrapper') || element.parentElement;
        const progressFill = container.querySelector('.progress-fill');
        const timeDisplay = container.querySelector('.time-display');
        
        if (element.duration > 0) {
            const percentage = (element.currentTime / element.duration) * 100;
            progressFill.style.width = `${percentage}%`;
            
            const currentMinutes = Math.floor(element.currentTime / 60);
            const currentSeconds = Math.floor(element.currentTime % 60);
            const durationMinutes = Math.floor(element.duration / 60);
            const durationSeconds = Math.floor(element.duration % 60);
            
            timeDisplay.textContent = 
                `${currentMinutes}:${currentSeconds.toString().padStart(2, '0')} / ` +
                `${durationMinutes}:${durationSeconds.toString().padStart(2, '0')}`;
        }
    }
    
    onVideoPlay(videoId) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        const container = element.closest('.video-wrapper') || element.parentElement;
        const playIcon = container.querySelector('.play-icon');
        const pauseIcon = container.querySelector('.pause-icon');
        
        playIcon.style.display = 'none';
        pauseIcon.style.display = 'block';
        
        // Pause other videos
        this.pauseOtherVideos(videoId);
        
        // Analytics
        this.trackVideoEvent('play', videoId);
    }
    
    onVideoPause(videoId) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        const container = element.closest('.video-wrapper') || element.parentElement;
        const playIcon = container.querySelector('.play-icon');
        const pauseIcon = container.querySelector('.pause-icon');
        
        playIcon.style.display = 'block';
        pauseIcon.style.display = 'none';
        
        this.trackVideoEvent('pause', videoId);
    }
    
    onVideoEnd(videoId) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        const container = element.closest('.video-wrapper') || element.parentElement;
        const playIcon = container.querySelector('.play-icon');
        const pauseIcon = container.querySelector('.pause-icon');
        
        playIcon.style.display = 'block';
        pauseIcon.style.display = 'none';
        
        this.trackVideoEvent('ended', videoId);
    }
    
    pauseOtherVideos(excludeVideoId) {
        this.videos.forEach((videoData, videoId) => {
            if (videoId !== excludeVideoId && videoData.isPlaying) {
                videoData.element.pause();
            }
        });
    }
    
    showLoadingState(videoId) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        const container = element.closest('.video-demo') || element.parentElement;
        container.classList.add('loading');
    }
    
    hideLoadingState(videoId) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        const container = element.closest('.video-demo') || element.parentElement;
        container.classList.remove('loading');
    }
    
    updateVideoReady(videoId) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        const container = element.closest('.video-demo') || element.parentElement;
        container.classList.add('ready');
    }
    
    handleVideoError(videoId, error) {
        const videoData = this.videos.get(videoId);
        const { element } = videoData;
        const container = element.closest('.video-wrapper') || element.parentElement;
        
        const errorOverlay = document.createElement('div');
        errorOverlay.className = 'video-error-overlay';
        errorOverlay.innerHTML = `
            <div class="error-content">
                <svg class="error-icon" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
                <h3>Video Unavailable</h3>
                <p>This video is temporarily unavailable. Please try again later.</p>
                <button class="retry-btn" onclick="this.closest('.video-error-overlay').remove(); this.closest('.video-wrapper').querySelector('video').load();">
                    Try Again
                </button>
            </div>
        `;
        
        container.appendChild(errorOverlay);
        
        console.error('Video error:', error);
        this.trackVideoEvent('error', videoId, { error: error.message });
    }
    
    setupVideoObservers() {
        // Lazy loading for videos
        const videoObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const video = entry.target;
                    if (video.dataset.src) {
                        video.src = video.dataset.src;
                        video.load();
                        delete video.dataset.src;
                        videoObserver.unobserve(video);
                    }
                }
            });
        }, { rootMargin: '50px' });
        
        document.querySelectorAll('video[data-src]').forEach(video => {
            videoObserver.observe(video);
        });
    }
    
    bindGlobalEvents() {
        // Pause all videos when page becomes hidden
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.videos.forEach(videoData => {
                    if (videoData.isPlaying) {
                        videoData.element.pause();
                    }
                });
            }
        });
    }
    
    trackVideoEvent(event, videoId, data = {}) {
        const videoData = this.videos.get(videoId);
        const eventData = {
            video_id: videoId,
            video_src: videoData.element.src,
            current_time: videoData.currentTime,
            duration: videoData.duration,
            ...data
        };
        
        // Replace with your analytics implementation
        console.log(`Video ${event}:`, eventData);
        
        // Example: Send to analytics service
        // analytics.track(`video_${event}`, eventData);
    }
}

// Initialize video controller when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new VideoController();
});

// CSS for video controls
const videoControlsCSS = `
    .video-controls-overlay {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(transparent, rgba(0,0,0,0.7));
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
    }
    
    .video-controls-overlay.visible {
        opacity: 1;
        pointer-events: auto;
    }
    
    .video-controls {
        display: flex;
        align-items: center;
        padding: 1rem;
        gap: 1rem;
    }
    
    .play-pause-btn,
    .volume-btn,
    .fullscreen-btn {
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        padding: 0.5rem;
        border-radius: 4px;
        transition: background 0.2s;
    }
    
    .play-pause-btn:hover,
    .volume-btn:hover,
    .fullscreen-btn:hover {
        background: rgba(255,255,255,0.2);
    }
    
    .play-pause-btn svg,
    .volume-btn svg,
    .fullscreen-btn svg {
        width: 20px;
        height: 20px;
        fill: currentColor;
    }
    
    .video-progress {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .progress-bar {
        flex: 1;
        height: 4px;
        background: rgba(255,255,255,0.3);
        border-radius: 2px;
        cursor: pointer;
        position: relative;
    }
    
    .progress-fill {
        height: 100%;
        background: var(--primary-color);
        border-radius: 2px;
        transition: width 0.1s;
    }
    
    .time-display {
        color: white;
        font-size: 0.875rem;
        white-space: nowrap;
    }
    
    .video-volume {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .volume-slider {
        width: 60px;
    }
    
    .video-error-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10;
    }
    
    .error-content {
        text-align: center;
        color: white;
        padding: 2rem;
    }
    
    .error-icon {
        width: 48px;
        height: 48px;
        fill: #ef4444;
        margin-bottom: 1rem;
    }
    
    .retry-btn {
        background: var(--primary-color);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        cursor: pointer;
        margin-top: 1rem;
    }
    
    @media (max-width: 768px) {
        .video-controls {
            padding: 0.5rem;
            gap: 0.5rem;
        }
        
        .volume-slider {
            display: none;
        }
        
        .time-display {
            font-size: 0.75rem;
        }
    }
`;

// Inject video controls styles
const videoStyleSheet = document.createElement('style');
videoStyleSheet.textContent = videoControlsCSS;
document.head.appendChild(videoStyleSheet);
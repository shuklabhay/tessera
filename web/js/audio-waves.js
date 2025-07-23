function initializeAudioWaves() {
    const container = document.querySelector('.audio-waves');
    if (!container) return;

    const waves = container.querySelectorAll('.wave');
    waves.forEach(wave => {
        const pointsContainer = wave.querySelector('.wave-points');
        if (!pointsContainer) return;
        
        const numPoints = 40;
        const isPrimary = wave.classList.contains('wave-primary');
        const amplitude = isPrimary ? 12 : 8;
        
        for (let i = 0; i < numPoints; i++) {
            const point = document.createElement('div');
            point.className = 'wave-point';
            
            const xPos = (i / (numPoints - 1)) * 100;
            point.style.left = `${xPos}%`;
            
            const yOffset = Math.sin(i * 0.2) * amplitude;
            point.style.transform = `translateY(${yOffset}px)`;
            
            pointsContainer.appendChild(point);
        }
    });

    function animateWaves() {
        waves.forEach((wave, waveIndex) => {
            const points = wave.querySelectorAll('.wave-point');
            const isPrimary = wave.classList.contains('wave-primary');
            const speed = isPrimary ? 0.05 : 0.03;
            const amplitude = isPrimary ? 12 : (wave.classList.contains('wave-secondary') ? 8 : 5);
            const offset = waveIndex * 2;
            
            points.forEach((point, i) => {
                const time = Date.now() * speed + i * 0.2 + offset;
                const y = Math.sin(time * 0.1) * amplitude;
                point.style.transform = `translateY(${y}px)`;
            });
        });
        
        requestAnimationFrame(animateWaves);
    }
    
    animateWaves();
}

document.addEventListener('DOMContentLoaded', function() {
    initializeAudioWaves();
});
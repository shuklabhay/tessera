function animateFigure8() {
    const svg = document.querySelector('.figure8-svg');
    if (!svg) return;

    const path = svg.querySelector('.figure8-path');
    const orb1 = svg.querySelector('.orb-1');
    const orb2 = svg.querySelector('.orb-2');
    
    if (!path || !orb1 || !orb2) return;
    
    const pathLength = path.getTotalLength();
    let position = 0;
    
    function animate() {
        // Calculate positions for both orbs
        const point1 = path.getPointAtLength(position);
        const point2 = path.getPointAtLength((position + pathLength/2) % pathLength);
        
        // Update orb positions
        orb1.setAttribute('cx', point1.x);
        orb1.setAttribute('cy', point1.y);
        
        orb2.setAttribute('cx', point2.x);
        orb2.setAttribute('cy', point2.y);
        
        // Increment position
        position += 1;
        if (position > pathLength) {
            position = 0;
        }
        
        requestAnimationFrame(animate);
    }
    
    animate();
}

document.addEventListener('DOMContentLoaded', animateFigure8);
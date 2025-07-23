class ScrollAnimations {
  constructor() {
    this.observers = new Map();
    this.animatedElements = new Set();
    this.init();
  }

  init() {
    this.createObservers();
    this.setupAnimations();
  }

  createObservers() {
    const fadeObserver = new IntersectionObserver(
      this.handleFadeIntersection.bind(this),
      {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px",
      }
    );

    const staggerObserver = new IntersectionObserver(
      this.handleStaggerIntersection.bind(this),
      {
        threshold: 0.05,
        rootMargin: "0px 0px -100px 0px",
      }
    );

    this.observers.set("fade", fadeObserver);
    this.observers.set("stagger", staggerObserver);
  }

  setupAnimations() {
    const fadeElements = document.querySelectorAll(
      ".feature-card, .tech-feature, .step, .phase-item"
    );

    fadeElements.forEach((el) => {
      el.classList.add("fade-ready");
      this.observers.get("fade").observe(el);
    });

    const staggerGroups = document.querySelectorAll(
      ".features-grid, .video-grid, .tech-grid"
    );

    staggerGroups.forEach((group) => {
      this.observers.get("stagger").observe(group);
    });

    this.setupHeroAnimations();
    this.setupCounterAnimations();
  }

  handleFadeIntersection(entries) {
    entries.forEach((entry) => {
      if (entry.isIntersecting && !this.animatedElements.has(entry.target)) {
        this.animatedElements.add(entry.target);
        entry.target.classList.add("fade-in");
      }
    });
  }

  handleStaggerIntersection(entries) {
    entries.forEach((entry) => {
      if (entry.isIntersecting && !this.animatedElements.has(entry.target)) {
        this.animatedElements.add(entry.target);
        this.staggerChildren(entry.target);
      }
    });
  }

  staggerChildren(container) {
    const children = container.children;
    Array.from(children).forEach((child, index) => {
      setTimeout(() => {
        child.classList.add("stagger-in");
      }, index * 100);
    });
  }

  setupHeroAnimations() {
    const heroTitle = document.querySelector(".hero-title");
    const heroSubtitle = document.querySelector(".hero-subtitle");
    const heroCTA = document.querySelector(".hero-cta");
    const heroVideo = document.querySelector(".hero-video");

    setTimeout(() => {
      if (heroTitle) heroTitle.classList.add("slide-up");
    }, 200);

    setTimeout(() => {
      if (heroSubtitle) heroSubtitle.classList.add("slide-up");
    }, 400);

    setTimeout(() => {
      if (heroCTA) heroCTA.classList.add("slide-up");
    }, 600);

    setTimeout(() => {
      if (heroVideo) heroVideo.classList.add("slide-left");
    }, 800);
  }

  setupCounterAnimations() {
    const phaseNumbers = document.querySelectorAll(".phase-number");
    const stepNumbers = document.querySelectorAll(".step-number");

    const counterObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (
            entry.isIntersecting &&
            !this.animatedElements.has(entry.target)
          ) {
            this.animatedElements.add(entry.target);
            const targetNumber = parseInt(entry.target.textContent);
            this.animateCounter(entry.target, targetNumber);
          }
        });
      },
      { threshold: 0.5 }
    );

    [...phaseNumbers, ...stepNumbers].forEach((el) => {
      counterObserver.observe(el);
    });
  }

  animateCounter(element, target) {
    let current = 0;
    const increment = target / 40; 
    const duration = 1000; 
    const stepTime = duration / 40;

    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        current = target;
        clearInterval(timer);
      }
      element.textContent = Math.floor(current);
    }, stepTime);
  }
}

class ParallaxEffect {
  constructor() {
    this.elements = [];
    this.init();
  }

  init() {
    const heroVideo = document.querySelector(".hero-video");
    const heroContent = document.querySelector(".hero-content");

    if (heroVideo) {
      this.elements.push({
        element: heroVideo,
        speed: 0.5,
      });
    }

    if (heroContent) {
      this.elements.push({
        element: heroContent,
        speed: 0.8,
      });
    }

    if (this.elements.length > 0) {
      this.bindEvents();
    }
  }

  bindEvents() {
    let ticking = false;

    window.addEventListener("scroll", () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          this.updateParallax();
          ticking = false;
        });
        ticking = true;
      }
    });
  }

  updateParallax() {
    const scrolled = window.pageYOffset;
    const rate = scrolled * -0.5;

    this.elements.forEach((item) => {
      const yPos = Math.round(rate * item.speed);
      item.element.style.transform = `translateY(${yPos}px)`;
    });
  }
}

class TextRevealAnimation {
  constructor() {
    this.init();
  }

  init() {
    const textElements = document.querySelectorAll(
      ".hero-title, .hero-subtitle, .section-header h2, .section-header p"
    );

    textElements.forEach((el) => {
      this.wrapWordsInSpans(el);
    });

    const observer = new IntersectionObserver(
      this.handleTextIntersection.bind(this),
      {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px",
      }
    );

    textElements.forEach((el) => observer.observe(el));
  }

  wrapWordsInSpans(element) {
    const text = element.textContent;
    const words = text.split(" ");
    element.innerHTML = words
      .map((word) => `<span class="word-reveal">${word}</span>`)
      .join(" ");
  }

  handleTextIntersection(entries) {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const words = entry.target.querySelectorAll(".word-reveal");
        words.forEach((word, index) => {
          setTimeout(() => {
            word.classList.add("revealed");
          }, index * 50);
        });
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  if (!prefersReducedMotion) {
    new ScrollAnimations();
    new ParallaxEffect();
    new TextRevealAnimation();
    initializeFigure8Animation();
  }
});

function initializeFigure8Animation() {
  const orb1 = document.querySelector(".orb-1");
  const orb2 = document.querySelector(".orb-2");
  const container = document.querySelector(".figure-eight");
  
  if (orb1 && orb2 && container) {
    let angle1 = 0;
    let angle2 = Math.PI; // Half cycle offset (180 degrees)
    
    const containerWidth = 240;
    const radius = 60; // Half of orbit size
    const centerX = containerWidth / 2;
    
    function updatePositions() {
      // Calculate which circle (left or right) based on angle
      const isOrb1InLeftCircle = angle1 < Math.PI;
      const isOrb2InLeftCircle = angle2 < Math.PI;
      
      // Orb 1 position
      if (isOrb1InLeftCircle) {
        // Left circle
        const x = centerX - radius + radius * Math.cos(angle1);
        const y = radius * Math.sin(angle1);
        orb1.style.left = `${x}px`;
        orb1.style.top = `${radius + y}px`;
      } else {
        // Right circle
        const x = centerX + radius * Math.cos(angle1);
        const y = radius * Math.sin(angle1);
        orb1.style.left = `${x}px`;
        orb1.style.top = `${radius + y}px`;
      }
      
      // Orb 2 position
      if (isOrb2InLeftCircle) {
        // Left circle
        const x = centerX - radius + radius * Math.cos(angle2);
        const y = radius * Math.sin(angle2);
        orb2.style.left = `${x}px`;
        orb2.style.top = `${radius + y}px`;
      } else {
        // Right circle
        const x = centerX + radius * Math.cos(angle2);
        const y = radius * Math.sin(angle2);
        orb2.style.left = `${x}px`;
        orb2.style.top = `${radius + y}px`;
      }
      
      // Increment angles
      angle1 += 0.015;
      if (angle1 > Math.PI * 2) angle1 -= Math.PI * 2;
      
      angle2 += 0.015;
      if (angle2 > Math.PI * 2) angle2 -= Math.PI * 2;
      
      requestAnimationFrame(updatePositions);
    }
    
    updatePositions();
  }
}

const animationStyles = `
    .fade-ready {
        opacity: 0;
        transform: translateY(30px);
        transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .fade-in {
        opacity: 1;
        transform: translateY(0);
    }
    
    .stagger-in {
        opacity: 1;
        transform: translateY(0);
        transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .features-grid > *,
    .video-grid > *,
    .tech-grid > * {
        opacity: 0;
        transform: translateY(30px);
    }
    
    .hero-title,
    .hero-subtitle,
    .hero-cta {
        opacity: 0;
        transform: translateY(40px);
        transition: all 1s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .hero-video {
        opacity: 0;
        transform: translateX(40px);
        transition: all 1.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .slide-up {
        opacity: 1;
        transform: translateY(0);
    }
    
    .slide-left {
        opacity: 1;
        transform: translateX(0);
    }
    
    .word-reveal {
        display: inline-block;
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .word-reveal.revealed {
        opacity: 1;
        transform: translateY(0);
    }
    
    .feature-card,
    .video-demo,
    .phase-item {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .feature-card:hover {
        transform: translateY(-8px) scale(1.02);
    }
    
    .video-demo:hover {
        transform: translateY(-6px);
    }
    
    .phase-item:hover {
        transform: translateX(12px);
    }
    
    .btn {
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .btn::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }
    
    .btn:hover::before {
        left: 100%;
    }
    
    @media (prefers-reduced-motion: reduce) {
        .fade-ready,
        .hero-title,
        .hero-subtitle,
        .hero-cta,
        .hero-video,
        .word-reveal {
            opacity: 1;
            transform: none;
            transition: none;
        }
        
        .feature-card:hover,
        .video-demo:hover,
        .phase-item:hover {
            transform: none;
        }
    }
`;

const styleSheet = document.createElement("style");
styleSheet.textContent = animationStyles;
document.head.appendChild(styleSheet);

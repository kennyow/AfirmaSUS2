/* Content stays visible without JavaScript; motion respects user preferences. */
(() => {
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.05 });
    document.querySelectorAll('.editorial-heading, .pathway, .activities-heading, .footer-callout').forEach(element => {
        // Only animate elements below the initial viewport. No hidden primary content.
        if (element.getBoundingClientRect().top > window.innerHeight) {
            element.classList.add('reveal-ready');
            observer.observe(element);
        }
    });
})();

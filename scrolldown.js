function Scrolldown() {
    const findScrollArea = (root) => {
        if (!root) return null;
        const candidates = Array.from(root.querySelectorAll('*')).filter(el => {
            const style = window.getComputedStyle(el);
            return el.scrollHeight > el.clientHeight && (style.overflowY === 'auto' || style.overflowY === 'scroll' || style.overflowY === 'overlay');
        });
        return candidates.length ? candidates[candidates.length - 1] : null;
    };

    const root = document.getElementById('chatbot');
    if (!root) {
        setTimeout(Scrolldown, 500);
        return;
    }

    let targetNode = findScrollArea(root);
    
    if (!targetNode) {
        let attempts = 0;
        const checkInterval = setInterval(() => {
            targetNode = findScrollArea(root);
            if (targetNode) {
                clearInterval(checkInterval);
                attachObserver(targetNode);
            }
            attempts++;
            if (attempts > 40) {
                clearInterval(checkInterval);
            }
        }, 100);
        return;
    }

    attachObserver(targetNode);
}

function attachObserver(targetNode) {
    targetNode.scrollTop = targetNode.scrollHeight;
    const config = { attributes: true, childList: true, subtree: true };
    const callback = () => {
        targetNode.scrollTop = targetNode.scrollHeight;
    };
    const observer = new MutationObserver(callback);
    observer.observe(targetNode, config);
}

// Call immediately
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', Scrolldown);
} else {
    requestAnimationFrame(() => setTimeout(Scrolldown, 100));
}

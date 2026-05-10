function Scrolldown() {
    const root = document.getElementById('chatbot');
    if (!root) {
        setTimeout(Scrolldown, 300);
        return;
    }

    const findScrollArea = () => {
        const scrollables = Array.from(root.querySelectorAll('*')).filter(el => el.scrollHeight > el.clientHeight);
        if (!scrollables.length) return null;
        return scrollables.reverse().find(el => typeof el.scrollTop === 'number') || null;
    };

    const findLatestMessage = () => {
        return root.querySelector('.message-row:last-child, .chatbot-message:last-child, .chatbot-card:last-child, .generated-message:last-child, .message:last-child');
    };

    const scrollBottom = () => {
        const latest = findLatestMessage();
        if (latest) {
            latest.scrollIntoView({ behavior: 'auto', block: 'end', inline: 'nearest' });
        }

        const targetNode = findScrollArea() || root;
        if (targetNode) {
            targetNode.scrollTop = targetNode.scrollHeight;
        }
    };

    scrollBottom();
    setTimeout(scrollBottom, 100);
    setTimeout(scrollBottom, 300);

    const observer = new MutationObserver(scrollBottom);
    observer.observe(root, { childList: true, subtree: true });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', Scrolldown);
} else {
    requestAnimationFrame(() => setTimeout(Scrolldown, 100));
}

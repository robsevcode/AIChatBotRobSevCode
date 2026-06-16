import gradio as gr

style_html = """
<style>
/* Resize the avatar image */
.message-row.user-row .avatar-image.svelte-1pijsyv {
    width: 40px !important;
    height: 40px !important;
    min-width: 40px !important;
    min-height: 40px !important;
}
        
.message-row.bot-row .avatar-image.svelte-1pijsyv {
    width: 70px !important;
    height: 70px !important;
    min-width: 70px !important;
    min-height: 70px !important;
}

/* Resize its container so layout adjusts */
.message-row.bot-row .avatar-container.svelte-1csv61q {
    width: 70px !important;
    height: 70px !important;
    min-width: 70px !important;
    min-height: 70px !important;
}

/* Resize its container so layout adjusts */
.message-row.user-row .avatar-container.svelte-1csv61q {
    width: 40px !important;
    height: 40px !important;
    min-width: 40px !important;
    min-height: 40px !important;
}

/* Adjust message bubble spacing so text doesn't overlap */
.message-row.svelte-1csv61q.with_avatar.with_opposite_avatar {
    margin-left: 10px !important;   /* space for user avatar */
    margin-right: 10px !important;  /* space for bot avatar */
}
.gradio-container *::-webkit-scrollbar {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    }

    /* Hide scrollbars for IE, Edge and Firefox */
    .gradio-container * {
    -ms-overflow-style: none !important;  /* IE and Edge */
    scrollbar-width: none !important;  /* Firefox */
    }

    /* Fix potential overflow issues while ensuring content is still accessible */
    .gradio-container [data-testid="table"] {
    overflow: hidden !important;
    }

    .gradio-container .gradio-dataframe {
    overflow: hidden !important;
    }

    /* Target additional selectors that might contain scrollbars */
    .gradio-container .table-wrap {
    overflow: hidden !important;
    }

    .gradio-container .scroll-container {
    overflow: hidden !important;
    }

    /* Handle any fixed height elements that might trigger scrollbars */
    .gradio-container .fixed-height {
    max-height: none !important;
    }

/* Make bold-italic action text pure white for easier reading */
.gradio-container .markdown strong em,
.gradio-container .markdown em strong,
.gradio-container strong em,
.gradio-container em strong {
    color: #ffffff !important;
}

/* Hide the residual Share button for avatars/messages */
.gradio-container button[title="Share"],
.gradio-container [aria-label="Share"] {
    display: none !important;
}
/* Hide the app-level Clear button */
.gradio-container button[title="Clear"],
.gradio-container [aria-label="Clear"] {
    display: none !important;
}
</style>
"""

script_html = """
<script>
function removeShareAndClearButtons() {
    const selectors = ['button', 'a', 'input'];
    selectors.forEach(selector => {
        document.querySelectorAll(selector).forEach(el => {
            const text = (el.innerText || '').trim();
            const title = el.title || '';
            const aria = el.getAttribute('aria-label') || '';
            if (['Share', 'Clear'].includes(text) || ['Share', 'Clear'].includes(title) || ['Share', 'Clear'].includes(aria)) {
                el.style.display = 'none';
            }
        });
    });
}

function Scrolldown() {
    const root = document.getElementById('chatbot');
    if (!root) {
        setTimeout(() => { removeShareAndClearButtons(); Scrolldown(); }, 300);
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

    const observer = new MutationObserver(() => {
        removeShareAndClearButtons();
        scrollBottom();
    });
    observer.observe(root, { childList: true, subtree: true });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        removeShareAndClearButtons();
        Scrolldown();
    });
} else {
    requestAnimationFrame(() => setTimeout(() => {
        removeShareAndClearButtons();
        Scrolldown();
    }, 100));
}
</script>
"""


def inject_gr_html(parent: gr.Blocks):
    """Inject extracted style and script HTML into a Gradio Blocks parent.

    Keep HTML content centralized here so `main.py` doesn't need editing.
    """
    # Use simple calls to gr.HTML so callers can just call this function.
    gr.HTML(style_html)
    gr.HTML(script_html)

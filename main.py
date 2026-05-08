import logging
import gradio as gr
from ui_components import build_chat_ui
import os

logging.getLogger("httpx").setLevel(logging.WARNING)

css = """
.generating,
.generating.svelte-zlszon.svelte-zlszon {
    border: none !important;
    box-shadow: none !important;
    background-color: transparent !important;
}
"""

# Get the path to scrolldown.js in the same directory as this script
js_path = os.path.join(os.path.dirname(__file__), "scrolldown.js")

with gr.Blocks(title="AI Chat bot", css=css, js=js_path) as demo:
    demo.queue()
    gr.HTML("""
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
        </style>
    """)
    chat_list, chatbot, msg_box, current_chat, char_name_input, system_prompt_input, create_char_btn, system_prompt_display = build_chat_ui(demo)

    gr.HTML("""
    <script>
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
            // Retry if root not found yet
            setTimeout(Scrolldown, 500);
            return;
        }

        let targetNode = findScrollArea(root);
        
        if (!targetNode) {
            // Try again with polling
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
        // Scroll to bottom immediately
        targetNode.scrollTop = targetNode.scrollHeight;

        // Set up observer to keep scrolling to bottom as new messages arrive
        const config = { attributes: true, childList: true, subtree: true };
        const callback = () => {
            targetNode.scrollTop = targetNode.scrollHeight;
        };
        const observer = new MutationObserver(callback);
        observer.observe(targetNode, config);
    }

    // Call Scrolldown as soon as possible
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', Scrolldown);
    } else {
        // Use requestAnimationFrame and setTimeout for extra safety
        requestAnimationFrame(() => setTimeout(Scrolldown, 100));
    }
    </script>
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7861)

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

with gr.Blocks(title="AI Chat bot") as demo:
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
    """)
    chat_list, chatbot, msg_box, current_chat, char_name_input, system_prompt_input, create_char_btn, system_prompt_display = build_chat_ui(demo)

    gr.HTML("""
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
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, css=css, js=js_path)

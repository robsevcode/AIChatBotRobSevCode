import gradio as gr
from ui_components import build_chat_ui

with gr.Blocks(title="AI Chat bot") as demo:
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
    chat_list, chatbot, msg_box, current_chat, char_name_input, system_prompt_input, create_char_btn, system_prompt_display = build_chat_ui()

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)

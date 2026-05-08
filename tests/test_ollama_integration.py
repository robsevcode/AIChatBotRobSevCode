import os
import sys
import json
import unittest

# Ensure the repository root is on sys.path when tests are run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import chat_backend
import ollama

class TestOllamaIntegration(unittest.TestCase):
    def test_ollama_chat_response(self):
        system_prompt = "You are a helpful assistant."
        history = [{"role": "user", "content": "Hello, how are you?"}]

        generator = chat_backend.make_chat_fn(system_prompt, history)(history)
        result = list(generator)

        self.assertTrue(result, "Expected at least one generator output from Ollama")
        final_history = result[-1]
        self.assertIsInstance(final_history, list)
        self.assertTrue(final_history, "Final history should not be empty")

        assistant_messages = [msg for msg in final_history if msg.get("role") == "assistant"]
        self.assertTrue(assistant_messages, "Expected at least one assistant message in the returned history")
        self.assertTrue(
            any(msg.get("content") for msg in assistant_messages),
            "Expected assistant message content to be non-empty"
        )

    def test_direct_ollama_api_response(self):
        system_prompt = "You are a helpful assistant."
        history = [{"role": "user", "content": "Say hello to me."}]

        gen = ollama.chat_with_ollama(system_prompt, history, history)
        result = list(gen)

        self.assertTrue(result, "Expected direct Ollama generator output")
        self.assertIsInstance(result[-1], list)
        self.assertTrue(result[-1][-1].get("content"), "The final assistant message should contain text")

    def test_save_chat_persists_history(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            original_chat_folder = chat_backend.CHAT_FOLDER
            original_backup_folder = chat_backend.BACKUP_CHAT_FOLDER
            chat_backend.CHAT_FOLDER = tmpdir
            chat_backend.BACKUP_CHAT_FOLDER = os.path.join(tmpdir, "backup")
            os.makedirs(chat_backend.BACKUP_CHAT_FOLDER, exist_ok=True)

            try:
                name = "TestCharacter"
                chat_data = {"history": [{"role": "user", "content": "Hi"}]}
                chat_backend.save_chat(name, chat_data)
                loaded_data, metadata = chat_backend.load_chat(name)

                self.assertEqual(loaded_data["history"], chat_data["history"])
                self.assertEqual(loaded_data.get("system_prompt", ""), "")
            finally:
                chat_backend.CHAT_FOLDER = original_chat_folder
                chat_backend.BACKUP_CHAT_FOLDER = original_backup_folder

if __name__ == '__main__':
    unittest.main()

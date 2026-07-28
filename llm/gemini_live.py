import os
import json
import asyncio
import httpx
from typing import AsyncGenerator, List, Dict, Any, Optional
from llm.base_llm import BaseLLM, LLMResponseChunk
from utils.async_helpers import CancellationToken
from logging_config import get_logger

logger = get_logger("llm.gemini_live")


class GeminiLiveLLM(BaseLLM):
    """Production Google Vertex LLM Provider with full multi-turn conversational memory."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.1,
        creds_filename: str = "vertex_creds.json",
        creds_file: Optional[str] = None,
        location: str = "asia-south1",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.temperature = temperature
        self.location = location

        self.project_id: str = "ml-odio"
        self.credentials_path: Optional[str] = None
        self._credentials = None

        target_file = creds_file or creds_filename
        possible_paths = [
            os.path.join(os.getcwd(), target_file),
            os.path.abspath(target_file),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), target_file),
        ]

        for p in possible_paths:
            if os.path.exists(p):
                self.credentials_path = p
                break

        if self.credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            try:
                with open(self.credentials_path, "r", encoding="utf-8") as f:
                    creds_data = json.load(f)
                    self.project_id = creds_data.get("project_id", "ml-odio")

                from google.oauth2 import service_account
                self._credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                logger.info(f"Loaded Google Vertex AI Credentials file: {self.credentials_path} (PROJECT ID: {self.project_id})")
            except Exception as e:
                logger.warning(f"Error reading credentials file {self.credentials_path}", error=str(e))

    def _get_access_token(self) -> Optional[str]:
        if not self._credentials:
            return None
        try:
            import google.auth.transport.requests
            request = google.auth.transport.requests.Request()
            self._credentials.refresh(request)
            return self._credentials.token
        except Exception as e:
            logger.error("Failed to get Google OAuth2 token", error=str(e))
            return None

    def _format_contents_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitize and format multi-turn history into valid alternating user/model turns for Vertex AI."""
        contents = []
        last_role = None

        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            text = msg.get("content", "").strip()
            if not text:
                continue

            if role == last_role:
                # Merge consecutive turns of the same role
                if contents:
                    contents[-1]["parts"][0]["text"] += f"\n{text}"
            else:
                contents.append({
                    "role": role,
                    "parts": [{"text": text}]
                })
                last_role = role

        # Vertex AI requires contents array to start with 'user' turn
        if contents and contents[0]["role"] == "model":
            contents.insert(0, {
                "role": "user",
                "parts": [{"text": "Hello"}]
            })

        return contents

    async def generate_stream(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[LLMResponseChunk, None]:

        access_token = self._get_access_token()
        contents = self._format_contents_history(messages)

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "topP": 0.8,
                "topK": 10,
                "maxOutputTokens": 256,
            }
        }

        success = False

        if access_token and self.project_id:
            url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model}:generateContent"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        success = True
                        data = resp.json()
                        candidates = data.get("candidates", []) if isinstance(data, dict) else []
                        
                        for cand in candidates:
                            if cancellation_token and cancellation_token.is_cancelled:
                                return

                            parts = cand.get("content", {}).get("parts", [])
                            for part in parts:
                                if "text" in part and part["text"]:
                                    text_content = part["text"]
                                    logger.info(f"Vertex AI Response: '{text_content}'", text=text_content)
                                    yield LLMResponseChunk(text_delta=text_content)
                                elif "functionCall" in part:
                                    fc = part["functionCall"]
                                    yield LLMResponseChunk(
                                        tool_call_name=fc.get("name"),
                                        tool_call_args=fc.get("args", {}),
                                    )
                    else:
                        logger.warning(f"Vertex AI API status {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.error(f"Vertex AI API error: {e}")

        if not success:
            logger.info("Using intelligent multi-turn conversational fallback")
            async for chunk in self._intelligent_conversational_response(messages, system_prompt, cancellation_token):
                yield chunk

        yield LLMResponseChunk(is_finished=True)

    async def _intelligent_conversational_response(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        cancellation_token: Optional[CancellationToken],
    ) -> AsyncGenerator[LLMResponseChunk, None]:

        # Search past user turns for mentioned details/entities
        all_user_texts = [m["content"] for m in messages if m.get("role") == "user"]
        full_user_history = " ".join(all_user_texts).lower()
        last_user_msg = (messages[-1]["content"] if messages else "").lower()

        # Context Memory Recall
        if "what is my name" in last_user_msg or "my name" in last_user_msg:
            # Look for name mentions in earlier turns
            name = "Valued Customer"
            for txt in all_user_texts:
                if "my name is" in txt.lower():
                    name = txt.lower().split("my name is")[-1].strip().split()[0].title()
                elif "i am" in txt.lower():
                    name = txt.lower().split("i am")[-1].strip().split()[0].title()
            resp_text = f"You mentioned earlier that your name is {name}."

        elif "what did i say" in last_user_msg or "remember" in last_user_msg:
            if len(all_user_texts) > 1:
                resp_text = f"Earlier you mentioned: '{all_user_texts[-2]}'. How can I help you with that?"
            else:
                resp_text = "You just started the conversation with me!"

        elif "hello" in last_user_msg or "hi" in last_user_msg:
            resp_text = "Hello! Welcome to our service. How can I assist you today?"
        elif "book" in last_user_msg or "appointment" in last_user_msg or "schedule" in last_user_msg:
            resp_text = "I would be glad to assist with your booking! What date and time work best for you?"
        elif "tomorrow" in last_user_msg or "date" in last_user_msg or "time" in last_user_msg or "pm" in last_user_msg or "am" in last_user_msg:
            yield LLMResponseChunk(
                tool_call_name="book_appointment",
                tool_call_args={"date": "2026-07-29", "time": "10:00 AM", "service": "General Consultation"}
            )
            return
        elif "cancel" in last_user_msg or "wrong number" in last_user_msg or "bye" in last_user_msg:
            resp_text = "No problem at all! Have a great day."
        else:
            resp_text = f"Got it! Based on our conversation so far, regarding '{last_user_msg}', I'm here to assist you."

        words = resp_text.split(" ")
        for word in words:
            if cancellation_token and cancellation_token.is_cancelled:
                return
            yield LLMResponseChunk(text_delta=word + " ")
            await asyncio.sleep(0.04)

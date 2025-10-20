"""
LLM Client Module
Supports LM Studio (local/remote), OpenAI ChatGPT, and Microsoft Copilot APIs
"""

import os
import requests
from typing import Dict, Optional

class LMStudioClient:
    def __init__(self):
        self.provider = os.getenv('LLM_PROVIDER', 'lmstudio')  # lmstudio, openai, copilot
        self.endpoint = os.getenv('LM_STUDIO_ENDPOINT', 'http://localhost:1234')
        self.api_key = os.getenv('OPENAI_API_KEY') or os.getenv('COPILOT_API_KEY')
        self.model = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
        self.temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))
        self.max_tokens = int(os.getenv('LLM_MAX_TOKENS', '4000'))

    def get_config(self) -> Dict:
        """Get current configuration"""
        return {
            'provider': self.provider,
            'endpoint': self.endpoint,
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'has_api_key': bool(self.api_key)
        }

    def update_config(self, config: Dict):
        """Update configuration"""
        if 'provider' in config:
            self.provider = config['provider']
        if 'endpoint' in config:
            self.endpoint = config['endpoint']
        if 'api_key' in config:
            self.api_key = config['api_key']
        if 'model' in config:
            self.model = config['model']
        if 'temperature' in config:
            self.temperature = float(config['temperature'])
        if 'max_tokens' in config:
            self.max_tokens = int(config['max_tokens'])

    def generate(self, prompt: str) -> str:
        """Generate completion using configured provider"""
        if self.provider == 'lmstudio':
            return self._generate_lmstudio(prompt)
        elif self.provider == 'openai':
            return self._generate_openai(prompt)
        elif self.provider == 'copilot':
            return self._generate_copilot(prompt)
        else:
            raise Exception(f"Unknown provider: {self.provider}")

    def generate_chat(self, messages: list, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
        """Generate completion using chat-style messages"""
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        if self.provider == 'lmstudio':
            return self._generate_lmstudio_chat(messages, temp, tokens)
        elif self.provider == 'openai':
            return self._generate_openai_chat(messages, temp, tokens)
        elif self.provider == 'copilot':
            return self._generate_copilot_chat(messages, temp, tokens)
        else:
            raise Exception(f"Unknown provider: {self.provider}")

    def _generate_lmstudio(self, prompt: str) -> str:
        """Generate using LM Studio (local or remote)"""
        url = f"{self.endpoint}/v1/completions"

        payload = {
            "prompt": prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stop": []  # Remove stop sequences to allow longer responses
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            # LM Studio returns completions in choices array
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['text'].strip()
            else:
                raise Exception("No completion returned from LM Studio")

        except requests.exceptions.ConnectionError:
            raise Exception(f"Could not connect to LM Studio at {self.endpoint}. Is it running?")
        except Exception as e:
            raise Exception(f"LM Studio generation failed: {str(e)}")

    def _generate_openai(self, prompt: str) -> str:
        """Generate using OpenAI ChatGPT API"""
        if not self.api_key:
            raise Exception("OpenAI API key not configured")

        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content'].strip()
            else:
                raise Exception("No completion returned from OpenAI")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("Invalid OpenAI API key")
            elif e.response.status_code == 429:
                raise Exception("OpenAI rate limit exceeded")
            else:
                raise Exception(f"OpenAI API error: {e.response.text}")
        except Exception as e:
            raise Exception(f"OpenAI generation failed: {str(e)}")

    def _generate_copilot(self, prompt: str) -> str:
        """Generate using Microsoft Copilot API (OpenAI-compatible endpoint)"""
        if not self.api_key:
            raise Exception("Copilot API key not configured")

        # Microsoft Copilot uses OpenAI-compatible API
        # Endpoint might be different, e.g., Azure OpenAI endpoint
        copilot_endpoint = os.getenv('COPILOT_ENDPOINT', 'https://api.openai.com/v1/chat/completions')

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        try:
            response = requests.post(copilot_endpoint, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content'].strip()
            else:
                raise Exception("No completion returned from Copilot")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("Invalid Copilot API key")
            elif e.response.status_code == 429:
                raise Exception("Copilot rate limit exceeded")
            else:
                raise Exception(f"Copilot API error: {e.response.text}")
        except Exception as e:
            raise Exception(f"Copilot generation failed: {str(e)}")

    def _generate_lmstudio_chat(self, messages: list, temperature: float, max_tokens: int) -> str:
        """Generate using LM Studio with chat messages"""
        url = f"{self.endpoint}/v1/chat/completions"

        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content'].strip()
            else:
                raise Exception("No completion returned from LM Studio")

        except requests.exceptions.ConnectionError:
            raise Exception(f"Could not connect to LM Studio at {self.endpoint}. Is it running?")
        except Exception as e:
            raise Exception(f"LM Studio generation failed: {str(e)}")

    def _generate_openai_chat(self, messages: list, temperature: float, max_tokens: int) -> str:
        """Generate using OpenAI ChatGPT API with chat messages"""
        if not self.api_key:
            raise Exception("OpenAI API key not configured")

        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content'].strip()
            else:
                raise Exception("No completion returned from OpenAI")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("Invalid OpenAI API key")
            elif e.response.status_code == 429:
                raise Exception("OpenAI rate limit exceeded")
            else:
                raise Exception(f"OpenAI API error: {e.response.text}")
        except Exception as e:
            raise Exception(f"OpenAI generation failed: {str(e)}")

    def _generate_copilot_chat(self, messages: list, temperature: float, max_tokens: int) -> str:
        """Generate using Microsoft Copilot API with chat messages"""
        if not self.api_key:
            raise Exception("Copilot API key not configured")

        copilot_endpoint = os.getenv('COPILOT_ENDPOINT', 'https://api.openai.com/v1/chat/completions')

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(copilot_endpoint, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content'].strip()
            else:
                raise Exception("No completion returned from Copilot")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("Invalid Copilot API key")
            elif e.response.status_code == 429:
                raise Exception("Copilot rate limit exceeded")
            else:
                raise Exception(f"Copilot API error: {e.response.text}")
        except Exception as e:
            raise Exception(f"Copilot generation failed: {str(e)}")

    def test_connection(self) -> Dict:
        """Test connection to the configured provider"""
        try:
            # Test with a simple prompt
            result = self.generate("Say 'OK' if you can read this.")
            return {
                'success': True,
                'message': f'Successfully connected to {self.provider}',
                'response': result
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }

import requests
import json

class AIGenerator:
    def __init__(self, api_key, provider='groq', model='llama-3.1-8b-instant', system_prompt=None):
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.system_prompt = system_prompt or "You are a helpful Twitter user."

    def generate_reply(self, tweet_text):
        if not self.api_key:
            return "Error: No API Key provided."

        try:
            if self.provider == 'groq':
                return self._generate_groq(tweet_text)
            elif self.provider == 'openai':
                return self._generate_openai(tweet_text)
            else:
                return "Error: Unknown provider."
        except Exception as e:
            print(f"AI Generation Error: {e}")
            return f"Error generating reply: {str(e)}"

    def _generate_groq(self, tweet_text):
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Reply to this tweet in Arabic language suitable for the context: \"{tweet_text}\". Keep it short, engaging, and relevant. Do not use hashtags unless necessary. Output ONLY the reply text."}
            ],
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content'].strip().replace('"', '')
        else:
            raise Exception(f"Groq API Error: {response.text}")

    def generate_tweets(self, topic, tone, lang='ar', count=3):
        if not self.api_key: return ["Error: No API Key"]
        
        lang_prompt = "Arabic" if lang == 'ar' else "English"
        
        system = f"You are a professional social media manager. Tone: {tone}. Language: {lang_prompt}."
        user_prompt = f"Generate {count} distinct, engaging tweets about '{topic}'. Keep them under 280 characters. Output ONLY a valid JSON list of strings. Example: [\"Tweet 1\", \"Tweet 2\"]"
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = { "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json" }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload))
            if r.status_code == 200:
                content = r.json()['choices'][0]['message']['content']
                # Parse JSON list
                data = json.loads(content)
                # Handle if it returns object with key 'tweets' or just list
                if isinstance(data, list): return data
                if 'tweets' in data: return data['tweets']
                return list(data.values()) # Fallback
            else:
                return [f"API Error: {r.text}"]
        except Exception as e:
            return [f"Error: {e}"]

    def _generate_openai(self, tweet_text):
        # Placeholder for OpenAI implementation if needed
        return "OpenAI not implemented yet."

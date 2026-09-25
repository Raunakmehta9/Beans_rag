import os
import json
from typing import List, Dict, Any, Optional
from groq import Groq
from backend.config import config
from backend.vector_store import BeansVectorStore

class BeansRAGAgent:
    def __init__(self, vector_store: Optional[BeansVectorStore] = None):
        self.vector_store = vector_store or BeansVectorStore()
        self.groq_client = Groq(api_key=config.GROQ_API_KEY)
        self.model = config.GROQ_MODEL
        self.fallback_model = config.GROQ_FALLBACK_MODEL
        self.threshold = config.SIMILARITY_THRESHOLD
        self.top_k = config.TOP_K

    def answer_query(self, query: str) -> Dict[str, Any]:
        """
        Executes end-to-end RAG:
        1. HNSW Vector search + Cosine similarity threshold guardrail
        2. Prompt assembly with timestamped cues & doc passages
        3. Groq Llama 3 synthesis with inline citations & reasoning
        """
        # Step 1: Retrieval
        retrieved_chunks = self.vector_store.query(
            query_text=query,
            top_k=self.top_k,
            threshold=self.threshold
        )

        # Step 2: Handle cases with and without retrieved documentation chunks
        sources_meta = []
        guardrail_triggered = False

        if not retrieved_chunks:
            guardrail_triggered = True
            system_prompt = (
                "You are the official Beans.ai Customer Support Assistant.\n"
                "Your mission is to provide helpful, courteous, and professional support to users of Beans.ai products, apps, and services (including drivers, dispatchers, and managers).\n\n"
                "GUIDELINES:\n"
                "1. If the user is asking about Beans.ai (e.g. issues, troubleshooting, app problems, account help, inquiries) but no specific documentation snippet is available in your database, provide helpful general support and troubleshooting guidance (such as restarting or updating the app, checking GPS/device permissions, or checking network connectivity) and direct them to contact Beans.ai support at support@beans.ai.\n"
                "2. If the user's question is completely unrelated to Beans.ai or logistics/support (e.g. baking a cake, recipes, sports, entertainment, general trivia), politely and briefly state that you are the Beans.ai support assistant and cannot assist with that topic, and offer help with any Beans.ai issues or inquiries they may have.\n"
                "3. Do NOT limit or pigeonhole the user into a fixed narrow list of features (e.g., do not say 'only ask about moving pins or manifest uploads'). You are here to assist with any Beans.ai issue or inquiry.\n"
                "4. Maintain a warm, concise, and professional customer support tone."
            )
            user_prompt = f"User Question: {query}\n\nPlease respond to the user helpfully as the Beans.ai support assistant."
        else:
            context_blocks = []
            for idx, chunk in enumerate(retrieved_chunks, 1):
                src_type = chunk["source_type"]
                title = chunk["title"]
                time_str = chunk.get("timestamp_str", "")
                deep_link = chunk.get("deep_link", "")
                snippet = chunk["text"]
                similarity = chunk["similarity"]

                if src_type == "youtube":
                    ref_label = f"Source [{idx}] (YouTube Video: '{title}' at {time_str})"
                else:
                    ref_label = f"Source [{idx}] (Zendesk Guide: '{title}')"

                context_blocks.append(f"{ref_label}\n{snippet}\n")

                sources_meta.append({
                    "source_index": idx,
                    "source_type": src_type,
                    "title": title,
                    "timestamp_str": time_str,
                    "start_seconds": chunk.get("start_seconds", 0.0),
                    "deep_link": deep_link,
                    "snippet": snippet[:280] + ("..." if len(snippet) > 280 else ""),
                    "full_text": snippet,
                    "similarity_score": similarity,
                    "rank": chunk["rank"]
                })

            formatted_context = "\n---\n".join(context_blocks)

            system_prompt = (
                "You are the official Beans.ai Customer Support Assistant.\n"
                "Your task is to answer the user's question accurately, concisely, and strictly based on the provided Context Sources.\n\n"
                "RULES:\n"
                "1. ONLY state facts that are directly supported by the context.\n"
                "2. Cite sources inline using ONLY simple numeric brackets like [1] or [2]. Never put timestamps, dagger symbols, or times inside or next to the citations (e.g., use '[1]', NEVER '【1†00:00】' or '[1 @ 00:30]').\n"
                "3. DO NOT write timestamps (like 00:00, 01:25) in your chat answer text. Timestamps and interactive video playback links are handled automatically by the user interface in the source cards below.\n"
                "4. Provide direct, clear, step-by-step instructions or explanations citing [1], [2], etc.\n"
                "5. If information on a detail is missing, state it honestly without guessing and suggest reaching out to support@beans.ai."
            )

            user_prompt = (
                f"User Question: {query}\n\n"
                f"Context Sources:\n{formatted_context}\n\n"
                "Please provide your direct answer citing sources as [1], [2]."
            )

        # Step 3: Call Groq API
        model_used = self.model
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                temperature=0.2,
                max_tokens=1024
            )
            raw_response = chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error calling {self.model}: {e}. Retrying with fallback model {self.fallback_model}...")
            model_used = self.fallback_model
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.fallback_model,
                temperature=0.2,
                max_tokens=1024
            )
            raw_response = chat_completion.choices[0].message.content

        # Step 5: Clean and format Answer (removing any legacy reasoning or headers)
        answer_part = raw_response
        for header in ["**How I Found This Information**", "How I Found This Information:", "### How I Found This Information"]:
            if header in answer_part:
                answer_part = answer_part.split(header)[0]
        answer_part = answer_part.replace("**Answer**:", "").replace("**Answer**", "").strip()

        # Sanitize any citation timestamp artifacts like 【1†00:00】 or [1 @ 00:00] into clean [1]
        import re
        answer_part = re.sub(r'[\[【](\d+)[†@:,\s][^\]】]*[\]】]', r'[\1]', answer_part)
        answer_part = re.sub(r'【(\d+)】', r'[\1]', answer_part)

        return {
            "answer": answer_part,
            "reasoning": "",
            "sources": sources_meta,
            "guardrail_triggered": guardrail_triggered,
            "model_used": model_used
        }

if __name__ == "__main__":
    agent = BeansRAGAgent()
    res = agent.answer_query("How do I move a pin on iPhone?")
    print("Answer:\n", res["answer"])
    print("\nReasoning:\n", res["reasoning"])
    print("\nSources:\n", json.dumps(res["sources"], indent=2))

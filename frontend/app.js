document.addEventListener("DOMContentLoaded", () => {
  const messagesContainer = document.getElementById("messages-container");
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const clearChatBtn = document.getElementById("clear-chat-btn");
  const suggestionsRow = document.getElementById("suggestions-row");
  const chunkCountFooter = document.getElementById("chunk-count-footer");

  // Stats elements
  const statsBtn = document.getElementById("stats-btn");
  const statsModal = document.getElementById("stats-modal");
  const closeStatsBtn = document.getElementById("close-stats-btn");
  const statLlm = document.getElementById("stat-llm");
  const statChunks = document.getElementById("stat-chunks");

  // Video Modal elements
  const videoModal = document.getElementById("video-modal");
  const modalVideoTitle = document.getElementById("modal-video-title");
  const videoEmbedContainer = document.getElementById("video-embed-container");
  const modalTimestampInfo = document.getElementById("modal-timestamp-info");
  const modalExternalLink = document.getElementById("modal-external-link");
  const closeModalBtn = document.getElementById("close-modal-btn");

  let isSubmitting = false;

  // 1. Fetch system health & stats
  async function fetchSystemHealth() {
    try {
      const res = await fetch("/api/health");
      if (res.ok) {
        const data = await res.json();
        const chunks = data.vector_store_chunks || 242;
        const modelName = (data.model || "llama-3.3-70b-versatile").replace("llama-", "Llama ");
        if (chunkCountFooter) chunkCountFooter.textContent = chunks;
        if (statChunks) statChunks.textContent = `${chunks} Chunks`;
        if (statLlm) statLlm.textContent = modelName;
      }
    } catch (e) {
      console.error("Health check error:", e);
    }
  }

  fetchSystemHealth();

  // Stats modal open/close
  if (statsBtn && statsModal) {
    statsBtn.addEventListener("click", () => {
      statsModal.classList.remove("hidden");
    });
  }

  if (closeStatsBtn && statsModal) {
    closeStatsBtn.addEventListener("click", () => {
      statsModal.classList.add("hidden");
    });
  }

  if (statsModal) {
    statsModal.addEventListener("click", (e) => {
      if (e.target === statsModal) {
        statsModal.classList.add("hidden");
      }
    });
  }

  // 2. Auto-expand textarea & toggle send button
  userInput.addEventListener("input", () => {
    userInput.style.height = "auto";
    userInput.style.height = `${Math.min(userInput.scrollHeight, 140)}px`;
    sendBtn.disabled = !userInput.value.trim() || isSubmitting;
  });

  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) {
        chatForm.dispatchEvent(new Event("submit"));
      }
    }
  });

  // 3. Handle suggestion chips
  if (suggestionsRow) {
    suggestionsRow.addEventListener("click", (e) => {
      const chip = e.target.closest(".suggestion-chip");
      if (chip && !isSubmitting) {
        const query = chip.getAttribute("data-query");
        if (query) {
          userInput.value = query;
          userInput.dispatchEvent(new Event("input"));
          chatForm.dispatchEvent(new Event("submit"));
        }
      }
    });
  }

  // 4. Handle Clear Chat
  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", () => {
      const welcomeCard = messagesContainer.querySelector(".welcome-card");
      const suggestions = messagesContainer.querySelector(".suggestions-row");
      messagesContainer.innerHTML = "";
      if (welcomeCard) messagesContainer.appendChild(welcomeCard);
      if (suggestions) messagesContainer.appendChild(suggestions);
    });
  }

  // 5. Send message
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query || isSubmitting) return;

    // Render user message
    appendUserMessage(query);
    userInput.value = "";
    userInput.style.height = "auto";
    sendBtn.disabled = true;
    isSubmitting = true;

    // Render typing indicator
    const typingElement = appendTypingIndicator();
    scrollToBottom();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query })
      });

      if (!response.ok) {
        throw new Error(`Server returned status: ${response.status}`);
      }

      const data = await response.json();
      typingElement.remove();
      appendAssistantMessage(data);
    } catch (err) {
      console.error("Chat error:", err);
      typingElement.remove();
      appendErrorMessage(
        "I encountered an issue processing your request. Please ensure the backend is running and your Groq API key is valid."
      );
    } finally {
      isSubmitting = false;
      sendBtn.disabled = !userInput.value.trim();
      scrollToBottom();
    }
  });

  // Render Functions
  function appendUserMessage(text) {
    const msg = document.createElement("div");
    msg.className = "message user-message";
    msg.innerHTML = `
      <div class="message-avatar">👤</div>
      <div class="message-content">
        <div class="bubble">${escapeHtml(text)}</div>
      </div>
    `;
    messagesContainer.appendChild(msg);
  }

  function appendTypingIndicator() {
    const msg = document.createElement("div");
    msg.className = "message assistant-message typing-msg";
    msg.innerHTML = `
      <div class="message-avatar bot-avatar"><img src="/static/beans_logo.png" alt="Beans.ai"></div>
      <div class="message-content">
        <div class="bubble">
          <div class="typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
      </div>
    `;
    messagesContainer.appendChild(msg);
    return msg;
  }

  function appendErrorMessage(errorText) {
    const msg = document.createElement("div");
    msg.className = "message assistant-message";
    msg.innerHTML = `
      <div class="message-avatar">⚠️</div>
      <div class="message-content">
        <div class="bubble" style="border-color: rgba(239, 68, 68, 0.4); color: #fca5a5;">
          ${escapeHtml(errorText)}
        </div>
      </div>
    `;
    messagesContainer.appendChild(msg);
  }

  function formatAnswerMarkdown(text) {
    if (!text) return "";

    // 1. Strip raw timestamps inside bracket notations or daggers like 【1†00:00】 or [1 @ 00:00] or (00:00)
    let cleaned = text
      .replace(/[\[【](\d+)(?:[†@:,\s][^\]】]*)?[\]】]/g, "[$1]")
      .replace(/【(\d+)】/g, "[$1]");

    // 2. Escape HTML
    let formatted = escapeHtml(cleaned);

    // 3. Bold text: **text** -> <strong>text</strong>
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // 4. Convert bullet points: * or -
    formatted = formatted.replace(/(?:^|\n)[*-]\s+(.+)/g, "<br>• $1");

    // 5. Convert numbered lists
    formatted = formatted.replace(/(?:^|\n)(\d+)\.\s+(.+)/g, "<br><strong>$1.</strong> $2");

    // 6. Line breaks
    formatted = formatted.replace(/\n\n/g, "<br><br>").replace(/\n/g, "<br>");

    // 7. Render interactive citation pills [1], [2] without timestamp text
    formatted = formatted.replace(/\[(\d+)\]/g, (match, p1) => {
      return `<a href="#source-ref-${p1}" class="citation-tag" title="Jump to source [${p1}]">[${p1}]</a>`;
    });

    return formatted;
  }

  function appendAssistantMessage(data) {
    const msg = document.createElement("div");
    msg.className = "message assistant-message";

    const formattedAnswer = formatAnswerMarkdown(data.answer);

    // Build Sources grid
    let sourcesHtml = "";
    if (data.sources && data.sources.length > 0) {
      const sourceCards = data.sources.map((s) => {
        const isYt = s.source_type === "youtube";
        const badgeClass = isYt ? "youtube" : "document";
        const icon = isYt ? "▶ YouTube" : "📄 Doc";
        const similarityPct = Math.round(s.similarity_score * 100);

        let actionBtnHtml = "";
        if (isYt && s.video_id) {
          actionBtnHtml = `
            <button class="source-action-btn play-video-btn" 
                    data-video-id="${s.video_id}" 
                    data-title="${escapeHtml(s.title)}" 
                    data-start="${s.start_seconds}" 
                    data-link="${s.deep_link}">
              ▶ Play @ ${s.timestamp_str}
            </button>
          `;
        } else {
          actionBtnHtml = `
            <a href="${s.deep_link}" target="_blank" rel="noopener" class="source-action-btn">
              Open Document ↗
            </a>
          `;
        }

        return `
          <div class="source-card" id="source-ref-${s.source_index}">
            <div class="source-card-top">
              <span class="source-type-pill ${badgeClass}">
                ${icon} [${s.source_index}]
              </span>
              <span class="similarity-score">${similarityPct}% Match</span>
            </div>
            <div class="source-card-title">${escapeHtml(s.title)}</div>
            <div class="source-card-snippet">"${escapeHtml(s.snippet)}"</div>
            ${actionBtnHtml}
          </div>
        `;
      }).join("");

      sourcesHtml = `
        <div class="sources-card">
          <div class="sources-header">
            <span>📚 Grounded Sources & Timestamps</span>
          </div>
          <div class="source-badges-grid">
            ${sourceCards}
          </div>
        </div>
      `;
    }

    msg.innerHTML = `
      <div class="message-avatar bot-avatar"><img src="/static/beans_logo.png" alt="Beans.ai"></div>
      <div class="message-content">
        <div class="bubble">
          <div>${formattedAnswer}</div>
          ${sourcesHtml}
        </div>
      </div>
    `;

    messagesContainer.appendChild(msg);

    // Attach listeners to newly created play video buttons
    msg.querySelectorAll(".play-video-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const vid = btn.getAttribute("data-video-id");
        const title = btn.getAttribute("data-title");
        const start = Math.floor(parseFloat(btn.getAttribute("data-start") || "0"));
        const link = btn.getAttribute("data-link");
        openVideoModal(vid, title, start, link);
      });
    });
  }

  // 6. Video Modal Management
  function openVideoModal(videoId, title, startSeconds, externalLink) {
    modalVideoTitle.textContent = title;
    modalTimestampInfo.textContent = `Timestamp cue: ${formatSeconds(startSeconds)} (${startSeconds}s)`;
    modalExternalLink.href = externalLink;

    // Inject iframe with autoplay and start parameter
    videoEmbedContainer.innerHTML = `
      <iframe 
        src="https://www.youtube.com/embed/${videoId}?start=${startSeconds}&autoplay=1&rel=0" 
        title="${escapeHtml(title)}" 
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
        allowfullscreen>
      </iframe>
    `;

    videoModal.classList.remove("hidden");
  }

  function closeVideoModal() {
    videoModal.classList.add("hidden");
    videoEmbedContainer.innerHTML = ""; // Stop video playback
  }

  if (closeModalBtn) closeModalBtn.addEventListener("click", closeVideoModal);
  if (videoModal) {
    videoModal.addEventListener("click", (e) => {
      if (e.target === videoModal) {
        closeVideoModal();
      }
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (videoModal && !videoModal.classList.contains("hidden")) {
        closeVideoModal();
      }
      if (statsModal && !statsModal.classList.contains("hidden")) {
        statsModal.classList.add("hidden");
      }
    }
  });

  // Utilities
  function formatSeconds(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});

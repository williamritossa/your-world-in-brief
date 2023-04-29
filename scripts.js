document.addEventListener("DOMContentLoaded", function() {
    const fadeInElements = document.querySelectorAll(".fade-in");

    function isElementVisible(element) {
        const rect = element.getBoundingClientRect();
        const windowHeight = (window.innerHeight || document.documentElement.clientHeight);

        return (rect.top <= windowHeight) && ((rect.top + rect.height) >= 0);
    }

    function checkVisibility() {
        let delay = 0;
        for (const element of fadeInElements) {
            if (isElementVisible(element) && !element.classList.contains("visible")) {
                element.style.animationDelay = `${delay}s`;
                delay += 0.2;
                element.classList.add("visible");
            } else {
                delay = 0;
            }
        }
    }

    // Add 'visible' class when the element is in the viewport
    checkVisibility();
    window.addEventListener("scroll", checkVisibility);
});


// Chatbot
const messages = [];
const messagesWithContext = [];
messages.push({ role: "system", content: "You are a chatbot on a page which shows summarise of news articles. Your job is to answer questions that the user has about the articles. You will be given sections from the article which may be related to help you answer their question." });

// Convert embeddings to JSON
let embeddings;
(async () => {
  embeddings = await getEmbeddings();
})();

async function getAssistantResponse(userMessage) {
    const searchTermVector = await getSearchTermVector(userMessage); // Turn the user's question into a searchTermVector.
    const topResults = getTopNResults(embeddings, searchTermVector, 5); // Get the top N related article sections using the searchTermVector.

    // Append the related sections as context to the user's message.
    const relatedSections = topResults.join("\n\n- ");
    const messageWithContext = `Below is a question from the user they have about a news articles. Here are some extracts from various articles which may be useful context for you to form your answer. You may quote relevant and specific sections of the context if it helps but your goal is to produce a succinct answer. If the answer is not contained in the context, do your best to answer it without making up anything or hallucinating.\n\n${relatedSections}\n\nUsers question: ${userMessage}\n\nNote that the context may not be relevant or necessary.}`

    // Add the user message with context to the messagesWithContext array
    messagesWithContext.push({ role: "user", content: messageWithContext });

    // Keep only the last 3 user messages with context
    if (messagesWithContext.length > 3) {
        messagesWithContext.shift();
    }

    // A function to get the response from the OpenAI API
    const response = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${OPENAI_API_KEY}`,
        },
        body: JSON.stringify({
            model: "gpt-3.5-turbo",
            messages: [...messagesWithContext, ...messages],
            temperature: 0,
        }),
    });

    const data = await response.json();
    return data.choices[0].message.content;
}

document.addEventListener("DOMContentLoaded", function() {
    const chatbotButton = document.getElementById("chatbot-button");
    const chatbotBox = document.getElementById("chatbot-box");

    chatbotButton.addEventListener("click", () => {
        chatbotBox.classList.toggle("d-none");
    });

    const chatbotSend = document.getElementById("chatbot-send");
    const chatbotInput = document.getElementById("chatbot-input");
    const chatbotMessages = document.getElementById("chatbot-messages");


    chatbotSend.addEventListener("click", async () => {
        sendMessage();
    });

    chatbotInput.addEventListener("keydown", (event) => {
        if (event.keyCode === 13) {
            event.preventDefault();
            sendMessage();
        }
    });

    const sendMessage = async () => {
        const userMessage = chatbotInput.value.trim();
        if (userMessage) {
            chatbotMessages.innerHTML += `<div class="message-container"><div class="message right">${userMessage}</div></div>`;
            chatbotInput.value = "";

            // Add typing dots for AI's message
            chatbotMessages.innerHTML += `
                <div id="typing-dots" class="message-container">
                    <div class="message left">
                        <div class="typing typing-1"></div>
                        <div class="typing typing-2"></div>
                        <div class="typing typing-3"></div>
                    </div>
                </div>`;

            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
            chatbotBox.scrollTop = chatbotBox.scrollHeight;

            const assistantMessage = await getAssistantResponse(userMessage);

            // Remove typing dots
            const typingDots = document.getElementById("typing-dots");
            typingDots.parentNode.removeChild(typingDots);

            chatbotMessages.innerHTML += `<div class="message-container"><div class="message left">${assistantMessage}</div></div>`;

            messages.push({ role: "assistant", content: assistantMessage });
            messages.push({ role: "user", content: userMessage });

            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
            chatbotBox.scrollTop = chatbotBox.scrollHeight;
        }
    };
});


// Embeddings
function pythonListToJSONArray(pythonListString) {
  const jsonString = pythonListString
    .replace(/'/g, `"`)
    .replace(/None/g, "null")
    .replace(/True/g, "true")
    .replace(/False/g, "false");
  return JSON.parse(jsonString);
}

function dotProduct(a, b) {
  let sum = 0;
  for (let i = 0; i < a.length; i++) {
    sum += a[i] * b[i];
  }
  return sum;
}

function magnitude(a) {
  let sum = 0;
  for (let i = 0; i < a.length; i++) {
    sum += a[i] * a[i];
  }
  return Math.sqrt(sum);
}

function cosineSimilarity(a, b) {
  return dotProduct(a, b) / (magnitude(a) * magnitude(b));
}

async function getEmbeddings() {
    return embeddingsData.map((row) => ({
        article_uuid: row.article_uuid,
        embedding_uuid: row.embedding_uuid,
        text: row.text,
        embedding: pythonListToJSONArray(row.embedding),
    }));
}

async function getSearchTermVector(searchTerm) {
  const response = await fetch("https://api.openai.com/v1/embeddings", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      input: searchTerm,
      model: "text-embedding-ada-002",
    }),
  });

  const data = await response.json();
  return data.data[0].embedding;
}


function getTopNResults(embeddings, searchTermVector, n) {
    embeddings.forEach((row) => {
        row.similarity = cosineSimilarity(row.embedding, searchTermVector);
    });

  embeddings.sort((a, b) => b.similarity - a.similarity);
  return embeddings.slice(0, n).map((row) => row.text);
}

// Usage:
/*
getEmbeddings().then(async (embeddings) => {
  const searchTerm = "Credit Suisse and liabilities";
  const searchTermVector = await getSearchTermVector(searchTerm);
  const topResults = getTopNResults(embeddings, searchTermVector, 5);
  console.log(topResults);
});
*/

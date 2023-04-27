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
const OPENAI_API_KEY = "OPENAI_API_KEY"; // Replace with your OpenAI API key
async function getAssistantResponse(message) {
    // A function to get the response from the OpenAI API
    const response = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${OPENAI_API_KEY}`, // Replace with your OpenAI API key
        },
        body: JSON.stringify({
            model: "gpt-3.5-turbo",
            messages: [...messages, { role: "user", content: message }],
            temperature: 0,
        }),
    });

    const data = await response.json();
    return data.choices[0].message.content;
}

const messages = []
messages.push({ role: "system", content: "You are a chatbot on a page which shows summarise of news articles. Your job is to answer questions that the user has about the articles. You will be given sections from the article which may be related to help you answer their question." });

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

            messages.push({ role: "user", content: userMessage });
            messages.push({ role: "assistant", content: assistantMessage });

            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
            chatbotBox.scrollTop = chatbotBox.scrollHeight;
        }
    };
});
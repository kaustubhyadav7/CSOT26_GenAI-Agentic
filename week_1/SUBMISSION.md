## Week1 Submission- Multi Turn Chatbot
This is basically a terminal based multi- turn chatbot using openrouter.ai and concepts of OOPs. It offers user a choice to choose among certain number of models and then responds to the user's messages alternatively.

## HOW IT WORKS?????
Basically the entire thing revolves around the class- Chatagent. And within this class self.messages is esentially what constitutes the memory of the chatbot. Inside the class there are certain methods like __init__ which is basically trhe constructor of the class.
The standalone fucntion is the **run_chatbot** which basically provides the user with the choice to pick his/her preferred model and then calls another function which is the **call_model**, esentially the heart of this chatbot, what it does is takes the user input, appends it to the memory, sends it to the model, extracts the reply and appends it to memory further. additionally the except block is also added to it which also performs a very important task, to ensure that if in case some error occurs the alternative nature of user's message and model's response is retained by popping the last user input that gave error and printing the error string.
Further there is a function **_trim_history**, which basically ensures that the model doesm't get too slow in replying by trimming memory prior to twice the number of maximum turns given.Thus the token cost and time is managed.

## Key Decisions
**Configurable class:** I made the model, system_prompt, and max_turns into parameters of the ChatAgent class instead of prefixing them, so the same class can be set up differently without changing the code.

**max_turns = 25:** I chose 25 as a middle ground. A bigger buffer lets the bot remember more of the conversation but sends more tokens each call (slower, more cost); a smaller one is cheaper but the bot forgets things faster. 25 turns felt like enough memory while keeping the history manageable.

**Rolling buffer (`_trim_history`):** Since the model has no memory of its own, the full message list is resent on every call, so it grows every turn. If left unchecked this raises token cost and can eventually exceed the model's context limit. So I keep only the most recent max_turns × 2 messages and always preserve the system message at index 0, because it holds the bot's instructions and would otherwise be the first thing dropped.

**Error handling (`try/except`):** I didn't plan this initially, but while testing I kept hitting 429 rate-limit errors from the free models, which crashed the whole program. So I wrapped the API call in try/except. On failure it shows the error instead of crashing, and pops the user message that was just added, so the user/assistant turns stay alternating for the next call.

**Model choice:** I offered 5 free models from different providers from openroute.ai (Google Gemma, Meta Llama, NVIDIA Nemotron, DeepSeek, Liquid) so the user can compare them. The ChatAgent is model-agnostic and works with any OpenRouter model ID. I used a dictionary with `.get()` so an invalid menu choice safely defaults to model 1.

## Note on Structure
I implemented the final ChatAgent task **directly inside chatbot.py rather than keeping a separate basic Build 2 loop**, so chatbot.py contains the complete class-based version.

## Challenges / What I Learned
I started this with no background in LLM APIs at all — I hadn't even used Python in VS Code before, only in IDLE. The biggest concept I learned is that the model is stateless: it remembers nothing between calls, and the "memory" is just the message list that the chatbot keeps and resends each time. I also learned how the response object is nested (response.choices[0].message.content), what a class is and how methods use self, and why conversation history has to be managed manually.
A few things didn't work along the way. I first hardcoded model names like google/gemma-3-27b-it:free, but got 404 errors because free model names on OpenRouter change and expire — I learned to pull the current model IDs from the OpenRouter site directly. I also repeatedly hit 429 rate limits, which taught me that free models share a tight combined request limit, and that experience is what made me add the error handling.


## How to Run
1. `pip install openai python-dotenv`
2. Create a `.env` file with `OPENROUTER_API_KEY=your_key`
3. Run `python chatbot.py`
4. Choose a model from the menu and start chatting. Type `exit` or `quit` to stop.
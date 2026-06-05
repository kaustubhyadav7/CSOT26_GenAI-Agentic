import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
class ChatAgent:
    def __init__(self, model, system_prompt="You are a helpful assistant.", max_turns=25):
        self.model = model                  # stores the free model chosen from openrouter.ai
        self.max_turns = max_turns          #buffer limit (for trimming later)
        self.messages = [                    #agent's conversation record
                    {"role": "system", "content": system_prompt}
        ]
        self.client = OpenAI(                #agent's connection to OpenRouter
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
    def call_model(self, user_input):
        self.messages.append({"role": "user", "content": user_input})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
            )
            reply = response.choices[0].message.content
        except Exception as e:
            reply = f"[Error talking to model: {e}]"
            self.messages.pop()
            return reply

        self.messages.append({"role": "assistant", "content": reply})

        self._trim_history()       
        return reply
    def _trim_history(self):
        system_message = self.messages[0]          
        conversation = self.messages[1:]            # everything after system

        max_messages = self.max_turns * 2           # each turn = user + assistant = 2 msgs
        if len(conversation) > max_messages:
            conversation = conversation[-max_messages:]   # keep only the most recent

        self.messages = [system_message] + conversation   # rebuild
def run_chatbot():
    # Menu of models for the user to choose
    models = {
        "1": "google/gemma-4-26b-a4b-it:free",
        "2": "meta-llama/llama-3.3-70b-instruct:free",
        "3": "nvidia/nemotron-3-super-120b-a12b:free",
        "4": "deepseek/deepseek-r1:free",
        "5": "liquid/lfm-2.5-1.2b-thinking:free",
    }

    print("Choose a model:")
    for key, name in models.items():
        print(f"  {key}. {name}")

    choice = input("Enter number (default 1): ")
    model = models.get(choice, models["1"])   # fall back to model 1 if chosen model fails

    #Creating the agent with the chosen model
    agent = ChatAgent(model=model)

    print(f"\nChat started with {model}. Type 'exit' to quit.\n")

    #Conversation loop
    while True:
        user_input = input("[YOU] ")
        if user_input == "exit" or user_input == "quit":
            print("Thanks for using! Have a nice day!")
            break
        reply = agent.call_model(user_input)
        print("[MODEL]", reply)    

if __name__ == "__main__":
     run_chatbot()
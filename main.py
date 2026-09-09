from agent.llm import ask_model
from agent.memory import load_memory
from agent.memory import save_memory

def main() -> None:
    print("Mini Coding Agent")
    conversation = load_memory()
    while True:
        print("What would you like to work on?\n")
        #print("Type 'exit' to terminate this program.\n")
        task = input("-----------------------------------\n")
        if task.lower() == "exit":
            break
        conversation.append(
            {
                "role": "user", 
                "content": task
            }
        )
        print(ask_model(conversation))
        save_memory(conversation)

if __name__ == "__main__":
    main()
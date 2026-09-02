from agent.llm import ask_model


def main() -> None:
    print("Mini Coding Agent")
    task = input("What would you like to work on?\n")
    print(ask_model(task))

if __name__ == "__main__":
    main()
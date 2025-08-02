from graph_setup import build_graph

def main():
    """
    The main entry point for the application.
    """
    graph = build_graph()

    print("Welcome to your Multi-AI Agent Personal Assistant!")
    print("How can I help you today?")

    while True:
        user_query = input("> ")
        if user_query.lower() == "exit":
            break

        response = graph.invoke({"user_query": user_query})
        print(response["response"])

if __name__ == "__main__":
    main()
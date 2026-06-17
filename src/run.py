from src.agent import run_agent

history = []

print("STM32 Agentic AI Ready (type 'exit' to quit)")

while True:
    q = input("\nQuestion: ")
    if q.lower() == "exit":
        break

    answer, steps, history, sources = run_agent(q, history)

    print("\n--- 思考步驟 ---")
    for s in steps:
        print(s)

    print("\n--- 回答 ---")
    print(answer)

    if sources:
        print("\n--- 參考來源 ---")
        for s in sources[:3]:
            print(f"  • {s}")
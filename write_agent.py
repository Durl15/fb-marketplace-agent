code = open("agent_clean.py").read()
open("marketplace_agent.py", "w").write(code)
print("Written:", len(code.splitlines()), "lines")
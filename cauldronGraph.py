import requests

BASE = "https://hackutd2025.eog.systems/api/Information"
resp = requests.get(f"{BASE}/cauldrons")
resp.raise_for_status()
cauldrons = resp.json()

resp = requests.get(f"{BASE}/network")
resp.raise_for_status()
edges = resp.json().get("edges") or []

graph = [[0 for i in range(len(cauldrons) + 1)] for j in range(len(cauldrons) + 1)]

# fill the graph with all travel distances between cauldrons and market
for e in edges:
    From = int(e.get("from")[-3:])
    if "market" in e.get("to"):
        To = 0
    else:
        To = int(e.get("to")[-3:])
    graph[From][To] = graph[To][From] = e.get("travel_time_minutes")

# code to test graph generation
for row in graph:
    print(row)


# need to implement witch algorithm which uses the least amount of witches possible, prevents cauldrons from overflowing, and minmizes travel distance
# it also needs to consider witch carrying capacity
# if possible, use machine learning here to generate the optimal paths
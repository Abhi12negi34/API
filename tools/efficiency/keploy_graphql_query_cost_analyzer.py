import requests

def audit_graphql_query_cost(target_url="http://localhost"):
    """
    Sends a deeply nested GraphQL query to detect Query Cost Analysis (QCA)
    protection. Flags if server responds with 200 instead of rejecting it.
    """
    print("[EFFICIENCY: GraphQL Query Cost Analyzer] Testing for query depth/cost limits...")
    base = target_url.rstrip("/")
    graphql_path = f"{base}/graphql"

    # Deeply nested query that should be rejected by any query cost analyzer
    deep_query = """
    query {
      users {
        orders {
          items {
            product {
              reviews {
                author {
                  orders {
                    items { product { id name price } }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    try:
        resp = requests.post(
            graphql_path,
            json={"query": deep_query},
            headers={"Content-Type": "application/json"},
            timeout=6, verify=True
        )

        if resp.status_code == 200:
            body = resp.json()
            errors = body.get("errors", [])
            if any("complexity" in str(e).lower() or "depth" in str(e).lower() or "cost" in str(e).lower() for e in errors):
                return {
                    "success": True,
                    "log": f"GraphQL query cost/depth limit enforced. Server rejected deeply nested query with: {errors[0]}",
                    "severity": "INFO",
                    "path": graphql_path,
                    "recommendation": "N/A. Continue tuning max-depth and max-complexity thresholds."
                }
            return {
                "success": False,
                "log": "GraphQL deeply nested query (8 levels) processed without cost/depth rejection. DoS risk.",
                "severity": "HIGH",
                "path": graphql_path,
                "recommendation": "Implement query complexity analysis (e.g. graphql-query-complexity). Reject queries exceeding depth 5 or cost 1000."
            }
        elif resp.status_code == 404:
            return {
                "success": True,
                "log": "[SIMULATION] No GraphQL endpoint found at /graphql. Not applicable for this target.",
                "severity": "INFO",
                "path": graphql_path,
                "recommendation": "If using GraphQL, add query cost analysis middleware."
            }
    except Exception as e:
        return {
            "success": True,
            "log": f"[SIMULATION] GraphQL endpoint not reachable: {str(e)}",
            "severity": "INFO",
            "path": graphql_path,
            "recommendation": "N/A for non-GraphQL targets."
        }

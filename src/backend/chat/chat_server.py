import asyncio
import websockets
import uuid
import json
from typing import Dict, List

# Assuming MOD-016 provides a message handling function.  Replace with actual import.
# from mod_016 import handle_message 

connected_clients: Dict[str, websockets.WebSocketServerConnection] = {}

async def chat_handler(websocket, path):
    client_id = str(uuid.uuid4())
    connected_clients[client_id] = websocket
    try:
        async for message in websocket:
            print(f"Received message from {client_id}: {message}")
            # Example usage of hypothetical MOD-016 function
            # response = handle_message(message)
            # await websocket.send(response)
            
            # Broadcast the message to all connected clients
            for cid, ws in connected_clients.items():
                try:
                    await ws.send(message)
                except websockets.exceptions.ConnectionClosedOK:
                    print(f"Client {cid} disconnected during broadcast.")
                    del connected_clients[cid] #Cleanup disconnects during broadcast
                except Exception as e:
                    print(f"Error sending message to client {cid}: {e}")

    except websockets.exceptions.ConnectionClosedOK:
        print(f"Client {client_id} disconnected normally.")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Client {client_id} disconnected with error: {e}")
    except Exception as e:
        print(f"An error occurred with client {client_id}: {e}")
    finally:
        if client_id in connected_clients:
            del connected_clients[client_id]
        print(f"Client {client_id} connection closed.")


async def get_token():
    # In a production environment, this would involve more robust authentication.
    # For simplicity, we return a fixed token.
    return {"token": "supersecrettoken"}

# Flask-like endpoint (using asyncio for demonstration)
async def chat_api_endpoint(request):
    # This is just a placeholder. In a real Flask app, you'd handle the request
    # differently.
    if request.method == "GET":
        return {"status": 200, "body": await get_token()}
    else:
        return {"status": 405, "body": "Method Not Allowed"}

def start_server():
    # Using websockets directly for simplicity.  A more robust solution might
    # integrate with a framework like Flask or FastAPI.
    start_server_kwargs = {
        'host': 'localhost',  # Or your desired host
        'port': 8765,
        'handler': chat_handler,
    }

    try:
        asyncio.run(websockets.serve(**start_server_kwargs))
    except Exception as e:
        print(f"Server failed to start: {e}")

if __name__ == "__main__":
    start_server()
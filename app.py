from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import uuid
from langchain_core.messages import ToolMessage
from src.Graph import Graphing
from src.utilities import _print_event
import os 
from langchain_groq import ChatGroq
from src.Tools import initalize_rag


#initalize_rag()


# Set environment variable for API key
os.environ['TAVILY_API_KEY'] = ""

# Initialize the chatbot model
llm = ChatGroq(api_key="", model="llama-3.2-11b-vision-preview")

app = Flask(__name__)
socketio = SocketIO(app)

# Initialize the graph with the model
graph = Graphing(llm=llm)
graph.Tool_binding_llm_agent()
graph = graph.Build()

# Initialize thread id for each user session
thread_id = str(uuid.uuid4())

# Config settings (can be customized per user)
config = {
    "configurable": {
        "passenger_id": "3442 587242",  # This could be dynamic per user
        "thread_id": thread_id,
    }
}

_printed = set()

@app.route('/')
def chat():
    return render_template('chat.html')

@socketio.on('message')
def handle_message(message):
    """Handle incoming messages from the user and send chatbot responses."""
    
    # Stream chatbot events and collect responses
    events = graph.stream({"messages": ("user", message)}, config, stream_mode="values")
    
    chatbot_responses = []  # Collect responses in a list
    for event in events:
        chatbot_response = _print_event(event, _printed)
        chatbot_responses.append(chatbot_response)  # Append each response
    
    emit('response', {'messages': chatbot_responses})  # Send the list of responses back to the client

    # Handle tool invocations, approvals, etc.
    snapshot = graph.get_state(config)
    while snapshot.next:
        user_input = "y"  # Example approval input
        if user_input.strip() == "y":
            result = graph.invoke(None, config)
        else:
            result = graph.invoke(
                {
                    "messages": [
                        ToolMessage(
                            tool_call_id=event["messages"][-1].tool_calls[0]["id"],
                            content=f"API call denied by user. Reasoning: '{user_input}'. Continue assisting, accounting for the user's input.",
                        )
                    ]
                },
                config,
            )
        snapshot = graph.get_state(config)

if __name__ == '__main__':
    socketio.run(app, debug=True)

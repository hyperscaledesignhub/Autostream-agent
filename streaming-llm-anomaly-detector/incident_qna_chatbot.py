"""
Production Incident Q&A Chatbot using OpenAI ChatGPT API
This chatbot answers questions about production incidents using LangGraph and OpenAI's API.
"""

import os
import pandas as pd
import uuid
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.tools import tool
from langchain.tools.retriever import create_retriever_tool
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# Load environment variables from .env file
load_dotenv()

# Setup the LLM using OpenAI's ChatGPT
model = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4"),  # Using GPT-4 for better incident analysis
    temperature=0.3  # Lower temperature for more factual responses about incidents
)

# Setup the Embedding model
embedding = OpenAIEmbeddings(
    model="text-embedding-3-large"
)

# Create incident severity database
incident_data = {
    "Incident ID": ["INC001", "INC002", "INC003", "INC004", "INC005"],
    "Severity": ["Critical", "High", "Medium", "High", "Critical"],
    "Service": ["Payment Gateway", "User Authentication", "Database", "API Gateway", "Load Balancer"],
    "Resolution Time (hours)": [4, 2, 6, 3, 5],
    "Root Cause": ["Memory Leak", "Certificate Expiry", "Deadlock", "Rate Limiting", "Network Partition"]
}

incident_df = pd.DataFrame(incident_data)

@tool
def get_incident_severity(incident_id: str) -> str:
    """
    Returns the severity level of an incident given its ID.
    Returns 'Not Found' if the incident ID doesn't exist.
    """
    # Filter for matching incident ID
    match = incident_df[incident_df["Incident ID"].str.contains(incident_id, case=False)]
    
    if len(match) == 0:
        return "Not Found"
    else:
        return match["Severity"].iloc[0]

@tool
def get_incident_resolution_time(incident_id: str) -> str:
    """
    Returns the resolution time in hours for a given incident ID.
    Returns -1 if the incident ID doesn't exist.
    """
    # Filter for matching incident ID
    match = incident_df[incident_df["Incident ID"].str.contains(incident_id, case=False)]
    
    if len(match) == 0:
        return "Not Found"
    else:
        return f"{match['Resolution Time (hours)'].iloc[0]} hours"

@tool
def get_incidents_by_severity(severity: str) -> str:
    """
    Returns all incidents of a given severity level (Critical, High, Medium, Low).
    """
    # Filter incidents by severity
    matches = incident_df[incident_df["Severity"].str.contains(severity, case=False)]
    
    if len(matches) == 0:
        return f"No incidents found with severity: {severity}"
    else:
        incidents = matches[["Incident ID", "Service", "Root Cause"]].to_dict('records')
        return str(incidents)

@tool
def get_incident_statistics() -> str:
    """
    Returns overall statistics about production incidents.
    """
    stats = {
        "Total Incidents": len(incident_df),
        "Critical Incidents": len(incident_df[incident_df["Severity"] == "Critical"]),
        "Average Resolution Time": f"{incident_df['Resolution Time (hours)'].mean():.1f} hours",
        "Most Affected Service": incident_df["Service"].mode()[0] if len(incident_df) > 0 else "N/A"
    }
    return str(stats)

# Load and process incident document
def setup_incident_retriever():
    """
    Load, chunk and index the contents of the production incident document.
    Returns a retriever tool for incident details.
    """
    # Load PDF document from data folder
    loader = PyPDFLoader("./data/Production Incident History Document.pdf")
    docs = loader.load()
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024, 
        chunk_overlap=256,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    splits = text_splitter.split_documents(docs)
    
    # Create a vector store with Chroma
    incident_store = Chroma.from_documents(
        documents=splits,
        embedding=embedding,
        collection_name="production_incidents"
    )
    
    # Create retriever tool
    get_incident_details = create_retriever_tool(
        incident_store.as_retriever(search_kwargs={"k": 3}),
        name="Get_Incident_Details",
        description="""
        This store contains detailed information about production incidents including:
        - Incident timelines and chronology
        - Root cause analysis
        - Impact assessment
        - Resolution steps taken
        - Lessons learned
        - Prevention measures
        - Technical details and logs
        Use this to answer questions about specific incidents, patterns, or historical trends.
        """
    )
    
    return get_incident_details

# Setup the incident retriever
get_incident_details = setup_incident_retriever()

# Create a System prompt for incident analysis
system_prompt = SystemMessage("""
    You are an expert Site Reliability Engineer (SRE) and incident response specialist.
    You help teams understand production incidents, their root causes, and prevention strategies.
    
    Your responsibilities:
    1. Provide detailed analysis of production incidents using ONLY the available tools and documents
    2. Identify patterns and trends in incident history
    3. Suggest prevention measures based on past incidents
    4. Explain technical root causes in clear terms
    5. Help with post-mortem analysis and lessons learned
    
    When answering questions:
    - Be factual and precise about incident details
    - Reference specific incident IDs when available
    - Provide actionable insights for prevention
    - Highlight critical patterns or recurring issues
    - Use the incident document for detailed information
    
    Do NOT make up incident details. Only use information from the provided tools and documents.
    """
)

# Create a list of tools available
tools = [
    get_incident_severity,
    get_incident_resolution_time,
    get_incidents_by_severity,
    get_incident_statistics,
    get_incident_details
]

# Create memory across questions in a conversation
checkpointer = MemorySaver()

# Create an Incident QnA Agent
incident_QnA_agent = create_react_agent(
    model=model,
    tools=tools,
    state_modifier=system_prompt,
    debug=False,
    checkpointer=checkpointer
)

def test_single_query():
    """
    Test the agent with a single incident query.
    """
    # Setup configuration with thread ID for memory
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    # Test the agent with an incident-related input
    inputs = {"messages": [
        HumanMessage("What were the major incidents last month and their root causes?")
    ]}
    
    print("\n" + "="*50)
    print("Testing single query...")
    print("="*50)
    
    # Use streaming to print responses
    for stream in incident_QnA_agent.stream(inputs, config, stream_mode="values"):
        message = stream["messages"][-1]
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()

def simulate_incident_conversation():
    """
    Simulate a conversation about production incidents.
    """
    # Incident-focused conversation
    user_inputs = [
        "Hello, I need help understanding our recent production incidents",
        "What incidents do we have in the system?",
        "Show me all critical incidents",
        "What was the root cause of the payment gateway incident?",
        "How long did it take to resolve?",
        "What patterns do you see in our incidents?",
        "What preventive measures should we take?",
        "Thank you for the analysis"
    ]
    
    # Create a new thread for the conversation
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    print("\n" + "="*50)
    print("Starting incident analysis conversation...")
    print("="*50)
    
    for user_input in user_inputs:
        print(f"\n{'─'*40}")
        print(f"USER: {user_input}")
        
        # Format the user message
        user_message = {"messages": [HumanMessage(user_input)]}
        
        # Get response from the agent
        ai_response = incident_QnA_agent.invoke(user_message, config=config)
        
        # Print the response
        print(f"AGENT: {ai_response['messages'][-1].content}")

def analyze_incident_patterns():
    """
    Analyze patterns and trends in incidents.
    """
    print("\n" + "="*50)
    print("Analyzing incident patterns...")
    print("="*50)
    
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    analysis_queries = [
        "What are the statistics of all incidents?",
        "Which services are most affected by incidents?",
        "What are the common root causes?",
        "How can we reduce incident frequency?"
    ]
    
    for query in analysis_queries:
        print(f"\n{'─'*40}")
        print(f"ANALYSIS: {query}")
        
        user_message = {"messages": [HumanMessage(query)]}
        ai_response = incident_QnA_agent.invoke(user_message, config=config)
        print(f"RESULT: {ai_response['messages'][-1].content}")

def main():
    """
    Main function to run the incident Q&A chatbot.
    """
    print("Production Incident Q&A Chatbot")
    print("="*50)
    
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("\nError: OPENAI_API_KEY not found!")
        print("Please add your OpenAI API key to the .env file")
        return
    
    while True:
        print("\n" + "="*50)
        print("Incident Analysis Menu:")
        print("1. Test single incident query")
        print("2. Simulate incident conversation")
        print("3. Analyze incident patterns")
        print("4. Interactive incident chat")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == "1":
            test_single_query()
        elif choice == "2":
            simulate_incident_conversation()
        elif choice == "3":
            analyze_incident_patterns()
        elif choice == "4":
            # Interactive chat mode for incidents
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            print("\n" + "="*50)
            print("Interactive Incident Analysis Mode")
            print("Ask questions about production incidents")
            print("Type 'exit' to quit")
            print("="*50)
            
            while True:
                user_input = input("\nYOU: ")
                if user_input.lower() == 'exit':
                    break
                
                user_message = {"messages": [HumanMessage(user_input)]}
                ai_response = incident_QnA_agent.invoke(user_message, config=config)
                print(f"AGENT: {ai_response['messages'][-1].content}")
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
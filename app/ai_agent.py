from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import database, config

full_chain = None

def init_agent():
    """Initializes the three-agent sequential chain."""
    global full_chain
    
    print("🚀 Initializing Sequential AI Agent...")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=config.GOOGLE_API_KEY)
    db_engine = database.engine()
    db = SQLDatabase(db_engine)

    # --- Chain 1: Query Reformulator ---
    reformulate_template = "Based on the user's question, reformulate it into a direct, unambiguous question for a data analyst. Include the User ID. Original Question: {question}, User ID: {user_id}. Reformulated Question:"
    reformulate_prompt = PromptTemplate.from_template(reformulate_template)
    query_reformulator_chain = reformulate_prompt | llm | StrOutputParser()

    # --- Chain 2: SQL Agent ---
    sql_agent_executor = create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=True)

    # --- Chain 3: Response Synthesizer ---
    synthesize_template = """
    You are a friendly and helpful AI financial assistant. The user asked: "{original_question}".
    The database returned: "{sql_data}".
    Formulate a helpful, natural language response with visually appealing markdown.
    """
    synthesize_prompt = PromptTemplate.from_template(synthesize_template)
    response_synthesizer_chain = synthesize_prompt | llm | StrOutputParser()

    # --- Combine into the full sequential chain ---
    full_chain = (
        {"reformulated_question": query_reformulator_chain, "original_question": lambda x: x["question"]}
        | RunnablePassthrough.assign(
            sql_data=lambda x: sql_agent_executor.invoke({"input": x["reformulated_question"]})["output"]
        )
        | response_synthesizer_chain
    )
    
    print("🤖 Sequential AI Agent is ready.")

# Initialize the agent on application startup
try:
    init_agent()
except Exception as e:
    print(f"🔥 Critical error during AI Agent initialization: {e}")
    full_chain = None

from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
import asyncio


class GenericAgent:
    def __init__(self, agent_id: str, name: str, system_prompt: str):
        self.agent_id = agent_id
        self.name = name
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

        backstory = system_prompt if system_prompt else """
        You are a versatile and intelligent assistant that helps users with a wide variety of questions and tasks.
        You provide accurate, helpful, and friendly responses to any query.

        Your capabilities include:
        - Answering general knowledge questions
        - Providing explanations and educational content
        - Helping with problem-solving
        - Offering advice and recommendations
        - Engaging in meaningful conversations

        Always be helpful, accurate, and considerate in your responses.
        """

        self.agent = Agent(
            role="Intelligent General Assistant",
            goal="To provide useful, accurate, and helpful responses to a wide variety of user questions and requests",
            backstory=backstory,
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    async def process_message(self, message: str) -> str:
        """Process user message and return appropriate response."""
        try:
            task = Task(
                description=f"""
                Process the following user message and provide an appropriate, helpful response:

                User Message: "{message}"
                Agent ID: {self.agent_id}

                Instructions:
                - Provide a helpful, relevant, and friendly response to the user's message
                - Be accurate and informative
                - If the user asks for specific information, provide detailed and useful content
                - Maintain a conversational and engaging tone
                - If you're unsure about something, be honest about it

                Provide a complete and thoughtful response that addresses the user's needs.
                """,
                expected_output="A helpful, accurate, and relevant response to the user's message",
                agent=self.agent
            )

            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                process=Process.sequential,
                verbose=True
            )

            # Run the crew asynchronously
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crew.kickoff)

            return str(result)

        except Exception as e:
            print(f"Error processing message with GenericAgent: {str(e)}")
            return f"Sorry, I encountered an error while processing your request: {str(e)}"
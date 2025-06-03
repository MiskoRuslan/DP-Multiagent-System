from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from backend.core.tools.weather_tools import get_current_weather, get_weather_forecast
import asyncio


class SmartWeatherAgent:
    def __init__(self, agent_id: str, name: str, system_prompt: str):
        self.agent_id = agent_id
        self.name = name
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

        # Set up backstory
        backstory = system_prompt if system_prompt else """
        You are an intelligent weather assistant that provides accurate weather information.
        You have access to tools to get current weather and weather forecasts for any city.

        When users ask about weather, you should:
        1. Use the current_weather tool for current conditions
        2. Use the weather_forecast tool for multi-day forecasts
        3. Choose the appropriate tool based on the user's request
        4. Provide helpful and informative responses

        Always be friendly and helpful in your responses.
        """

        # Create the agent with tools
        self.agent = Agent(
            role='Intelligent Weather Assistant',
            goal='Provide accurate weather information using appropriate tools based on user requests',
            backstory=backstory,
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[get_current_weather, get_weather_forecast]
        )

    async def process_message(self, message: str) -> str:
        """Process user message and return appropriate response using CrewAI agents and tools."""
        try:
            task = Task(
                description=f"""
                Analyze the user's message and respond appropriately using available weather tools.

                User Message: "{message}"
                Agent ID: {self.agent_id}

                Instructions:
                - If the user asks for current weather, use the current_weather tool
                - If the user asks for a forecast or weather for multiple days, use the weather_forecast tool
                - If the user specifies a number of days, use that number with the forecast tool
                - If no specific number is mentioned for forecasts, default to 7 days
                - For general weather questions without specifying current vs forecast, use current_weather
                - Always provide helpful and informative responses
                - Extract city names from the user's message carefully

                Provide a complete response that directly addresses the user's weather query.
                """,
                expected_output="A helpful weather response using the appropriate tools based on the user's request",
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
            print(f"Error processing message with SmartWeatherAgent: {str(e)}")
            return f"Sorry, I encountered an error while processing your weather request: {str(e)}"
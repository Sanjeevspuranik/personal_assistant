from typing import Annotated, List, Any, Optional, Dict
from typing_extensions import TypedDict
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field
from sidekick_tools import playwright_tools, other_tools
import uuid
import asyncio
from datetime import datetime
load_dotenv(override=True)


class State(TypedDict):
    messages: Annotated[List[Any], add_messages]
    success_criteria: str
    feedback_on_work: Optional[str]
    success_criteria_met: bool
    user_input_needed: bool


class EvaluatorOutput(BaseModel):
    feedback: str = Field(description="Feedback on the assistant's response")
    success_criteria_met: bool = Field(
        description="Whether the success criteria have been met")
    user_input_needed: bool = Field(
        description="True if more input is needed from the user, or clarifications, or the assistant is stuck")


class Sidekick:
    def __init__(self) -> None:
        self.worker_llm_with_tools = None
        self.evaloator_ll_with_output = None
        self.tools = None
        self.graph = None
        self.ll_with_tools = None
        self.sidekick_id = str(uuid.uuid4())
        self.memory = MemorySaver()
        self.browser = None
        self.playwright = None

    async def setup(self):
        self.tools, self.browser, self.playwright = await playwright_tools()
        self.tools += await other_tools()
        worker_llm = ChatOpenAI(model="gpt-4o-mini")
        self.worker_llm_with_tools = worker_llm.bind_tools(self.tools)
        evaluator_llm = ChatOpenAI(model="gpt-4o-mini")
        self.evaloator_ll_with_output = evaluator_llm.with_structured_output(
            EvaluatorOutput)
        await self.build_graph()  # type: ignore

    def worker(self, state: State) -> Dict[str, Any]:
        system_message = f"""you are A helpful assistant that can use tools to complete task.
        You keep working on a task until either you have question or clarification for the user Or the success criteria is met.
        You have many tools to help you, including tools to browse the Internet, navigating and retrieving web pages. 
        You have tools to run Python code, but note that you would need to include a print statement if you want to receive output.
        The current date and time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        This is the success criteria:
        {state['success_criteria']}
        You should reply either with a question or For the user about this assignment or with your final response. If you have a question for the user, 
        you need to reply by clearly stating your question. An example might be:
        Question: Please clarify whether you want a summary or detailed answer 
        If you have finished, Reply with final answer. And don't ask a question simply reply with the answer.
        """

        if state.get("feedback_on_work"):
            system_message += f"""
            \nHere is some feedback on your previous work: {state['feedback_on_work']}\n
            Here is the feedback on why this was rejected. 
            With this feedback, please continue the assignment, ensuring that you met the success criteria. Or have a question for the user.
            """

        found_system_message = False
        messages = state["messages"]
        for message in messages:
            if isinstance(message, SystemMessage):
                message.content = system_message
                found_system_message = True
        if not found_system_message:
            messages = [SystemMessage(content=system_message)] + messages

        response = self.worker_llm_with_tools.invoke(messages)  # type: ignore

        return {
            "messages": [response],
        }

    def evaluator(self, state: State) -> Dict[str, Any]:
        last_response = state["messages"][-1].content

        system_messages = f"""
        You are an evaluator that determines if a task has been completed successfully by an assistant.
        Assess the assistant's last response based on the given criteria. 
        Respond with your feedback, and with your decision on whether the success criteria has been met and whether more input input is nedded from the user.
        """

        user_message = f"""
        You are evaluating a conversation betwwen the User and Assistant. You decide what action to take based on the last response from the assistant, 
        the success criteria, and the full conversation history.
        
        The entire convesation history is as follows:
        {self.format_convesation(state['messages'])}
        
        the success criteria for this assignment is:
        {state['success_criteria']}
        
        And the final response from the assistant that you are evaluating is:
        {last_response}
        
        Respond with your feedback, and decide if the success criteria is met by this response.
        Also, decide if more user input s required, either because the assistant has a question or because the success criteria is not yet met. 
        or seems to be stuck and unable to answer without help.
        
        The Assistant has access to a tool to write files. If the assistant says they have written a file, then you can assume they have done so. 
        Overall, you should give the assistant the benefit of the doubt if they say they've done something, but you should reject if more work is needed.
        """

        if state["feedback_on_work"]:
            user_message += f"""
            Also, note that in a prior attempt from the assistant, you provided this feedback: {state['feedback_on_work']}\n. 
            Consider if this feedback has been addressed in the assistant's latest response. if you're seeing the assistant repeating the same mistakes, then consider responding that user input is needed.
            """

        evaluator_messages = [SystemMessage(
            content=system_messages), HumanMessage(content=user_message)]

        eval_result = self.evaluator_llm_with_output.invoke(  # type: ignore
            evaluator_messages)

        new_state = {
            "messages": {"role": "assistant", "content": f"Evauator feedback on this answer: {eval_result.feedback}"},
            "success_criteria": state["success_criteria"],
            "feedback_on_work": eval_result.feedback,
            "success_criteria_met": eval_result.success_criteria_met,
            "user_input_needed": eval_result.user_input_needed,
        }

        return new_state

    def worker_router(self, state: State) -> str:
        last_message = state['messages'][-1]
        if isinstance(last_message, HumanMessage):
            return "worker"
        else:
            return "evaluator"

    def format_convesation(self, messages: List[Any]) -> str:
        conversation = "Conversation history:\n\n"
        for message in messages:
            if isinstance(message, HumanMessage):
                conversation += f"User: {message.content}\n"
            elif isinstance(message, AIMessage):
                text = message.content or '[tool use]'
                conversation += f"Assistant: {text}\n"
        return conversation

    def route_based_on_evaluation(self, state: State) -> str:
        if state["success_criteria_met"] or state["user_input_needed"]:
            return END
        else:
            return "worker"

    async def build_graph(self):
        # Setup graph Builder with State
        graph_builder = StateGraph(State)

        # add nodes
        graph_builder.add_node("worker", self.worker)
        graph_builder.add_node("evaluator", self.evaluator)
        graph_builder.add_node("tools", ToolNode(
            tools=self.tools))  # type: ignore

        # add edges
        graph_builder.add_conditional_edges("worker", self.worker_router, {
                                            "tools": "tools", "evaluator": "evaluator"})
        graph_builder.add_edge("tools", "worker")
        graph_builder.add_conditional_edges(
            "evaluator", self.route_based_on_evaluation, {"END": END, "worker": "worker"})
        graph_builder.add_edge(START, "worker")

        # Compile the graph
        self.graph = graph_builder.compile(checkpointer=self.memory)

    async def run_superstep(self, message, success_criteria, history):
        config = {"configurable": {"thread_id": self.sidekick_id}}

        state = {
            "messages": message,
            "success_criteria": success_criteria or "The answer shoud be clear and accurate",
            "feedback_on_work": None,
            "success_criteria_met": False,
            "user_input_needed": False
        }
        result = await self.graph.ainvoke(state, config=config)  # type: ignore
        user = {"role": "user", "content": message}
        reply = {"role": "assistant",
                 "content": result["messages"][-2].content}
        feedback = {"role": "assistant",
                    "content": result["messages"][-1].content}
        return history + [user, reply, feedback]

    def cleanup(self):
        if self.browser:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.browser.close())
                if self.playwright:
                    loop.create_task(self.playwright.stop())
            except:
                asyncio.run(self.browser.close())
                if self.playwright:
                    asyncio.run(self.playwright.stop())

from playwright.async_api import async_playwright
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit, FileManagementToolkit
from dotenv import load_dotenv
import os
import requests
from requests.exceptions import RequestException, Timeout
from langchain_core.tools import Tool
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_experimental.tools import PythonREPLTool

load_dotenv(override=True)
pushover_token = os.getenv("PUSHOVER_API_TOKEN")
pushover_user = os.getenv("PUSHOVER_USER_KEY")
pushover_url = "https://api.pushover.net/1/messages.json"
serper = GoogleSerperAPIWrapper()


async def playwright_tools():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    toolkit = PlayWrightBrowserToolkit(async_browser=browser)
    return toolkit.get_tools(), browser, playwright


def push(text: str, timeout: int = 5) -> bool:
    """
    Sends a push notification using the Pushover API.

    Args:
        text: Message to send.
        timeout: Request timeout in seconds.

    Returns:
        True if the notification was successfully delivered, otherwise False.

    Usage Example
    -------------
    >>> push("Task completed.")
    True
    """

    payload = {
        "token": pushover_token,
        "user": pushover_user,
        "message": text
    }
    try:
        response = requests.post(pushover_url, data=payload, timeout=timeout)
        if response.status_code != 200:
            print(
                f"[PUSH ERROR] Status code: {response.status_code}, Response: {response.text}")
            return False

        data = response.json()
        if data.get("status") == 1:
            return True
        else:
            print(f"[PUSH ERROR] Response: {data}")
            return False

    except Timeout:
        print(f"[PUSH Error]: Request timed out after {timeout} seconds")
    except RequestException as e:
        print(f"[NETWORK Error]: {e}")

    return False


def get_file_tools():
    toolkit = FileManagementToolkit(root_dir="sandbox")
    return toolkit.get_tools()


async def other_tools():
    push_tool = Tool(name="send_push_notification",
                     func=push,
                     description="Sends a push notification with the given text message. Useful for notifying when a long task is complete. Input should be a string message.")
    file_tools = get_file_tools()

    tool_search = Tool(
        name="search_tool",
        func=serper.run,
        description="Useful for when you need to answer questions about current events or the current state of the world. Input should be a search query."
    )

    wikipedia = WikipediaAPIWrapper()  # type: ignore
    wiki_tool = Tool(
        name="wikipedia_tool",
        func=WikipediaQueryRun(api_wrapper=wikipedia).run,
        description="Useful for when you need to look up information about people, places, or things. Input should be a search query."
    )

    python_repl_tool = PythonREPLTool()

    return file_tools + [push_tool, tool_search, wiki_tool, python_repl_tool]

import json
import logging
import httpx
from DataModel.ServiceNowAPI import APIResponse
from fastapi import FastAPI, HTTPException
import uvicorn
from flow_logic import init_graph

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()
graph = None

# Load ServiceNow credentials from environment
from dotenv import load_dotenv
import os
load_dotenv()
SERVICENOW_USER = os.getenv('SERVICENOW_USER')
SERVICENOW_PWD = os.getenv('SERVICENOW_PWD')
SERVICENOW_ENDPOINT = "https://hexawaretechnologiesincdemo8.service-now.com"

@app.on_event("startup")
async def startup_event():
    """
    On application startup, initialize our StateGraph by calling init_graph().
    """
    global graph
    graph = await init_graph()

@app.get("/")
async def read_root():
    return {"message": "LangGraph Assistant is Running (Async)!"}

async def fetch_sys_id(task_number: str) -> str:
    """Fetch sys_id from ServiceNow using the task number."""
    try:
        url = f"{SERVICENOW_ENDPOINT}/api/now/table/sc_task?sysparm_query=number={task_number}&sysparm_fields=sys_id"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                auth=(SERVICENOW_USER, SERVICENOW_PWD),
                headers={"Accept": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("result") and len(data["result"]) > 0:
                sys_id = data["result"][0]["sys_id"]
                logging.debug(f"Fetched sys_id: {sys_id} for task {task_number}")
                return sys_id
            raise ValueError(f"No task found for number: {task_number}")
    except Exception as e:
        logging.error(f"Failed to fetch sys_id for {task_number}: {e}")
        raise

@app.post("/api/task")
async def execute_flow(task_data: APIResponse):
    """
    Endpoint to handle the flow for a given "number" (e.g., the ServiceNow Task Number).
    We will parse the JSON, create a thread_id, and invoke the graph.
    """
    try:
        logging.debug(f"Incoming task_data: {task_data}")
        task_response = task_data.model_dump()
        logging.debug(f"Converted task_response: {task_response}")

        if "result" not in task_response or not task_response["result"]:
            raise ValueError("Task response is missing 'result' field.")

        # Check if sys_id is missing, fetch it if needed
        if "sys_id" not in task_response["result"][0]:
            task_number = task_response["result"][0]["number"]
            sys_id = await fetch_sys_id(task_number)
            task_response["result"][0]["sys_id"] = sys_id
        else:
            logging.debug(f"sys_id already present: {task_response['result'][0]['sys_id']}")

        thread_id = "task_" + task_response["result"][0]["number"]
        output = await graph.ainvoke(
            {"task_response": task_response},
            config={"configurable": {"thread_id": thread_id}, "recursion_limit": 100}
        )
        return output

    except Exception as e:
        logging.error(f"Error executing flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

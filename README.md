Microsoft Windows [Version 10.0.17763.6893]
(c) 2018 Microsoft Corporation. All rights reserved.

C:\Users\automation_svc\Documents\testing-main\testing-main\WorkingDraft>venv\scripts\activate

(venv) C:\Users\automation_svc\Documents\testing-main\testing-main\WorkingDraft>python main.py
C:\Users\automation_svc\Documents\testing-main\testing-main\WorkingDraft\main.py:13: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
2025-03-04 07:09:57,790 - DEBUG - Using proactor: IocpProactor
[32mINFO[0m:     Started server process [[36m7148[0m]
[32mINFO[0m:     Waiting for application startup.
2025-03-04 07:09:57,815 - DEBUG - executing <function connect.<locals>.connector at 0x00000224FB186A20>
2025-03-04 07:09:57,816 - DEBUG - operation <function connect.<locals>.connector at 0x00000224FB186A20> completed
[32mINFO[0m:     Application startup complete.
[32mINFO[0m:     Uvicorn running on [1mhttp://127.0.0.1:8000[0m (Press CTRL+C to quit)
2025-03-04 07:10:10,234 - ERROR - Error executing flow: Task response is missing 'result' or 'sys_id' field.
[32mINFO[0m:     127.0.0.1:59093 - "[1mPOST /api/task HTTP/1.1[0m" [91m500 Internal Server Error[0m

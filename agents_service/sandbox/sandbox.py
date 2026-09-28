from dotenv import load_dotenv
from e2b_code_interpreter import Sandbox

load_dotenv()
sbx = Sandbox.create()  # Creates a persistent sandbox session
execution = sbx.run_code("print('hello world')")  # Execute Python inside the sandbox
print(execution.logs)

files = sbx.files.list("/")
print(files)

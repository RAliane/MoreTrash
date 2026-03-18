import anyio
from pydantic import BaseModel
from typing import Dict

class io_state(BaseModel):
    id: uint64
    state: int8 # 0 =
    dashMap: dict[uint64, int8]


class StateMachine:
    def __init__(self):
        self.state = io_state(id=1, state=0, dashMap={})
        self.lock = anyio.Lock()
        
    async def read(self):
        async with self.lock:
            if self.state.state == 0:
                print("Server is in READ mode.")
            else:
                print("Cannot read. Server in WRITE mode.")

    async def write(self, key: uint64, value: int):
        async with self.lock:
            print("Switching to WRITE mode.")
            self.state.state = 1
            self.state.dashMap[key] = value
            print(f"Updated key {key} with value {value}.")
            self.state.state = 0
            print("Returning to READ mode.")
"""         if io_state.state == 0:
            print("The server is listening for updates.")
        else:
            print("The server is in a write state, please wait till write lock is lifted.")

    async def LockCondition(input, output):
        while io_state == 0:
            input.allowRead()
        else:
            output.allowedWrite()
 """
async def main():
    sm = StateMachine()

    await sm.read()
    await sm.write(1, 42)
    await sm.read()

if __name__ == "__main__":
    anyio.run(main)

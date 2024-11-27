import json
from jupyter_client import KernelManager
from queue import Empty as QueueEmpty


def read_notebook_cells(notebook_path):
    """Reads the code cells from a Jupyter Notebook."""
    with open(notebook_path, 'r', encoding='utf-8') as file:
        notebook = json.load(file)
    cells = [cell['source'] for cell in notebook['cells'] if cell['cell_type'] == 'code']
    return cells


def execute_cell(kernel_manager, code):
    """Executes a single code cell using the kernel manager."""
    kernel_client = kernel_manager.client()
    kernel_client.start_channels()

    try:
        # Wait for the kernel to be ready
        kernel_client.kernel_info()

        # Send the code for execution
        msg_id = kernel_client.execute(code)

        # Capture and print outputs
        while True:
            try:
                msg = kernel_client.get_iopub_msg(timeout=10)  # Increase the timeout if needed
                if msg['parent_header'].get('msg_id') == msg_id:
                    msg_type = msg['msg_type']
                    content = msg['content']
                    if msg_type == 'execute_result':
                        print("Execution Result:", content['data']['text/plain'])
                    elif msg_type == 'stream':
                        print("Stream Output:", content['text'])
                    elif msg_type == 'error':
                        print("Error:", '\n'.join(content['traceback']))
                    if msg_type in ('execute_result', 'error'):
                        break
            except QueueEmpty:
                print("No response from kernel. Timeout occurred.")
                break

    finally:
        kernel_client.stop_channels()


def main():
    # Path to the notebook file
    notebook_path = "example.ipynb"

    # Read the notebook cells
    cells = read_notebook_cells(notebook_path)

    # Initialize the kernel manager
    kernel_manager = KernelManager()
    kernel_manager.start_kernel()

    try:
        # Execute the first code cell
        if cells:
            print(f"Executing Cell:\n{cells[0]}")
            # cells[0] is a list of strings, join them to form a single string
            execute_cell(kernel_manager, ''.join(cells[0]))
        else:
            print("No code cells found in the notebook.")
    finally:
        kernel_manager.shutdown_kernel()

if __name__ == "__main__":
    main()

import json
from tkinter import Tk, Text, Button, Label, filedialog, END, Frame
from jupyter_client import KernelManager
from threading import Thread
import logging
from queue import Empty as QueueEmpty

logging.basicConfig(level=logging.DEBUG)
# Write to file
logger = logging.getLogger(__name__)
logger.setLevel(
    logging.DEBUG
)
file_handler = logging.FileHandler('notebook_executor.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class NotebookExecutorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Notebook Executor")
        
        # Create UI Elements
        self.label = Label(root, text="Load a notebook and select a cell to execute:")
        self.label.pack()

        self.load_button = Button(root, text="Load Notebook", command=self.choose_notebook)
        self.load_button.pack()

        self.cell_frame = Frame(root)
        self.cell_frame.pack(side="top", fill="x", expand=False)

        self.output_label = Label(root, text="Output:")
        self.output_label.pack()

        self.output_area = Text(root, height=10, width=80, state="normal")
        self.output_area.pack()

        self.cells = []
        self.kernel_manager = None

        self.load_notebook("example.ipynb")

        self.execute_thread = None
        self.show_output_thread = Thread(target=self.show_output_thread).start()

    def choose_notebook(self):
        """Open a file dialog to choose a notebook file."""
        filepath = filedialog.askopenfilename(filetypes=[("Jupyter Notebook", "*.ipynb")])
        self.load_notebook(filepath)

    def load_notebook(self, filepath):
        """Load a notebook and display its code cells."""
        if filepath:
            with open(filepath, 'r', encoding='utf-8') as file:
                notebook = json.load(file)
            self.cells = [cell['source'] for cell in notebook['cells'] if cell['cell_type'] == 'code']
            self.display_cells()
            self.initialize_kernel()

    def initialize_kernel(self):
        """Start a Jupyter kernel."""
        if self.kernel_manager is not None:
            self.kernel_manager.shutdown_kernel()
        self.kernel_manager = KernelManager()
        self.kernel_manager.start_kernel()

    def display_cells(self):
        """Display clickable buttons for each code cell."""
        for widget in self.cell_frame.winfo_children():
            widget.destroy()

        for idx, cell in enumerate(self.cells):
            cell_text = ''.join(cell)
            print(f"cell_text:\n{cell_text}")
            # Align left
            cell_button = Button(self.cell_frame, text=cell_text, command=lambda i=idx: self.execute_cell(i), anchor="w", padx=0, justify="left")
            cell_button.pack(side="top", fill="x", expand=False, padx=0)

    def execute_cell(self, cell_index):
        """Execute the selected cell."""
        # Run in a separate thread to avoid blocking the UI
        if self.execute_thread is not None:
            logger.debug("waiting for previous execution to finish")
            self.execute_thread.join()
        self.output_area.config(state="normal")
        self.output_area.delete(1.0, END)
        self.execute_thread = Thread(target=self.execute_cell_thread, args=(cell_index,)).start()

    def execute_cell_thread(self, cell_index):
        code = ''.join(self.cells[cell_index])
        kernel_client = self.kernel_manager.client()
        kernel_client.start_channels()
        
        try:
            kernel_client.kernel_info()
            logger.debug(f"Executing cell")
            msg_id = kernel_client.execute(code)
            logger.debug(f"Done executing cell")
        except Exception as e:
            print(f"Error during execution: {str(e)}")
            logger.error(f"Error during execution: {str(e)}")
            self.show_output(f"Error during execution: {str(e)}")

    def show_output_thread(self):
        kernel_client = self.kernel_manager.client()
        kernel_client.start_channels()
        try:
            while True:
                logger.debug("Waiting for kernel response...")
                try:
                    msg = kernel_client.get_iopub_msg(timeout=10)
                except QueueEmpty:
                    logger.debug("No more messages")
                    continue
                content = msg['content']
                msg_type = msg['msg_type']
                if msg_type == 'execute_result':
                    logger.debug(f"Result: {content['data']['text/plain']}")
                    self.show_output(f"{content['data']['text/plain']}")
                elif msg_type == 'stream':
                    logger.debug(f"Stream: {content['text']}")
                    self.show_output(f"{content['text']}")
                elif msg_type == 'error':
                    traceback = '\n'.join(content['traceback'])
                    self.show_output(f"Error: {traceback}")
        except Exception as e:
            logger.error(f"Error in output thread: {str(e)}, {type(e)}")
            self.show_output(f"Error in output thread: {str(e)}")
        finally:
            kernel_client.stop_channels()

    def show_output(self, text):
        """Display output in the output area."""
        self.output_area.insert(END, text + "\n")


if __name__ == "__main__":
    root = Tk()
    app = NotebookExecutorApp(root)
    root.mainloop()

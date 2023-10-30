import interpreter
from interpreter.code_interpreters.create_code_interpreter import create_code_interpreter
import gradio as gr
import tempfile
import nbformat

interpreter.model = "gpt-3.5-turbo"
interpreter.auto_run = True

USER_HEADING = "##### User:\n"
ASSISTANT_HEADING = "##### Assistant:\n"

def add_user_message(history, user_message):
    if not user_message:
        return history, ""

    history = history + [(user_message, "")]
    return history, ""

def reset_interpreter():
    # HACK: interpreter.reset() sometimes has an exception when running in 
    # Gradio so I'm manually resetting the state below

    interpreter.messages = [ ]

    if "shell" in interpreter._code_interpreters and interpreter._code_interpreters["shell"].process is not None:
        interpreter._code_interpreters["shell"].terminate()
    if "python" in interpreter._code_interpreters and interpreter._code_interpreters["python"].process is not None:
        interpreter._code_interpreters["python"].terminate()

    interpreter._code_interpreters["shell"] = create_code_interpreter("shell")
    interpreter._code_interpreters["python"] = create_code_interpreter("python")


def generate(model, history):
    if len(history) == 1:
        reset_interpreter()

    interpreter.model = model

    new_user_message = history[-1][0]
    history[-1][1] = ""

    for chunk in interpreter.chat(new_user_message, stream=True, display=False):
        if 'message' in chunk:
            history[-1][1] += chunk['message']
        elif 'language' in chunk:
            history[-1][1] += f"\n```{chunk['language']}\n"
        elif 'code' in chunk:
            history[-1][1] += chunk['code']
        elif 'end_of_code' in chunk:
            history[-1][1] += "\n```\n"
        elif 'executing' in chunk:
            history[-1][1] += "\n```\n"
        elif 'output' in chunk:
            history[-1][1] += chunk['output']
        elif 'end_of_execution' in chunk:
            history[-1][1] += "\n```\n"

        yield history

    return history

def notebook_to_chat(history, file):
    history = [ [ "Here are the contents of a Jupyter notebook", "" ] ]

    reset_interpreter()

    # Convert Jupyter Notebook file into Open Interpreter messages
    with open(file.name, "r") as f:
        nb = nbformat.read(f, as_version=4)

        for cell in nb.cells:
            content = cell.source

            if content.strip() == "":
                continue

            if content.startswith(ASSISTANT_HEADING):
                role = "assistant"
                content = content[len(ASSISTANT_HEADING):]   # Strip Assistant Heading
            elif content.startswith(USER_HEADING):
                role = "user"
                content = content[len(USER_HEADING):]   # Strip User Heading
            else:
                role = "user"

            if cell.cell_type == "markdown":
                interpreter.messages.append({
                    "role": role,
                    "message": content
                })

                if role == "user":
                    history.append([content, ""])
                elif role == "assistant":
                    history[-1][1] += content

            elif cell.cell_type == "code":
                if content.startswith("!"):
                    code_interpreter = interpreter._code_interpreters["shell"]
                    code = content[1:]
                else:
                    code_interpreter = interpreter._code_interpreters["python"]   # HACK:  Assume all code is Python
                    code = content

                history[-1][1] += f"\n```python\n{content}\n```\n"
                history[-1][1] += f"\n```\n"
                yield history

                output = ""
                for line in code_interpreter.run(code):
                    if "output" in line:
                        output += line["output"]
                        history[-1][1] += line["output"]
                        yield history

                history[-1][1] += f"\n```\n"
                
                interpreter.messages.append({
                    "role": "assistant",   # HACK: Assume all code cells are written by the assistant
                    "language": "python",  # HACK: Assume all code cells are Python
                    "code": content,
                    "output": output,
                    "message": ""
                })
                
                yield history

    return history

def chat_to_notebook(history):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.ipynb')
    temp_path = temp_file.name

    # Convert Open Interpreter messages into Jupyter Notebook file
    with open(temp_path, "w")  as f:
        nb = nbformat.v4.new_notebook()

        for message in interpreter.messages:
            if message['role'] == "user":
                nb.cells.append(nbformat.v4.new_markdown_cell(USER_HEADING + message['message']))
            elif message['role'] == "assistant":
                if 'message' in message:
                    nb.cells.append(nbformat.v4.new_markdown_cell(ASSISTANT_HEADING + message['message']))

                if 'code' in message:
                    code_cell = nbformat.v4.new_code_cell(ASSISTANT_HEADING + message['code'])
                    code_cell.outputs = [nbformat.v4.new_output(output_type="stream", text=message['output'])]
                    nb.cells.append(code_cell)

        nbformat.write(nb, f)
    
    return temp_path

# Setup Gradio UI
CSS = """
.contain { display: flex; flex-direction: column; }
.gradio-container { height: 100vh !important; }
.svelte-vt1mxs { flex-grow: 1; overflow: auto; }
#chatbot { flex-grow: 1; overflow: auto; }
"""

with gr.Blocks(css=CSS) as demo:
    chatbot = gr.Chatbot(
        [],
        elem_id="chatbot",
        bubble_full_width=False
    )

    with gr.Row():
        user_message = gr.Textbox(
            scale=4,
            show_label=False,
            placeholder="Enter message for Open Interpreter and press Enter",
            container=False,
        )
        model = gr.Dropdown(
            choices=["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4"],
            show_label=False,
            value=interpreter.model,
            interactive=True
        )

    with gr.Row():
        load_button = gr.UploadButton("Load Notebook into Chat")
        save_button = gr.Button("Convert Chat into Notebook")

    notebook_file = gr.File(label="Notebook file will appear here after you click on Convert Chat into Notebook", interactive=False)

    user_message.submit(add_user_message, [chatbot, user_message], [chatbot, user_message], queue=False).then(generate, [model, chatbot], chatbot)

    load_button.upload(notebook_to_chat, [chatbot, load_button], [chatbot], queue=True)
    save_button.click(chat_to_notebook, [chatbot], [notebook_file], queue=False)
    
demo.queue().launch(debug=True, share=False)
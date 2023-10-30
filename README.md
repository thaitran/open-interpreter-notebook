# Open Interpreter Notebook
This is a prototype of enabling [Open Interpreter](https://github.com/KillianLucas/open-interpreter/) to import and export Jupyter notebooks.

Create a Conda environment (optional):
```
conda create -n oi-notebook python=3.11
conda activate oi-notebook
```

Setup:
```
pip install -r requirements.txt
export OPENAI_API_KEY=<insert your Open AI key here>
```

Run the Gradio prototype:
```
python app.py
```

Example:

1. Load your web browser to http://127.0.0.1:7860/
2. Click on **Load Notebook into Chat** and select [examples/Heatmap.ipynb](https://github.com/thaitran/open-interpreter-notebook/blob/main/examples/Heatmap.ipynb)
   * The cells of the notebook will be converted into Open Interpreter messages and will be run in the code interpreter.
3. Enter a new message such as **"Plot the heatmap in grayscale"**
4. Click on **Convert Chat to Notebook**
5. Click on the link in the box below to download the notebook file
   

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from graph_setup import build_graph

def main():
    """
    Generates a PNG visualization of the graph.
    """
    graph = build_graph()
    
    try:
        png_data = graph.get_graph().draw_mermaid_png()
        with open("graph_visualization.png", "wb") as f:
            f.write(png_data)
        print("Successfully generated graph_visualization.png")
        print("Please open the file to see the graph.")
    except Exception as e:
        print(f"An error occurred during diagram generation: {e}")
        print("It's possible that you are missing some browser dependencies for Mermaid.js rendering.")
        print("Please try running: playwright install --with-deps")

if __name__ == "__main__":
    main()
